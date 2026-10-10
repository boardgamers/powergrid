"""Download immutable search results and independently recheck all games/pairs."""
import argparse
import importlib.util
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from search_transfer import ROOT,PROTOCOL,read,write,digest,summarize_run,module

checks=module('transfer_summary_check','collect-discard-correction-screen.py')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102'])
    p.add_argument('case',choices=['heuristic-2p','search_geo-2p','a260-3p'])
    p.add_argument('revision');p.add_argument('output',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',a.revision)
    protocol=read(PROTOCOL);source=read(ROOT/'ai/strong/search-transfer-source-v1.json')
    case=next(c for c in protocol['cases'] if c['id']==a.case);pin=protocol['models'][a.key]
    prefix='runs/search-transfer-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.case}'
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    def fetch(name):
        assert Path(name).name==name
        path=out/name;path.write_bytes(Path(hf_hub_download(protocol['repo'],prefix+'/'+name,revision=a.revision)).read_bytes());return path
    status=read(fetch('search-transfer-check.json'))
    games=(1 if a.smoke else case['deals'])*4*case['players']
    for k,v in {'key':a.key,'case':a.case,'smoke':a.smoke,'status':'complete','games':games,
        'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],'source_sha256':source['sha256'],
        'game_truncations':0,'search_truncations':0,'trained':False,'qualification_eligible':False}.items():assert status[k]==v,k
    required={'checkpoint.json','search.json','summary.json'}|({'baseline.json'} if not a.smoke else set())
    assert required<=set(status['artifacts'])
    for name,sha in status['artifacts'].items():assert digest(fetch(name))==sha,name
    assert read(out/'checkpoint.json')==pin
    summary=summarize_run(out,protocol,a.key,case,a.smoke);checks.same_summary(summary,read(out/'summary.json'))
    result={'key':a.key,'case':a.case,'smoke':a.smoke,'games':games,'revision':a.revision,'prefix':prefix,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
        'summary':summary,'verified':True,'game_truncations':0,'search_truncations':0,'qualification_eligible':False,
        'artifacts':{p.name:digest(p) for p in out.iterdir() if p.is_file()}}
    write(out/'verified.json',result)
    print({'key':a.key,'case':a.case,'smoke':a.smoke,'games':games,'seconds':summary['search']['seconds'],
        'search_stats':summary['search']['search_stats'],
        **({'search_minus_raw':summary['search_minus_raw']['overall']} if not a.smoke else {})})


if __name__=='__main__':main()
