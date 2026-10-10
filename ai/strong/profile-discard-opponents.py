"""Use available verified HF endpoint timings for count-specific admission."""
import argparse
from pathlib import Path
from five_plant_screen import ROOT,read,write

protocol=read(ROOT/'ai/strong/discard-opponents-protocol-v1.json')
source=read(ROOT/'ai/strong/discard-opponents-source-v1.json')
p=argparse.ArgumentParser(__doc__)
p.add_argument('--players',nargs='+',type=int,choices=[2,6],default=[2,6])
a=p.parse_args();assert len(set(a.players))==len(a.players)
profiles={}
for n in a.players:
    verified=read(ROOT/f'ai/runs/discard-opponents-smoke-verified-v1/{n}p/verified.json')
    assert verified['verified'] and verified['smoke'] and verified['players']==n and verified['key']=='10102'
    assert verified['source_revision']==source['revision'] and verified['source_sha256']==source['sha256']
    assert verified['game_truncations']==verified['search_truncations']==0
    times={k:v['seconds'] for k,v in verified['summary'].items()}
    projection=sum(times[k]*deals for k,deals in protocol['opponents'].items())
    profiles[str(n)]={'revision':verified['revision'],'games':verified['games'],'seconds_by_opponent':times,
        'linear_full_shard_seconds':projection,'search_rollouts':verified['summary']['search_geo']['search_stats']['search_geo']['evaluations']}
admission={n:{'projected_shard_seconds':120+2*v['linear_full_shard_seconds'],
    'basis':'Measured same-count smoke, doubled linear projection plus120s setup'} for n,v in profiles.items()}
if set(profiles)=={'2','6'}:
    for n in [3,4,5]:admission[str(n)]={
        'projected_shard_seconds':max(r['projected_shard_seconds'] for r in admission.values()),
        'basis':'Conservative endpoint planning estimate; not a same-count runtime measurement'}
result={'source_revision':source['revision'],'source_sha256':source['sha256'],'profiles':profiles,
    'verified_players':a.players,'both_endpoints_verified':set(a.players)=={2,6},'admission':admission,
    'games':sum(v['games'] for v in profiles.values()),'game_truncations':0,'search_truncations':0,'verified':True,
    'max_projected_shard_seconds':120+2*max(v['linear_full_shard_seconds'] for v in profiles.values()),
    'interpretation':'Conservative planning estimate: two times the worse endpoint linear projection plus120s setup. Smoke2p has only8 concurrent games versus24 in full shards, so scaling should improve; counts3-5 and deal variation remain uncertain. Actual jobs have4h limits; preserve caps/timeouts rather than calling them losses.',
    'qualification_eligible':False}
write(ROOT/'ai/strong/discard-opponents-runtime-profile-v1.json',result);print(result)
