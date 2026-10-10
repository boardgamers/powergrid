"""Merge all disjoint collection deals, retaining immutable per-piece provenance."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
from strategic_collection_slices import ROOT, PROTOCOL, SOURCE, read, write, digest, verify_games


def check_ranges(pieces, deals):
    assert pieces and all(type(p['start']) is int and type(p['end']) is int and 0 <= p['start'] < p['end'] <= deals for p in pieces)
    assert sorted(d for p in pieces for d in range(p['start'],p['end'])) == list(range(deals)), 'Missing/overlapping deals'


def assemble(pieces, n, mode, out, deals=16):
    """Pieces must already have been independently verified by the caller."""
    check_ranges(pieces,deals)
    pieces=sorted(pieces,key=lambda p:p['start'])
    p=read(PROTOCOL)
    games=[]
    seen_games=set()
    for piece in pieces:
        rows=read(piece['folder']/'games.json')
        verify_games(rows,p,n,mode,False,piece['start'],piece['end'])
        for row in rows:
            assert row['episode'] not in seen_games
            seen_games.add(row['episode'])
            games.append({**row,'source_piece_start':piece['start']})
    verify_games(games,p,n,mode,False,0,deals)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'games.json',sorted(games,key=lambda r:r['episode']))
    count=0
    seen_roots=set()
    ordinals=Counter()
    counts=Counter()
    with gzip.open(out/'roots.jsonl.gz','wt') as output:
        for piece in pieces:
            local_count=0
            with gzip.open(piece['folder']/'roots.jsonl.gz','rt') as roots:
                for row in map(json.loads,roots):
                    assert row['rootIndex']==local_count
                    assert row['players']==n and row['mode']==mode
                    assert piece['start'] <= row['deal'] < piece['end']
                    assert row['deal']==row['episode']//(4*n) and row['episode'] in seen_games
                    assert row['ordinal']==ordinals[row['episode']]
                    assert row['rootId']==f"{n}:{mode}:{row['episode']}:{row['ordinal']}" and row['rootId'] not in seen_roots
                    assert row['split']==('validation' if row['deal'] in p['validation_deal_indices'] else 'train')
                    assert 'source_piece_start' not in row and 'source_root_index' not in row
                    merged={**row,'source_piece_start':piece['start'],'source_root_index':local_count,'rootIndex':count}
                    output.write(json.dumps(merged)+'\n')
                    counts[row['phase'],row['split']]+=1
                    seen_roots.add(row['rootId']);ordinals[row['episode']]+=1
                    local_count+=1;count+=1
            assert local_count==piece['roots']
    # Independently reread output and compare with source records, except the explicit order index.
    with gzip.open(out/'roots.jsonl.gz','rt') as merged:
        index=0
        for piece in pieces:
            with gzip.open(piece['folder']/'roots.jsonl.gz','rt') as original:
                for local_index,line in enumerate(original):
                    source=json.loads(line);row=json.loads(next(merged))
                    assert row.pop('rootIndex')==index
                    assert row.pop('source_piece_start')==piece['start']
                    assert row.pop('source_root_index')==local_index
                    row['rootIndex']=local_index
                    assert row==source
                    index+=1
        assert next(merged,None) is None and index==count
    expected_games={r['episode']:{**r,'source_piece_start':piece['start']}
        for piece in pieces for r in read(piece['folder']/'games.json')}
    assert {r['episode']:r for r in read(out/'games.json')}==expected_games
    return {'games':len(games),'engine_game_runs':len(games)*2,'roots':count,
        'public_model_proposals_reproduced':count,'root_counts':{phase:{split:counts[phase,split] for split in ['train','validation']}
            for phase in ['auction','building']},'games_with_roots':len(ordinals),
        'game_truncations':0,'search_truncations':0,'all_source_games_and_roots_preserved':True,
        'source_root_index_preserved':True,'qualification_eligible':False}


def merge(n):
    p,source=read(PROTOCOL),read(SOURCE)
    plan=read(ROOT/f'ai/strong/strategic-training-collection-slices-{n}p-plan-v1.json')
    assert plan['source_sha256']==source['sha256'] and plan['source_revision']==source['revision']
    assert plan['protocol_sha256']==digest(PROTOCOL)
    check_ranges(plan['pieces'],p['deals_per_shard'])
    pieces=[]
    for part in plan['pieces']:
        folder=ROOT/f"ai/runs/strategic-training-collection-slices-verified-v1/{n}p-search_geo-{part['start']}-{part['end']}"
        saved=read(folder/'verified.json')
        for key,value in {'verified':True,'players':n,'start':part['start'],'end':part['end'],
            'source_revision':source['revision'],'source_sha256':source['sha256'],
            'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False}.items():
            assert saved[key]==value,key
        assert re.fullmatch('[a-f0-9]{40}',saved['revision'])
        for name,sha in saved['artifacts'].items():
            assert Path(name).name==name and digest(folder/name)==sha
        summary=saved['summary']
        assert summary['game_truncations']==summary['search_truncations']==0
        assert summary['roots']==summary['public_model_proposals_reproduced']>0
        pieces.append({**part,'folder':folder,'roots':summary['roots'],'verified':saved,'verified_sha256':digest(folder/'verified.json')})
    out=ROOT/f'ai/runs/strategic-training-collection-merged-v1/{n}p-search_geo'
    summary=assemble(pieces,n,'search_geo',out,p['deals_per_shard'])
    expected_roots=sum(piece['roots'] for piece in pieces)
    assert summary['roots']==expected_roots and summary['games']==4*n*p['deals_per_shard']
    record={'verified':True,'kind':'disjoint_deal_merge','players':n,'mode':'search_geo','summary':summary,
        'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],'source_sha256':source['sha256'],
        'pieces':[{k:v for k,v in piece.items() if k!='folder'} for piece in pieces],
        'artifacts':{q.name:digest(q) for q in out.iterdir() if q.is_file()},'qualification_eligible':False,
        'scope':'Exact verified source records; global rootIndex normalized, original piece/root index retained. No new games or strength claim.'}
    write(out/'verified.json',record)
    print(summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('players',type=int,choices=range(4,7))
    merge(parser.parse_args().players)
