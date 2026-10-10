"""Fixed public-search48 transfer experiment, preserving models and opponents."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, read, write, digest, summarize


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'ai/strong'/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


verifier=module('search_transfer_baseline_contract','collect-population-screen.py')
pairs=module('search_transfer_pairs','compare-population-screens.py')
PROTOCOL=ROOT/'ai/strong/search-transfer-protocol-v1.json'


def verify(report, protocol, key, case, guided=True, smoke=False):
    pin=protocol['models'][key];n=case['players'];deals=1 if smoke else case['deals']
    seed=protocol['smoke']['seed_template'].format(case=case['id']) if smoke else case['seed']
    assert report['candidate_search_samples']==(48 if guided else 0)
    assert report['candidate_geographic_search']==guided
    assert report['candidate_search_model_proposal'] and report['candidate_search_scope']=='all'
    assert not report['async_rollout'] and report['engine_workers']==min(24,deals*4*n)
    opponent=protocol['frozen_opponent']
    assert report['opponent_feature_revision']==(opponent['feature_revision'] if case['opponent']=='a260' else None)
    screen={'players':n,'games':deals*4*n,'opponent':case['opponent']}
    if case['opponent']=='a260':screen['sha256']=opponent['sha256']
    # The shared verifier checks raw-policy arenas. Validate the actual search
    # condition above, then reuse only its remaining unchanged arena contract.
    contract={**report,'candidate_search_samples':0,'candidate_geographic_search':False}
    ev={**protocol,'seed_template':seed,'deal_offsets':list(range(deals))}
    stats=verifier.verify_report(contract,screen,{'hashes':{'latest.onnx':pin['files']['inference64.onnx']}},ev,pin['feature_revision'])
    rows=report['results'];assert {r['episode'] for r in rows}==set(range(deals*4*n))
    roles=({'learner'} if guided else set())|({'search_geo'} if case['opponent']=='search_geo' else set())
    assert set(stats['search_stats'])==roles
    assert all(r['evaluations']>0 and r['truncated']==0 for r in stats['search_stats'].values())
    return {**summarize(rows,protocol),'search_stats':stats['search_stats'],'seconds':report['seconds'],
        'rules':{v+('/sealed' if s else '/open'):summarize([r for r in rows if r['variant']==v and r['sealed']==s],protocol)
            for v in ['original','recharged'] for s in [False,True]}}


def summarize_run(out, protocol, key, case, smoke=False):
    guided=read(out/'search.json');result={'search':verify(guided,protocol,key,case,True,smoke)}
    if not smoke:
        baseline=read(out/'baseline.json')
        assert digest(out/'baseline.json')==case['baselines'][key]['sha256']
        result['baseline']=verify(baseline,protocol,key,case,False)
        def paired(a,b):return pairs.paired_difference(a,b,protocol['bootstrap_replicates'],protocol['bootstrap_seed'])
        result['search_minus_raw']={'overall':paired(guided['results'],baseline['results']),'rules':{}}
        for v in ['original','recharged']:
            for s in [False,True]:
                select=lambda report:[r for r in report['results'] if r['variant']==v and r['sealed']==s]
                result['search_minus_raw']['rules'][v+('/sealed' if s else '/open')]=paired(select(guided),select(baseline))
    return result


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102'])
    p.add_argument('case',choices=['heuristic-2p','search_geo-2p','a260-3p']);p.add_argument('output',type=Path)
    p.add_argument('--smoke',action='store_true');p.add_argument('--upload',action='store_true');a=p.parse_args()
    protocol=read(PROTOCOL);case=next(c for c in protocol['cases'] if c['id']==a.case);pin=protocol['models'][a.key]
    assert protocol['candidate_search']=={'samples':48,'geography':True,'scope':'all','include_model_proposal':True,'search_max_steps':2400,'actual_game_max_steps':1600}
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    status={'key':a.key,'case':a.case,'smoke':a.smoke,'status':'running','protocol_sha256':digest(PROTOCOL),
        'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'trained':False,'qualification_eligible':False}
    try:
        model=hf_hub_download(protocol['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
        assert digest(model)==pin['files']['inference64.onnx'];write(out/'checkpoint.json',pin)
        deals=1 if a.smoke else case['deals'];seed=protocol['smoke']['seed_template'].format(case=a.case) if a.smoke else case['seed']
        command=[sys.executable,str(ROOT/'ai/strong/evaluate.py'),model,'--players',str(case['players']),
            '--games',str(deals*4*case['players']),'--workers','24','--seed',seed,'--search-samples','48',
            '--geographic-search','--search-scope','all','--output',str(out/'search.json')]
        if case['opponent']=='a260':
            other=protocol['frozen_opponent'];path=hf_hub_download(protocol['repo'],other['path'],revision=other['revision'])
            assert digest(path)==other['sha256'];command+=['--opponent-model',path]
        else:command+=['--opponent',case['opponent']]
        with (out/'search.log').open('w') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        if not a.smoke:
            base=case['baselines'][a.key];path=hf_hub_download(protocol['repo'],base['path'],revision=base['revision'])
            assert digest(path)==base['sha256'];(out/'baseline.json').write_bytes(Path(path).read_bytes())
        summary=summarize_run(out,protocol,a.key,case,a.smoke);write(out/'summary.json',summary)
        status.update(status='complete',games=deals*4*case['players'],game_truncations=0,search_truncations=0)
    except BaseException as error:
        status.update(status='failed',error=type(error).__name__+': '+str(error));raise
    finally:
        status['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'search-transfer-check.json',status)
        if a.upload:HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,
            path_in_repo='runs/search-transfer-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.case}')
        print(status,flush=True)


if __name__=='__main__':main()
