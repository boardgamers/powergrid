"""Prepare measured HF calibration admission, then submit each endpoint once."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download
from resource_development_v1 import PROTOCOL, verify_pins
from strategic_collection import ROOT, read, write, digest

STRONG = ROOT / 'ai/strong'
SOURCE = STRONG / 'resource-replanning-job-source-v1.json'
PREFLIGHT = STRONG / 'resource-job-source-preflight-evidence-v1.json'
PILOT = STRONG / 'resource-replanning-runtime-evidence-v1.json'
ADMISSION = STRONG / 'resource-replanning-hf-runtime-admission-v1.json'
GUARDS = ROOT / 'ai/runs/resource-replanning-hf-runtime-launches-v1'
HARDWARE = {
    'cpu-upgrade': {'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50},
    'cpu-xl': {'vcpus': 16, 'ram_gb': 124, 'disk_gb': 1000},
}
BOOTSTRAP = r'''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib,json
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt',filter='data')
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(file) as bundle:bundle.extractall('/workspace',filter='data')
root=Path('/workspace')
manifest=root/'resource-job-manifest.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==os.environ['SOURCE_MANIFEST_SHA256']
files=json.loads(manifest.read_text())
assert len(files)==1484
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in files.items())
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/resource-replanning-development-job-v1.py resource-filter "$PLAYERS" search_geo 0 1 --runtime-pilot
'''


def prerequisites():
    assert PILOT.exists(), 'The complete local 64-game / 16-replay pilot must be archived first'
    pilot, source, preflight = read(PILOT), read(SOURCE), read(PREFLIGHT)
    verify_pins(read(PROTOCOL))
    assert pilot['complete'] and pilot['games'] == 64 and pilot['independent_replays'] == 16
    assert pilot['all_pairs_complete'] and pilot['caps'] == 0
    assert set(pilot['cells']) == {f'{n}p-{arm}' for n in (2, 6) for arm in ('filter', 'resource-filter')}
    assert pilot['remote_archive_verified'] and source['remote_archive_verified']
    assert preflight['remote_archive_verified'] and preflight['complete_preflight']
    assert preflight['source'] == source and source['base'] == pilot['source']
    assert digest(PROTOCOL) == source['protocol_sha256'] == pilot['protocol_sha256']
    assert source['runtime_admitted'] is source['development_admitted'] is False
    assert all(digest(ROOT / name) == sha for name, sha in source['new_files'].items())
    assert all(digest(ROOT / name) == sha for name, sha in source['base']['new_files'].items())
    assert digest(ROOT / 'ai/runs' / source['archive']) == source['sha256']
    for descriptor, directory in ((pilot, 'resource-replanning-runtime-evidence-v1'),
                                  (preflight, 'resource-job-source-preflight-evidence-v1')):
        folder = ROOT / 'ai/runs' / directory
        assert digest(folder.with_suffix('.tgz')) == descriptor['archive_sha256']
        assert digest(folder / 'manifest.json') == descriptor['manifest_sha256']
        assert all(digest(folder / name) == sha for name, sha in read(folder / 'manifest.json').items())
    return pilot, source, preflight


def measured_admission(pilot, flavor, timeout_hours):
    assert flavor in HARDWARE and type(timeout_hours) is int and 1 <= timeout_hours <= 12
    hardware = HARDWARE[flavor]
    measurements = {str(n): {key: pilot['cells'][f'{n}p-resource-filter'][key]
                            for key in ('runtime', 'raw_evaluation_bytes')} for n in (2, 6)}
    # These margins select a calibration budget; they are not measured HF performance.
    peak = max(cell['runtime']['sampled_peak_total_rss_bytes'] for cell in measurements.values())
    assert peak > 0 and 2 * peak <= hardware['ram_gb'] * 10**9, 'Need more measured memory headroom'
    floor = 900 + 2 * max(max(cell['runtime']['seconds'], cell['runtime']['cpu_seconds'] / hardware['vcpus'])
                         for cell in measurements.values())
    assert timeout_hours * 3600 >= floor, 'Need more runtime headroom for calibration'
    raw = max(cell['raw_evaluation_bytes'] for cell in measurements.values())
    assert 0 < raw and 4 * raw <= hardware['disk_gb'] * 10**9, 'Need more artifact-storage headroom'
    return {'flavor': flavor, **hardware, 'timeout_hours': timeout_hours,
            'local_endpoint_measurements': measurements, 'estimated_timeout_floor_seconds': floor,
            'measurement_scope': 'Complete local HX370 endpoint pilot, not HF performance or AMD8840U latency.',
            'headroom': 'Two times measured summed RSS; 15 min setup plus twice max(local wall, CPU/vCPU); four times raw evidence bytes. Calibration only, no guarantee of remote runtime.'}


def prepare(flavor, timeout_hours):
    pilot, source, _ = prerequisites()
    assert not ADMISSION.exists(), 'Preserve an existing admission; do not overwrite it'
    plan = {'created_at': datetime.now(timezone.utc).isoformat(),
            'purpose': 'Two HF runtime-only endpoint jobs; all outcomes excluded from playing strength.',
            'players': [2, 6], 'arm': 'resource-filter', 'opponent': 'search_geo', 'start': 0, 'end': 1,
            'games': 32, 'workers': 8, 'search_workers': 1, 'samples': 8, 'max_concurrent_jobs': 2,
            'source_descriptor_sha256': digest(SOURCE), 'source_revision': source['revision'],
            'local_pilot_descriptor_sha256': digest(PILOT), 'preflight_descriptor_sha256': digest(PREFLIGHT),
            'protocol_sha256': digest(PROTOCOL), 'launcher_sha256': digest(__file__),
            'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'hardware': measured_admission(pilot, flavor, timeout_hours),
            'automatic_retries': False, 'development_admitted': False, 'gradients': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with ADMISSION.open('x') as stream:
        json.dump(plan, stream, indent=2)
        stream.write('\n')
    print({'admission': str(ADMISSION), 'flavor': flavor, 'timeout_hours': timeout_hours, 'jobs_launched': 0})


def launch(players, execute):
    assert type(players) is int and players in (2, 6)
    pilot, source, _ = prerequisites()
    assert ADMISSION.exists(), 'Prepare and review measured runtime admission before submission'
    plan = read(ADMISSION)
    assert plan['source_descriptor_sha256'] == digest(SOURCE)
    assert plan['local_pilot_descriptor_sha256'] == digest(PILOT)
    assert plan['preflight_descriptor_sha256'] == digest(PREFLIGHT)
    assert plan['protocol_sha256'] == digest(PROTOCOL) and plan['source_revision'] == source['revision']
    assert plan['launcher_sha256'] == digest(__file__)
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['players'] == [2, 6] and plan['max_concurrent_jobs'] == 2 and plan['games'] == 32
    assert (plan['arm'], plan['opponent'], plan['start'], plan['end']) == ('resource-filter', 'search_geo', 0, 1)
    assert (plan['workers'], plan['search_workers'], plan['samples']) == (8, 1, 8)
    for key in ('automatic_retries', 'development_admitted', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'):
        assert plan[key] is False
    hw = plan['hardware']
    assert measured_admission(pilot, hw['flavor'], hw['timeout_hours']) == hw
    case = f'resource-replanning-hf-runtime-v1-{players}p-resource-filter'
    record = {'case': case, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
              'admission': plan, 'admission_sha256': digest(ADMISSION), 'players': players,
              'source': source, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    if not execute:
        print({'case': case, 'admitted': True, 'execute': False, 'hardware': hw})
        return
    token = get_token()
    assert token
    assert digest(hf_hub_download(source['repo'], source['archive'], repo_type='dataset', revision=source['revision'])) == source['sha256']
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active, api = 0, HfApi()
        for path in GUARDS.glob('*.json'):
            previous = read(path)
            assert previous['stage'] == 'launched', 'Reconcile an unresolved submission; do not retry'
            stage = api.inspect_job(job_id=previous['job_id']).status.stage
            assert stage not in ('ERROR', 'CANCELED', 'CANCELLED', 'DELETED'), 'Review failed jobs before proceeding'
            active += stage != 'COMPLETED'
        assert active < plan['max_concurrent_jobs']
        guard = GUARDS / (case + '.json')
        with guard.open('x') as stream:
            json.dump(record, stream, indent=2)
        try:
            job = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=hw['flavor'], timeout=f"{hw['timeout_hours']}h", name=case,
                secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'resource-runtime-v1', 'case': case},
                env={'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                     'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['manifest_sha256'],
                     'PROTOCOL_SHA256': plan['protocol_sha256'], 'PLAYERS': str(players), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'})
            record.update(stage='launched', job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
            raise
        finally:
            write(guard, record)
    print({'case': case, 'job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--flavor', choices=HARDWARE, required=True)
    prepare_parser.add_argument('--timeout-hours', type=int, required=True)
    launch_parser = commands.add_parser('launch')
    launch_parser.add_argument('players', type=int, choices=[2, 6])
    launch_parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.flavor, args.timeout_hours)
    else:
        launch(args.players, args.execute)
