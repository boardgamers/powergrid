"""Compare all three frozen policies, rechecking raw complete-game shards."""
import argparse
import importlib.util
from pathlib import Path
import re
from five_plant_screen import ROOT, read, write, digest


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'ai/strong'/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


collector=module('discard_opponent_collector','collect-discard-opponents.py')
pairs=module('discard_opponent_pairs','compare-population-screens.py')


def compare(directory, counts):
    protocol_path=ROOT/'ai/strong/discard-opponents-protocol-v1.json';protocol=read(protocol_path)
    source=read(ROOT/'ai/strong/discard-opponents-source-v1.json')
    model_path=ROOT/'ai/strong/discard-correction-screen-models-v1.json'
    assert len(set(counts))==len(counts) and set(counts)<=set(protocol['players']) and counts
    arms,raw,provenance={},{},{}
    games=0
    for key in protocol['models']:
        arms[key],raw[key],provenance[key]={},{},{}
        for n in counts:
            out=directory/f'{key}-{n}p';saved=read(out/'verified.json')
            assert re.fullmatch('[a-f0-9]{40}',saved['revision'])
            for k,v in {'key':key,'players':n,'smoke':False,'verified':True,
                'source_revision':source['revision'],'source_sha256':source['sha256'],
                'models_sha256':digest(model_path),'qualification_eligible':False,
                'prefix':f'runs/discard-opponents-v1-{key}-{n}p'}.items():assert saved[k]==v,k
            for name,sha in saved['artifacts'].items():
                assert Path(name).name==name and digest(out/name)==sha,name
            summary=collector.verify_local(out,key,n)
            collector.checks.same_summary(summary,saved['summary'])
            count=sum(r['games'] for r in summary.values());assert saved['games']==count
            games+=count
            provenance[key][str(n)]={'revision':saved['revision'],'prefix':saved['prefix'],
                'verified_sha256':digest(out/'verified.json')}
            for opponent,row in summary.items():
                cell=f'{opponent}/{n}p';arms[key][cell]=row
                raw[key][cell]=read(out/(opponent+'.json'))['results']
    contrasts={}
    for left,right in [('10101','parent'),('10102','parent'),('10102','10101')]:
        contrasts[left+'-minus-'+right]={}
        for cell,left_rows in raw[left].items():
            right_rows=raw[right][cell]
            def paired(x,y):return pairs.paired_difference(x,y,
                repeats=protocol['bootstrap_replicates'],seed=protocol['bootstrap_seed'])
            rules={}
            for variant in ['original','recharged']:
                for sealed in [False,True]:
                    select=lambda rows:[r for r in rows if r['variant']==variant and r['sealed']==sealed]
                    rules[variant+('/sealed' if sealed else '/open')]=paired(select(left_rows),select(right_rows))
            contrasts[left+'-minus-'+right][cell]={'overall':paired(left_rows,right_rows),'rules':rules}
    complete=set(counts)==set(protocol['players'])
    if complete:assert games==protocol['planned_games']
    return {'source_revision':source['revision'],'source_sha256':source['sha256'],
        'protocol_sha256':digest(protocol_path),'models_sha256':digest(model_path),
        'prescribed_players':protocol['players'],'verified_players':counts,'all_shards_verified':complete,
        'games':games,'game_truncations':0,'search_truncations':0,'provenance':provenance,
        'arms':arms,'contrasts':contrasts,'qualification_eligible':False,
        'scope':'Fresh development comparisons, separate training seeds, all seats/rules. Whole-deal marginal exploratory bootstrap intervals; no multiplicity adjustment. No final qualification.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('directory',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--players',nargs='+',type=int,choices=range(2,7),default=list(range(2,7)),
        help='Optional complete-count subset, explicitly marked partial; requires all three policies per count')
    a=p.parse_args();result=compare(a.directory.resolve(),a.players);write(a.output,result)
    print({'games':result['games'],'all_shards_verified':result['all_shards_verified'],
        'win_rates':{k:{c:r['win_rate'] for c,r in cells.items()} for k,cells in result['arms'].items()}})
