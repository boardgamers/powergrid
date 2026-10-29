"""Publish the verified development overlay and submit fixed original shards."""
import argparse
from datetime import datetime, timezone
import json
from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status
from checkpoint_bucket_archives_v3 import archive_directory
from launch_auction_discount_teacher_v1 import bootstrap as base_bootstrap
from prepare_nomination_development_v1 import ROOT, OUT, PROTOCOL
from prepare_auction_discount_teacher_v2 import read, save, digest

SOURCE = ROOT/'ai/strong/nomination-discount-development-source-v1.json'
LAUNCH = ROOT/'ai/strong/nomination-discount-development-launch-v1.json'
REPO = 'coyotte508/powergrid-ai-training-v1'


def bootstrap():
    return base_bootstrap().split("python -B - <<'PILOT'")[0]+r'''python -B - <<'OVERLAY'
import hashlib,json,os,tarfile,shutil
from pathlib import Path
from huggingface_hub import hf_hub_download
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['DEV_ARCHIVE'],repo_type='dataset',revision=os.environ['DEV_REVISION'])
assert digest(file)==os.environ['DEV_SHA256']
root=Path('/workspace/nomination-development');assert not root.exists()
with tarfile.open(file) as bundle:
 members=bundle.getmembers();names=[m.name for m in members]
 assert len(names)==len(set(names)) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
 manifest=bundle.extractfile('manifest.json').read();assert hashlib.sha256(manifest).hexdigest()==os.environ['DEV_MANIFEST_SHA256']
 pins=json.loads(manifest);assert set(names)==set(pins)|{'manifest.json'}
 assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
 root.mkdir();bundle.extractall(root,filter='data')
overlay=json.loads((root/'overlay.json').read_text());artifact=Path('/workspace/source/artifact')
assert digest(artifact/'manifest.json')==overlay['expected_base_manifest_sha256']
for name,pin in overlay['files'].items():
 target=artifact/name
 assert (digest(target) if target.exists() else None)==pin['before']
 assert digest(root/'overlay'/name)==pin['after']
for name in overlay['files']:
 target=artifact/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'overlay'/name,target)
assert all(digest(artifact/name)==sha for name,sha in json.loads((artifact/'manifest.json').read_text()).items())
OVERLAY
python -u -B /workspace/nomination-development/run_nomination_development_v1.py --bundle /workspace/nomination-development --artifact /workspace/source/artifact --output "/workspace/$DEV_NAME" --name "$DEV_NAME" --execute --upload
'''


def checked():
    protocol = read(PROTOCOL); serving = read(ROOT/'ai/strong/nomination-discount-serving-v1.json')
    assert serving['complete'] and serving['count_rule_cells'] == 20
    assert serving['protocol_sha256'] == digest(PROTOCOL) == digest(OUT/'bundle/protocol.json')
    assert digest(OUT/'bundle/run_nomination_development_v1.py') == digest(ROOT/'ai/strong/run_nomination_development_v1.py')
    pins = read(OUT/'bundle/manifest.json'); assert all(digest(OUT/'bundle'/n) == h for n, h in pins.items())
    return protocol


def publish():
    protocol = checked(); assert not SOURCE.exists() and not (OUT/'upload-intent.json').exists()
    api = HfApi(); remote = 'strong-source-nomination-discount-development-v1.tgz'
    assert api.dataset_info(REPO).private and not api.file_exists(REPO, remote, repo_type='dataset')
    archive = archive_directory(OUT/'bundle')
    save(OUT/'upload-intent.json', {'archive': remote, 'sha256': digest(archive)})
    commit = api.upload_file(repo_id=REPO, repo_type='dataset', path_in_repo=remote, path_or_fileobj=archive)
    save(OUT/'upload-commit.json', {'revision': commit.oid, 'archive': remote})
    assert digest(hf_hub_download(REPO, remote, repo_type='dataset', revision=commit.oid)) == digest(archive)
    save(SOURCE, {'repo': REPO, 'revision': commit.oid, 'archive': remote, 'sha256': digest(archive),
                 'manifest_sha256': digest(OUT/'bundle/manifest.json'), 'protocol_sha256': digest(PROTOCOL),
                 'serving_check_sha256': digest(ROOT/'ai/strong/nomination-discount-serving-v1.json'), 'remote_archive_verified': True})
    print({'published': True, 'revision': commit.oid, 'bytes': archive.stat().st_size}, flush=True)


def launch(limit):
    assert 1 <= limit <= 50
    protocol = checked(); source = read(SOURCE); assert source['protocol_sha256'] == digest(PROTOCOL)
    folder = OUT/'launches'; folder.mkdir(exist_ok=True); api = HfApi(); submitted = 0
    # The first two are the new all-legal model against search at the count endpoints.
    pilot_names = [f'pg-nom-dev-v1-d1-all1-search-geo-{n}p' for n in (2, 6)]
    rows = sorted(protocol['rows'], key=lambda r: (pilot_names.index(r['name']) if r['name'] in pilot_names else 2, r['name']))
    for row in rows:
        name = row['name']; receipt = folder/(name+'.json'); intent = folder/(name+'.intent.json')
        if receipt.exists():
            record = read(receipt); check = read(folder/(name+'.checked.json'))
            assert record['source_sha256'] == digest(SOURCE) and check['job_id'] == record['job_id'] and check['effective_configuration_verified']
            continue
        assert not intent.exists(), 'Inspect ambiguous original launch, do not duplicate'
        if name not in pilot_names:
            for pilot in pilot_names:
                audit = read(ROOT/f'ai/runs/nomination-discount-development-collected-v1/{pilot}/audit.json')
                assert audit['independently_audited'] and audit['protocol_sha256'] == digest(PROTOCOL) and audit['caps'] == 0
        base = protocol['base_source']
        env = {'SOURCE_ARCHIVE': base['archive'], 'SOURCE_REVISION': base['revision'], 'SOURCE_SHA256': base['sha256'],
            'SOURCE_MANIFEST_SHA256': base['source_manifest_sha256'], 'DEV_ARCHIVE': source['archive'],
            'DEV_REVISION': source['revision'], 'DEV_SHA256': source['sha256'], 'DEV_MANIFEST_SHA256': source['manifest_sha256'],
            'DEV_NAME': name, 'POWERGRID_HF_DEVELOPMENT': '1', 'HF_HUB_DISABLE_PROGRESS_BARS': '1',
            'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
        config = {'image': 'python:3.11-slim-bookworm', 'command': ['bash', '-lc', bootstrap()], 'env': env,
                  'flavor': protocol['flavor'], 'timeout': protocol['timeout'], 'labels': {'name': name, 'project': 'powergrid-ai'}}
        save(intent, {'created_at': datetime.now(timezone.utc).isoformat(), 'config': config, 'source_sha256': digest(SOURCE), 'automatic_retries': False})
        token = get_token(); assert token
        job = api.run_job(**config, secrets={'HF_TOKEN': token})
        record = {'name': name, 'job_id': job.id, 'row': row, 'source_sha256': digest(SOURCE), 'intent_sha256': digest(intent)}
        save(receipt, record)
        response = get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job.id}', headers=api._build_hf_headers(), timeout=60)
        hf_raise_for_status(response); raw = response.json()
        assert raw['dockerImage'] == config['image'] and raw['flavor'] == config['flavor'] and raw['timeout'] == 18000
        assert raw['command'] == config['command'] and raw['environment'] == env and raw['labels']['name'] == name
        save(folder/(name+'.checked.json'), {'job_id': job.id, 'stage': raw['status']['stage'], 'effective_configuration_verified': True})
        records = [read(folder/(r['name']+'.json')) for r in rows if (folder/(r['name']+'.json')).exists()]
        summary = {'source': source, 'protocol_sha256': digest(PROTOCOL), 'jobs': records, 'planned_jobs': 50,
                   'submitted_jobs': len(records), 'planned_games': 3200, 'submitted_games': sum(r['row']['shard']['games'] for r in records),
                   'automatic_retries': False, 'qualified': False, 'reserved_final_seeds_used': False}
        temp = LAUNCH.with_suffix('.tmp'); temp.write_text(json.dumps(summary, indent=2)+'\n'); temp.replace(LAUNCH)
        print({'name': name, 'job_id': job.id, 'stage': raw['status']['stage']}, flush=True)
        submitted += 1
        if submitted == limit: break


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--publish-source', action='store_true'); g.add_argument('--launch', type=int); a = p.parse_args()
    if a.publish_source: publish()
    else: launch(a.launch)
