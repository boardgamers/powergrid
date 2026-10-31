"""Single bounded HF learner-class probe; explicit prepare/launch/status/collect."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np
from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status

from checkpoint_bucket_archives_v3 import archive_directory, checked_receipt, download_archive
from current_auction_resource_job_v2 import tree
from target_learner_probe_v1 import read, save, digest, inputs, dense, metrics, route, json_predict

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/target-learner-probe-v1'
DESIGN = ROOT/'ai/strong/target-learner-probe-design-v1.json'
SOURCE = ROOT/'ai/strong/target-learner-probe-source-v1.json'
LAUNCH = ROOT/'ai/strong/target-learner-probe-launch-v1.json'
REPO = 'coyotte508/powergrid-ai-training-v1'
NAME = 'pg-target-learner-probe-v1'
BOOTSTRAP = r'''set -euo pipefail
python -m pip install --quiet huggingface_hub==2.0.0 numpy==1.26.4 scipy==1.14.1 xgboost==2.1.4
mkdir -p /workspace
python -B - <<'SOURCE'
import os,hashlib,json,tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
out=Path('/workspace/learner');assert not out.exists()
with tarfile.open(file) as bundle:
 members=bundle.getmembers();names=[m.name for m in members]
 assert len(names)==len(set(names)) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
 manifest=bundle.extractfile('manifest.json').read();assert hashlib.sha256(manifest).hexdigest()==os.environ['MANIFEST_SHA256']
 pins=json.loads(manifest);assert set(names)==set(pins)|{'manifest.json'}
 assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
 out.mkdir();bundle.extractall(out,filter='data')
SOURCE
python -u -B /workspace/learner/target_learner_probe_v1.py --bundle /workspace/learner --output /workspace/pg-target-learner-probe-v1
'''


def now(): return datetime.now(timezone.utc).isoformat()


def prepare():
    assert not LOCAL.exists() and not SOURCE.exists() and not DESIGN.exists(), 'Inspect any prior preparation/upload'
    analysis = read(ROOT/'ai/strong/target-generalization-analysis-v1.json')
    assert analysis['complete'] and analysis['fits_improving_train_but_worsening_validation_mse'] == 16
    data = ROOT/'ai/runs/nomination-discount-training-data-v1'; report = read(data/'report.json')
    assert all(digest(data/k) == v for k, v in report['files'].items())
    arrays = dict(np.load(data/'data.npz', allow_pickle=False)); meta = read(data/'metadata.json')
    x, rows, actions, weights, groups = inputs(arrays, meta)
    design = {'created_at': now(), 'purpose': 'Test a different learner class after all historical neural fits overfit. Existing targets only; no new nomination candidate iteration or deployment.',
        'analysis_sha256': digest(ROOT/'ai/strong/target-generalization-analysis-v1.json'),
        'data_report_sha256': digest(data/'report.json'), 'worker_sha256': digest(ROOT/'ai/strong/target_learner_probe_v1.py'),
        'depths': [3, 6], 'seeds': [27101, 27102], 'max_rounds': 500, 'early_stopping_rounds': 40,
        'parameters': {'objective': 'reg:squarederror', 'eval_metric': 'rmse', 'device': 'cuda', 'tree_method': 'hist',
            'eta': .03, 'min_child_weight': 5, 'lambda': 10., 'alpha': .1, 'subsample': .8,
            'colsample_bytree': .8, 'max_bin': 128, 'base_score': 0., 'nthread': 4, 'verbosity': 1},
        'split_counts': {k: len(v) for k, v in groups.items()},
        'split': 'Fit on original training deals except 11,13; tune stopping only on training deals 11,13; legacy validation deals 0,4,8,12 scored once after fitting. Entire source games and public-state hashes are separate.',
        'features': '1522 numeric public inputs: state 0:1215 and discount 1217; candidate action 0:100,101:103; parent action same indices; candidate-minus-parent. No target, root/seed/deal ID, opponent identity or shortlist/eligibility flags.',
        'loss': 'Existing soft paired terminal-credit advantages, uncertainty weights normalized to equal total per-root weight; parent rows excluded from fit and forced to zero on prediction.',
        'selection': 'Earliest minimum internal-tune RMSE checkpoint; retain both seeds and both depths, report their fixed mean ensembles with margin .025. No sweep/threshold tuning using legacy validation.',
        'limitations': 'Existing neural population nomination targets and historically used validation are diagnostic only. This cannot resolve opponent mismatch, qualify a policy or prove game strength. No model serving change.',
        'preflight': {'rows': len(rows), 'features': x.shape[1], 'new_gradients': 0, 'split_integrity': True},
        'versions': {'numpy': '1.26.4', 'scipy': '1.14.1', 'xgboost': '2.1.4', 'huggingface_hub': '2.0.0'},
        'documentation': 'https://xgboost.readthedocs.io/en/release_2.1.0/gpu/index.html',
        'estimated_minutes': [15, 30], 'estimate_is_provisional': True,
        'suggested_ping_paris': '2026-10-31T11:45:00+01:00', 'hard_timeout_seconds': 3600,
        'automatic_retries': False, 'new_simulations': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    save(DESIGN, design); LOCAL.mkdir(); bundle = LOCAL/'bundle'; bundle.mkdir()
    shutil.copyfile(ROOT/'ai/strong/target_learner_probe_v1.py', bundle/'target_learner_probe_v1.py')
    shutil.copyfile(DESIGN, bundle/'design.json'); shutil.copytree(data, bundle/'data')
    shutil.copytree(ROOT/'ai/runs/auction-discount-teacher-prepared-v1/bundle/transport', bundle/'transport')
    save(bundle/'manifest.json', {str(p.relative_to(bundle)): digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()})
    api = HfApi(); assert api.dataset_info(REPO).private
    remote = 'strong-source-target-learner-probe-v1.tgz'
    assert not api.file_exists(REPO, remote, repo_type='dataset')
    archive = archive_directory(bundle)
    save(LOCAL/'upload-intent.json', {'archive': remote, 'sha256': digest(archive), 'created_at': now(), 'automatic_retries': False})
    commit = api.upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=archive, path_in_repo=remote)
    save(LOCAL/'upload-commit.json', {'archive': remote, 'revision': commit.oid})
    assert digest(hf_hub_download(REPO, remote, repo_type='dataset', revision=commit.oid)) == digest(archive)
    save(SOURCE, {'repo': REPO, 'revision': commit.oid, 'archive': remote, 'sha256': digest(archive),
        'manifest_sha256': digest(bundle/'manifest.json'), 'design_sha256': digest(DESIGN), 'remote_archive_verified': True})
    print({'prepared': True, 'source_revision': commit.oid, 'bytes': archive.stat().st_size}, flush=True)


def launch():
    assert not LAUNCH.exists() and not (LOCAL/'launch-intent.json').exists(), 'Inspect original handle before retry'
    source = read(SOURCE); design = read(DESIGN)
    assert source['remote_archive_verified'] and source['design_sha256'] == digest(DESIGN)
    assert digest(ROOT/'ai/strong/target_learner_probe_v1.py') == design['worker_sha256']
    tree(LOCAL/'bundle', 'manifest.json', source['manifest_sha256'])
    env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
        'MANIFEST_SHA256': source['manifest_sha256'], 'POWERGRID_HF_TRAINING': '1', 'HF_HUB_DISABLE_PROGRESS_BARS': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '1'}
    config = {'image': 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'command': ['bash', '-lc', BOOTSTRAP],
        'env': env, 'flavor': 'l4x1', 'timeout': '1h', 'labels': {'name': NAME, 'project': 'powergrid-ai'}}
    save(LOCAL/'launch-intent.json', {'created_at': now(), 'config': config, 'source_sha256': digest(SOURCE), 'automatic_retries': False})
    token = get_token(); assert token; api = HfApi(); job = api.run_job(**config, secrets={'HF_TOKEN': token})
    record = {'created_at': now(), 'job_id': job.id, 'name': NAME, 'source_sha256': digest(SOURCE),
        'design_sha256': digest(DESIGN), 'manager_sha256': digest(__file__), 'intent_sha256': digest(LOCAL/'launch-intent.json'),
        'flavor': 'l4x1', 'timeout_seconds': 3600, 'estimated_minutes': design['estimated_minutes'],
        'suggested_ping_paris': design['suggested_ping_paris'], 'automatic_retries': False, 'qualified': False}
    save(LAUNCH, record)
    response = get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job.id}', headers=api._build_hf_headers(), timeout=60)
    hf_raise_for_status(response); raw = response.json()
    assert raw['id'] == job.id and raw['dockerImage'] == config['image'] and raw['flavor'] == config['flavor']
    assert raw['command'] == config['command'] and raw['environment'] == env and raw['timeout'] == 3600
    save(LOCAL/'effective-configuration.json', {'job_id': job.id, 'verified': True, 'stage': raw['status']['stage']})
    print({'job_id': job.id, 'stage': raw['status']['stage'], 'configuration_verified': True}, flush=True)


def observe(collect=False):
    launch = read(LAUNCH); api = HfApi(); stage = api.inspect_job(job_id=launch['job_id']).status.stage
    print({'job_id': launch['job_id'], 'stage': stage}, flush=True)
    if not collect or stage != 'COMPLETED': return
    out = LOCAL/'collected'; out.mkdir(exist_ok=True)
    log = out/'final.log'
    if not log.exists():
        with log.open('x') as f: f.write('\n'.join(api.fetch_job_logs(job_id=launch['job_id'], follow=False)))
    receipts = []
    for line in log.read_text().splitlines():
        try: row = json.loads(line)
        except ValueError: continue
        if isinstance(row, dict) and row.get('target_learner_complete'): receipts.append(row['bucket_evidence'])
    assert len(receipts) == 1, 'Inspect original job evidence; do not rerun training'
    receipt = receipts[0]; checked_receipt(receipt, NAME)
    if (out/'receipt.json').exists(): assert read(out/'receipt.json') == receipt
    else: save(out/'receipt.json', receipt)
    raw = out/'raw'
    if not raw.exists(): download_archive(receipt, NAME, raw, api)
    tree(raw, 'manifest.json', receipt['manifest_sha256'])
    result = read(raw/'training.json'); design = read(DESIGN); data_dir = LOCAL/'bundle/data'
    assert result['complete'] and result['training_location'] == 'HF Jobs' and result['training_device'] == 'cuda'
    assert result['design_sha256'] == digest(DESIGN) and result['data_report_sha256'] == design['data_report_sha256']
    assert all(digest(data_dir/f) == sha for f, sha in read(data_dir/'report.json')['files'].items())
    data = dict(np.load(data_dir/'data.npz', allow_pickle=False)); meta = read(data_dir/'metadata.json')
    x, rows, actions, _, groups = inputs(data, meta)
    predictions = dict(np.load(raw/'predictions.npz', allow_pickle=False)); checked = {}
    assert {m['name'] for m in result['members']} == {f'd{d}-s{s}' for d in design['depths'] for s in design['seeds']}
    for member in result['members']:
        name = member['name']; path = raw/f'{name}.json'; history = read(raw/f'{name}-history.json')
        assert digest(path) == member['model_sha256']
        assert member['selected_rounds'] == int(np.argmin(history['tune']['rmse']))+1
        assert member['fit_rounds'] == len(history['fit']['rmse']) <= design['max_rounds']
        actual = dense(json_predict(read(path), x), rows, actions, data)
        assert np.max(np.abs(actual-predictions[name])) < 1e-5
        np.testing.assert_array_equal(route(actual, data['mask'], data['proposal_index']),
            route(predictions[name], data['mask'], data['proposal_index']))
        checked[name] = actual
    for depth in design['depths']:
        name = f'd{depth}-mean'; actual = np.mean([checked[f'd{depth}-s{s}'] for s in design['seeds']], axis=0)
        assert np.max(np.abs(actual-predictions[name])) < 1e-5
        checked[name] = actual
    measurements = {name: {g: metrics(pred, data, ids) for g, ids in groups.items()} for name, pred in checked.items()}
    for member in result['members']:
        for g in groups:
            for k, v in member['metrics'][g].items(): assert abs(measurements[member['name']][g][k]-v) < 1e-5
    for depth in design['depths']:
        for g in groups:
            for k, v in result['ensembles'][f'd{depth}'][g].items(): assert abs(measurements[f'd{depth}-mean'][g][k]-v) < 1e-5
    report = {'complete': True, 'created_at': now(), 'job_id': launch['job_id'], 'independently_audited': True,
        'receipt': receipt, 'log_sha256': digest(log), 'training_report_sha256': digest(raw/'training.json'),
        'design_sha256': digest(DESIGN), 'source_sha256': digest(SOURCE), 'seconds': result['seconds'],
        'members': result['members'], 'metrics': measurements, 'new_simulations': 0,
        'qualified': False, 'reserved_final_seeds_used': False, 'scope': result['scope']}
    save(ROOT/'ai/strong/target-learner-probe-results-v1.json', report)
    print({'audited': True, 'models': len(result['members']), 'seconds': result['seconds']}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['prepare', 'launch', 'status', 'collect'])
    operation = p.parse_args().operation
    if operation == 'prepare': prepare()
    elif operation == 'launch': launch()
    else: observe(operation == 'collect')
