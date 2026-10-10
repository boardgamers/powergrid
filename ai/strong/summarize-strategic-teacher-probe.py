"""Aggregate only independently verified runtime probes, retaining missing cases."""
from strategic_collection import ROOT, read, write, digest

p=read(ROOT/'ai/strong/strategic-teacher-probe-protocol-v1.json')
source=read(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json');cases={};pending=[]
for n in p['players']:
    for mode in p['modes']:
        key=f'{n}p-{mode}';folder=ROOT/f'ai/runs/strategic-teacher-probe-verified-v1/{key}'
        if not (folder/'verified.json').exists():pending.append(key);continue
        s=read(folder/'verified.json')
        assert s['verified'] and s['source_revision']==source['revision'] and s['source_sha256']==source['sha256']
        assert s['protocol_sha256']==source['protocol_sha256'] and not s['qualification_eligible']
        for name,sha in s['artifacts'].items():assert (folder/name).name==name and digest(folder/name)==sha
        summary=s['summary'];assert summary['players']==n and summary['mode']==mode
        assert summary['positions']==2 and summary['searches']==4
        assert summary['game_truncations']==summary['nested_truncations']==0
        cases[key]={**summary,'revision':s['revision'],'prefix':s['prefix'],
            'verified_sha256':digest(folder/'verified.json'),'artifacts':s['artifacts']}
result={'all_cases_verified':not pending,'cases':cases,'pending_cases':pending,
    'evaluations':sum(c['evaluations'] for c in cases.values()),
    'nested_evaluations':sum(c['nested_evaluations'] for c in cases.values()),
    'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':source['protocol_sha256'],
    'scope':'Partial runtime evidence only, two samples per batch on validation-only roots. No training or strength claim.',
    'qualification_eligible':False,'trained':False}
write(ROOT/'ai/strong/strategic-teacher-probe-results-v1.json',result)
print({k:v for k,v in result.items() if k!='cases'})
