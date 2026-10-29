"""Select a small current-engine teacher pilot without reading any outcomes."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/auction-discount-teacher-prepared-v1'
PROTOCOL = ROOT/'ai/strong/auction-discount-teacher-protocol-v1.json'


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def object_hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path,value):
    with Path(path).open('x') as stream: json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    assert not OUT.exists() and not PROTOCOL.exists(), 'Inspect prior pilot preparation'
    selected=ROOT/'ai/runs/policy-iteration-selected-v2'
    previous=read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    for name,sha in previous['roots']['files'].items(): assert digest(selected/name)==sha
    metadata_path=ROOT/'ai/runs/policy-iteration-features-v2/metadata.json'
    check=read(ROOT/'ai/runs/policy-iteration-features-v2/feature-check.json')
    assert digest(metadata_path)==check['artifacts']['metadata.json']
    metadata={r['rootId']:r for r in read(metadata_path)}
    buckets=defaultdict(list)
    with gzip.open(selected/'roots.jsonl.gz','rt') as stream:
        for line in stream:
            root=json.loads(line)
            if root['decision']!='nomination': continue
            assert root['split']==('validation' if root['deal'] in (0,4,8,12) else 'train')
            assert root['gameSeed'].startswith('policy-iteration-training-v2-')
            assert object_hash(root['request'])==root['public_root_sha256']
            state=root['request']['state']
            if root['variant']=='original': kind='original_control'
            else:
                if not state['plantDiscountActive']: continue
                cheap=state['actualMarket'][0]['number']
                ix=[i for i,m in enumerate(root['legal']) if m['name']=='ChoosePowerPlant' and m['data']==cheap]
                if not ix: continue
                assert len(ix)==1
                kind='discount_included' if ix[0] in metadata[root['rootId']]['options'] else 'discount_excluded'
            key=(root['split'],root['players'],root['sealed'],kind)
            buckets[key].append(root)
    keys={(split,n,sealed,kind) for split in ('train','validation') for n in range(2,7)
          for sealed in (False,True) for kind in ('original_control','discount_included','discount_excluded')}
    assert set(buckets)==keys
    roots=[]
    for key in sorted(keys):
        root=min(buckets[key],key=lambda r:hashlib.sha256(('auction-discount-teacher-v1:'+r['rootId']).encode()).hexdigest())
        roots.append({'rootId':root['rootId'],'players':root['players'],'sealed':root['sealed'],
            'variant':root['variant'],'split':root['split'],'deal':root['deal'],'kind':key[3],
            'source_game_seed':root['gameSeed'],'public_root_sha256':root['public_root_sha256'],
            'request':root['request'],'legal':root['legal'],
            'old_label_options':metadata[root['rootId']]['options']})
    historical=[]
    for version in (1,2):
        path=ROOT/f'ai/runs/auction-training-history-v{version}/newly-affordable-roots.jsonl'
        historical.append({'file':str(path.relative_to(ROOT)),'sha256':digest(path)})
        for index,line in enumerate(path.read_text().splitlines()):
            root=json.loads(line)
            assert root['labelled'] is False and root['variant']=='recharged'
            assert root['split']==('validation' if root['deal'] in (0,4,8,12) else 'train')
            assert root['gameSeed'].startswith('policy-iteration-training-v2-')
            roots.append({'rootId':f'natural-discount-v{version}-{index:02d}','players':root['players'],
                'sealed':root['sealed'],'variant':root['variant'],'split':root['split'],'deal':root['deal'],
                'kind':'newly_affordable','source_game_seed':root['gameSeed'],
                'public_root_sha256':object_hash(root['request']),'request':root['request'],'legal':root['legal'],
                'old_label_options':None})
    assert len(roots)==70 and len({r['rootId'] for r in roots})==70
    assert len({r['public_root_sha256'] for r in roots})==70
    assert Counter(r['split'] for r in roots)=={'train':36,'validation':34}
    OUT.mkdir(); save(OUT/'roots.json',roots)
    source=read(ROOT/'ai/strong/current-auction-grid-source-v1.json')
    artifact=ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
    protocol={'version':1,'created_at':datetime.now(timezone.utc).isoformat(),
        'purpose':'Measure current-engine all-legal nomination teachers before discount-aware training.',
        'selection':'One SHA-ranked root per split/count/auction/coverage cell, plus all ten separately recovered natural low-cash roots; no outcome filtering.',
        'roots':{'file':str((OUT/'roots.json').relative_to(ROOT)),'sha256':digest(OUT/'roots.json'),
                 'count':70,'splits':{'train':36,'validation':34}},
        'parent_roots':previous['roots'],'historical_roots':historical,
        'current_source':{k:source[k] for k in ('repo','revision','archive','sha256','source_manifest_sha256')},
        'artifact_manifest_sha256':digest(artifact/'manifest.json'),
        'teacher_policy':'policies/conservative_population.json',
        'teacher_policy_sha256':digest(artifact/'policies/conservative_population.json'),
        'teacher':'Frozen current-engine population continuations with every legal nomination/Pass; retain full terminal outcomes and negative/uncertain margins.',
        'pilot':{'worlds':4,'workers':4,'threads':1,'max_steps':2400,'mode':'neural_population'},
        'full_teacher_proposal':{'worlds':64,'independent_halves':[[0,32],[32,64]],'requires_pilot_review':True},
        'candidate_experiment':'After reliable current-engine labels: compare identical warm starts with/without discount inputs and with old/all-legal nomination coverage; freeze the parent and train correction heads on HF only.',
        'evaluation':'New whole-game development deals across 2–6 players, both editions and auction modes, against unchanged model and independent opponents. Current confirmation and reserved final deals never become training data.',
        'no_target_reuse_from_old_engine':True,'pilot_targets_training_ready':False,
        'new_gradient_updates':0,'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}
    save(PROTOCOL,protocol)
    print(json.dumps({'roots':70,'split_counts':protocol['roots']['splits'],
        'max_legal_options':max(len(r['legal']) for r in roots),'gradients':0}),flush=True)


if __name__=='__main__':main()
