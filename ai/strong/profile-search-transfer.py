"""Admit each search48 matchup only after independent full-game HF smoke checks."""
import argparse
import math
from search_transfer import ROOT,PROTOCOL,read,write,digest,summarize_run,module

checks=module('transfer_runtime_summary','collect-discard-correction-screen.py')
p=argparse.ArgumentParser(__doc__);p.add_argument('--cases',nargs='+',choices=['heuristic-2p','search_geo-2p','a260-3p'])
a=p.parse_args();protocol=read(PROTOCOL);source=read(ROOT/'ai/strong/search-transfer-source-v1.json')
cases=a.cases or [c['id'] for c in protocol['cases']];assert len(set(cases))==len(cases)
profiles,admission={},{}
for case in protocol['cases']:
    name=case['id']
    if name not in cases:continue
    out=ROOT/f'ai/runs/search-transfer-smoke-verified-v1/{name}';saved=read(out/'verified.json')
    assert saved['verified'] and saved['smoke'] and saved['key']=='10102' and saved['case']==name
    assert saved['source_revision']==source['revision'] and saved['source_sha256']==source['sha256']
    assert saved['protocol_sha256']==digest(PROTOCOL) and saved['game_truncations']==saved['search_truncations']==0
    for file,sha in saved['artifacts'].items():
        assert '/' not in file and '\\' not in file and digest(out/file)==sha
    summary=summarize_run(out,protocol,'10102',case,True);checks.same_summary(summary,saved['summary'])
    seconds=summary['search']['seconds'];assert math.isfinite(seconds) and seconds>0
    projected=120+2*seconds*case['deals'];hours=max(4,math.ceil(projected/(.75*3600)))
    admission[name]={'projected_shard_seconds':projected,'timeout_hours':hours,'admitted':hours<=12,
        'basis':'Measured same-case search48 smoke; double linear runtime plus120s setup and25% timeout headroom. No game/search horizon change.'}
    profiles[name]={'revision':saved['revision'],'verified_sha256':digest(out/'verified.json'),'games':saved['games'],
        'seconds':seconds,'search_stats':summary['search']['search_stats']}
result={'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
    'profiles':profiles,'admission':admission,'verified':True,'all_cases_verified':len(cases)==len(protocol['cases']),
    'games':sum(r['games'] for r in profiles.values()),'game_truncations':0,'search_truncations':0,'qualification_eligible':False}
write(ROOT/'ai/strong/search-transfer-runtime-profile-v1.json',result);print(result)
