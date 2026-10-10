"""Independently verify one complete frozen opponent-extension shard."""
import argparse
import importlib.util
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from discard_opponents_screen import ROOT, read, write, digest, collect

spec=importlib.util.spec_from_file_location('summary_check',ROOT/'ai/strong/collect-discard-correction-screen.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)


def verify_local(out, key, players, smoke=False):
    """Recheck saved raw artifacts; a verified.json flag alone is not evidence."""
    protocol_path=ROOT/'ai/strong/discard-opponents-protocol-v1.json';protocol=read(protocol_path)
    source=read(ROOT/'ai/strong/discard-opponents-source-v1.json')
    models_path=ROOT/'ai/strong/discard-correction-screen-models-v1.json';pin=read(models_path)[key]
    status=read(out/'screen-check.json')
    games=(4 if smoke else sum(protocol['opponents'].values()))*4*players
    for k,v in {'key':key,'players':players,'smoke':smoke,'status':'complete','games':games,
        'protocol_sha256':digest(protocol_path),'models_sha256':digest(models_path),'source_revision':source['revision'],
        'source_sha256':source['sha256'],'game_truncations':0,'search_truncations':0,'qualification_eligible':False}.items():assert status[k]==v,k
    assert {'checkpoint.json','summary.json',*[k+'.json' for k in protocol['opponents']]}<=set(status['artifacts'])
    for name,sha in status['artifacts'].items():
        assert Path(name).name==name
        assert digest(out/name)==sha,name
    assert read(out/'checkpoint.json')==pin
    summary=collect(out,protocol,pin,players,smoke);checks.same_summary(summary,read(out/'summary.json'))
    for opponent,row in summary.items():
        if opponent=='search_geo':
            assert set(row['search_stats'])=={'search_geo'}
            assert row['search_stats']['search_geo']['evaluations']>0 and row['search_stats']['search_geo']['truncated']==0
        else:assert not row['search_stats']
        report=read(out/(opponent+'.json'))
        assert all(len(r['value'])==players and abs(sum(r['value'])-1)<1e-8 and all(0<=x<=1 for x in r['value']) for r in report['results'])
    return summary


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102'])
    p.add_argument('players',type=int,choices=range(2,7));p.add_argument('revision');p.add_argument('output',type=Path)
    p.add_argument('--smoke',action='store_true');a=p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',a.revision)
    protocol_path=ROOT/'ai/strong/discard-opponents-protocol-v1.json';protocol=read(protocol_path)
    source=read(ROOT/'ai/strong/discard-opponents-source-v1.json')
    models_path=ROOT/'ai/strong/discard-correction-screen-models-v1.json';pin=read(models_path)[a.key]
    prefix='runs/discard-opponents-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.players}p'
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    def fetch(name):
        assert Path(name).name==name
        path=out/name;path.write_bytes(Path(hf_hub_download(protocol['repo'],prefix+'/'+name,revision=a.revision)).read_bytes());return path
    status=read(fetch('screen-check.json'))
    games=(4 if a.smoke else sum(protocol['opponents'].values()))*4*a.players
    for k,v in {'key':a.key,'players':a.players,'smoke':a.smoke,'status':'complete','games':games,
        'protocol_sha256':digest(protocol_path),'models_sha256':digest(models_path),'source_revision':source['revision'],
        'source_sha256':source['sha256'],'game_truncations':0,'search_truncations':0,'qualification_eligible':False}.items():assert status[k]==v,k
    assert {'checkpoint.json','summary.json',*[k+'.json' for k in protocol['opponents']]}<=set(status['artifacts'])
    for name,sha in status['artifacts'].items():assert digest(fetch(name))==sha
    summary=verify_local(out,a.key,a.players,a.smoke)
    result={'revision':a.revision,'prefix':prefix,'key':a.key,'players':a.players,'smoke':a.smoke,'games':games,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'models_sha256':digest(models_path),
        'summary':summary,'game_truncations':0,'search_truncations':0,'verified':True,'qualification_eligible':False,
        'artifacts':{p.name:digest(p) for p in out.iterdir() if p.is_file()}}
    write(out/'verified.json',result)
    print({'key':a.key,'players':a.players,'smoke':a.smoke,'games':games,
        'seconds':{k:v['seconds'] for k,v in summary.items()},'search_evaluations':summary['search_geo']['search_stats']['search_geo']['evaluations']})


if __name__=='__main__':main()
