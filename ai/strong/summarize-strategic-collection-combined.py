"""Account separately for whole-job and disjoint-deal collection provenance."""
import re
from strategic_collection import ROOT, PROTOCOL, read, write, digest

def summarize():
    p=read(PROTOCOL)
    whole=read(ROOT/'ai/strong/strategic-training-collection-results-v1.json')
    slice_source=read(ROOT/'ai/strong/strategic-training-collection-slices-source-v1.json')
    cases={}
    pending=[]
    for n in p['players']:
        for mode in p['modes']:
            key=f'{n}p-{mode}'
            merged=ROOT/f'ai/runs/strategic-training-collection-merged-v1/{key}'
            if key in whole['shards']:
                assert not (merged/'verified.json').exists(),'Duplicate whole and sliced coverage'
                folder=ROOT/f'ai/runs/strategic-training-collection-verified-v1/{key}'
                saved=read(folder/'verified.json');prior=whole['shards'][key]
                assert digest(folder/'verified.json')==prior['verified_sha256'] and saved['verified']
                assert saved['source_revision']==whole['source_revision'] and saved['source_sha256']==whole['source_sha256']
                assert re.fullmatch('[a-f0-9]{40}',saved['revision'])
                kind='whole_job'
            elif (merged/'verified.json').exists():
                assert mode=='search_geo' and n in [4,5,6]
                folder=merged;saved=read(folder/'verified.json')
                assert saved['verified'] and saved['kind']=='disjoint_deal_merge'
                assert saved['source_revision']==slice_source['revision'] and saved['source_sha256']==slice_source['sha256']
                assert sorted(d for piece in saved['pieces'] for d in range(piece['start'],piece['end']))==list(range(16))
                kind='disjoint_deal_merge'
            else:
                pending.append(key)
                continue
            assert saved['players']==n and saved['mode']==mode and saved['protocol_sha256']==digest(PROTOCOL)
            for name,sha in saved['artifacts'].items():
                assert folder.joinpath(name).name==name and digest(folder/name)==sha
            s=saved['summary']
            assert s['games']==n*4*16 and not s['game_truncations'] and not s['search_truncations']
            assert s['roots']==s['public_model_proposals_reproduced']>0
            cases[key]={'kind':kind,'summary':s,'source_revision':saved['source_revision'],
                'source_sha256':saved['source_sha256'],'verified_sha256':digest(folder/'verified.json'),
                'local_verified':str((folder/'verified.json').relative_to(ROOT)),
                'provenance':saved['pieces'] if kind=='disjoint_deal_merge' else {k:saved[k] for k in ['revision','prefix','artifacts']}}
    games=sum(c['summary']['games'] for c in cases.values())
    if not pending:assert games==p['unique_games']==3840
    result={'all_cases_verified':not pending,'cases':cases,'pending':pending,'unique_games':games,
        'engine_game_runs':2*games,'roots':sum(c['summary']['roots'] for c in cases.values()),
        'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False,'labels_generated':False,'trained':False,
        'scope':'Full collection coverage with explicit source provenance. Runtime probes excluded; no strength claim.'}
    write(ROOT/'ai/strong/strategic-training-collection-combined-results-v1.json',result)
    print({k:v for k,v in result.items() if k!='cases'})

if __name__=='__main__':summarize()
