"""Recheck complete case/model sets and retain all search-versus-raw contrasts."""
import argparse
from pathlib import Path
import re
from search_transfer import ROOT,PROTOCOL,read,write,digest,summarize_run,module,pairs

checks=module('transfer_final_summary_check','collect-discard-correction-screen.py')


def compare(directory, cases):
    protocol=read(PROTOCOL);source=read(ROOT/'ai/strong/search-transfer-source-v1.json')
    known={c['id']:c for c in protocol['cases']}
    assert cases and len(set(cases))==len(cases) and set(cases)<=set(known)
    summaries,raw,pins={},{},{};games=0
    for key in protocol['models']:
        summaries[key],raw[key],pins[key]={},{},{}
        for name in cases:
            case=known[name];out=directory/f'{key}-{name}';saved=read(out/'verified.json')
            assert re.fullmatch('[a-f0-9]{40}',saved['revision'])
            for k,v in {'key':key,'case':name,'smoke':False,'games':case['games'],'verified':True,
                'source_revision':source['revision'],'source_sha256':source['sha256'],
                'protocol_sha256':digest(PROTOCOL),'game_truncations':0,'search_truncations':0,
                'qualification_eligible':False,'prefix':f'runs/search-transfer-v1-{key}-{name}'}.items():assert saved[k]==v,k
            for file,sha in saved['artifacts'].items():assert Path(file).name==file and digest(out/file)==sha,file
            assert read(out/'checkpoint.json')==protocol['models'][key]
            summary=summarize_run(out,protocol,key,case);checks.same_summary(summary,saved['summary'])
            summaries[key][name]=summary;raw[key][name]=read(out/'search.json')['results'];games+=case['games']
            pins[key][name]={'revision':saved['revision'],'prefix':saved['prefix'],'verified_sha256':digest(out/'verified.json')}
    contrasts={}
    for left,right in [('10101','parent'),('10102','parent'),('10102','10101')]:
        contrasts[left+'-minus-'+right]={}
        for name in cases:
            def paired(x,y):return pairs.paired_difference(x,y,protocol['bootstrap_replicates'],protocol['bootstrap_seed'])
            a,b=raw[left][name],raw[right][name]
            cell={'overall':paired(a,b),'rules':{}}
            for v in ['original','recharged']:
                for s in [False,True]:
                    select=lambda rows:[r for r in rows if r['variant']==v and r['sealed']==s]
                    cell['rules'][v+('/sealed' if s else '/open')]=paired(select(a),select(b))
            contrasts[left+'-minus-'+right][name]=cell
    complete=set(cases)==set(known)
    if complete:assert games==protocol['planned_new_games']
    return {'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],'source_sha256':source['sha256'],
        'verified_cases':cases,'all_cases_verified':complete,'new_games':games,'paired_baseline_games':games,
        'summaries':summaries,'between_model_search_contrasts':contrasts,'provenance':pins,
        'game_truncations':0,'search_truncations':0,'qualification_eligible':False,
        'scope':protocol['analysis']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('directory',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--cases',nargs='+',choices=['heuristic-2p','search_geo-2p','a260-3p'],
        default=['heuristic-2p','search_geo-2p','a260-3p'])
    a=p.parse_args();r=compare(a.directory.resolve(),a.cases);write(a.output,r)
    print({'new_games':r['new_games'],'all_cases_verified':r['all_cases_verified'],
        'paired_deltas':{k:{c:v['search_minus_raw']['overall'] for c,v in cells.items()} for k,cells in r['summaries'].items()}})
