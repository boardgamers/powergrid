"""Verify every raw game and compare all frozen correction arms on paired deals."""
import argparse
import importlib.util
import math
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from five_plant_screen import ROOT, read, write, digest, collect

spec=importlib.util.spec_from_file_location('discard_screen_pairs',ROOT/'ai/strong/compare-population-screens.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def same_summary(actual, stored):
    if isinstance(actual,dict):
        assert actual.keys()==stored.keys()
        for key,value in actual.items():same_summary(value,stored[key])
    elif isinstance(actual,list):
        assert len(actual)==len(stored)
        for x,y in zip(actual,stored):same_summary(x,y)
    elif isinstance(actual,float):
        assert math.isfinite(actual) and math.isfinite(stored) and abs(actual-stored)<=1e-12
    else:assert actual==stored


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('revision');p.add_argument('output',type=Path);a=p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',a.revision)
    protocol_path=ROOT/'ai/strong/discard-correction-screen-protocol-v1.json'
    protocol=read(protocol_path);source=read(ROOT/'ai/strong/discard-correction-screen-source-v1.json')
    models_path=ROOT/'ai/strong/discard-correction-screen-models-v1.json';models=read(models_path)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    arms,raw={},{}
    for key in protocol['models']:
        target=out/key;target.mkdir();prefix='runs/discard-correction-screen-v1-'+key
        def fetch(name):
            assert Path(name).name==name
            path=target/name;path.write_bytes(Path(hf_hub_download(protocol['repo'],prefix+'/'+name,revision=a.revision)).read_bytes());return path
        status=read(fetch('screen-check.json'))
        for name,value in {'key':key,'status':'complete','protocol_sha256':digest(protocol_path),
            'models_sha256':digest(models_path),'source_revision':source['revision'],'source_sha256':source['sha256'],
            'games':1600,'cells':7,'truncations':0,'qualification_eligible':False}.items():assert status[name]==value,(key,name)
        required={'checkpoint.json','parity.json','serving.json','summary.json'}|{f"{s['opponent']}-{s['players']}p.json" for s in protocol['screens']}
        assert required<=set(status['artifacts'])
        for name,sha in status['artifacts'].items():assert digest(fetch(name))==sha,name
        manifest=read(target/'checkpoint.json');pin=models[key]
        assert manifest['key']==key and manifest['pin']==pin and manifest['revision']==pin['revision']
        assert manifest['feature_revision']==pin['feature_revision'] and manifest['hashes']=={'latest.onnx':pin['files']['inference64.onnx']}
        parity,serving=read(target/'parity.json'),read(target/'serving.json')
        assert parity['positions']==serving['positions']==2553
        assert parity['all_actions_match'] and parity['inactive_values_zero'] and serving['all_moves_legal']
        assert parity['model_sha256']==serving['model_sha256']==pin['files']['inference64.onnx']
        summary=collect(target,{'evaluation':protocol},manifest)
        same_summary(summary,read(target/'summary.json'))
        arms[key]=summary
        raw[key]={}
        for screen in protocol['screens']:
            n,opponent=screen['players'],screen['opponent'];rows=read(target/f'{opponent}-{n}p.json')['results']
            assert {r['episode'] for r in rows}==set(range(screen['games']))
            assert all(r['seat']==r['roles'].index('learner') and r['win']==r['value'][r['seat']] for r in rows)
            assert all(len(r['value'])==n and abs(sum(r['value'])-1)<1e-8 and all(0<=x<=1 for x in r['value']) for r in rows)
            raw[key][f'{opponent}/{n}p']=rows
    contrasts={}
    for left,right in [('10101','parent'),('10102','parent'),('10102','10101')]:
        comparisons={}
        for cell,left_rows in raw[left].items():
            right_rows=raw[right][cell]
            def compare(x,y):return module.paired_difference(x,y,repeats=protocol['bootstrap_replicates'],seed=protocol['bootstrap_seed'])
            rules={}
            for v in ['original','recharged']:
                for s in [False,True]:
                    select=lambda rows:[r for r in rows if r['variant']==v and r['sealed']==s]
                    rules[v+('/sealed' if s else '/open')]=compare(select(left_rows),select(right_rows))
            comparisons[cell]={'overall':compare(left_rows,right_rows),'rules':rules}
        contrasts[left+'-minus-'+right]=comparisons
    result={'revision':a.revision,'protocol_sha256':digest(protocol_path),'models_sha256':digest(models_path),
        'source_revision':source['revision'],'games':4800,'game_truncations':0,'search_truncations':0,
        'arms':arms,'contrasts':contrasts,'qualification_eligible':False,
        'scope':'Fresh complete-game development comparison, all counts/rules. Limited opponent scope and16 deals/cell; full strength gate remains required. Marginal exploratory intervals, no multiplicity adjustment.'}
    write(out/'verified.json',result)
    print({'games':4800,'contrasts':{k:{cell:v['overall'] for cell,v in cells.items()} for k,cells in contrasts.items()}})


if __name__=='__main__':main()
