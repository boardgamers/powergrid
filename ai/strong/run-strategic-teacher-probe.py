"""HF-only runtime probe; no gradients, winner labels or qualification claims."""
import argparse
import json
import os
from pathlib import Path
import time
from huggingface_hub import HfApi
from strategic_collection import ROOT, get_model, read, write, digest, request_hash
from strategic_teacher import MODES, Node, prepare, evaluate

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7))
    p.add_argument('mode',choices=MODES);p.add_argument('output',type=Path);p.add_argument('--upload',action='store_true');a=p.parse_args()
    protocol_path=ROOT/'ai/strong/strategic-teacher-probe-protocol-v1.json';protocol=read(protocol_path)
    roots_pin=read(ROOT/'ai/strong/strategic-teacher-probe-roots-v1.json')
    assert digest(ROOT/roots_pin['file'])==roots_pin['sha256']==protocol['roots_sha256']
    model=get_model(protocol);root_rows=[json.loads(line) for line in (ROOT/roots_pin['file']).read_text().splitlines()]
    roots=[r for r in root_rows if r['players']==a.players]
    assert len(roots)==2 and {r['phase'] for r in roots}=={'auction','building'}
    assert all(r['split']=='validation' and request_hash(r['request'])==r['public_root_sha256'] for r in roots)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    node=Node('strong/strategic-continuations.cjs');rows=[]
    status={'status':'running','players':a.players,'mode':a.mode,'protocol_sha256':digest(protocol_path),
        'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'model_sha256':model.sha256,'roots_sha256':roots_pin['sha256'],'trained':False,
        'scope':'Small runtime probe. Validation-only roots; no teacher choice or training admission from these estimates.',
        'qualification_eligible':False}
    try:
        with (out/'rollouts.jsonl').open('w') as f:
            for root in roots:
                options=prepare(node,model,root)
                for batch in protocol['batches']:
                    row=evaluate(model,root,options,a.mode,batch,protocol['samples'],protocol['workers'])
                    rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
                    print({'root':root['rootId'],'batch':batch,'mode':a.mode,'usable':row['usable'],**row['timing']},flush=True)
        assert len(rows)==4 and all(r['usable'] for r in rows), 'Incomplete or capped evidence; do not admit full work'
        status.update(status='complete',positions=len(roots),searches=len(rows),
            evaluations=sum(len(r['rollouts']) for r in rows),
            nested_evaluations=sum(r['nested_search']['evaluations'] for r in rows),
            game_truncations=sum(r['outer_truncations'] for r in rows),
            nested_truncations=sum(r['nested_search']['truncated'] for r in rows),
            engine_seconds=sum(r['timing']['engine_seconds'] for r in rows),
            policy_seconds=sum(r['timing']['policy_seconds'] for r in rows),seconds=time.monotonic()-started)
    except BaseException as e:
        status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        node.close();status['artifacts']={q.name:digest(q) for q in out.iterdir() if q.is_file()}
        write(out/'probe-check.json',status)
        if a.upload:HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,
            path_in_repo=f'runs/strategic-teacher-probe-v1-{a.players}p-{a.mode}')
        print(status,flush=True)

if __name__=='__main__':main()
