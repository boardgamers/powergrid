"""Guarded HF arenas, independent raw-record collection and paired comparisons."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess
from huggingface_hub import hf_hub_download
from strategic_correction_screen import (
    ROOT, PROTOCOL, SOURCE, read, write, digest, pin_hash, validate_pin, contract,
    case_key, prefix, verify_local, summarize, pairs,
)
from arena_statistics import validate_pairs, search_summary

PINS = ROOT/'ai/strong/strategic-correction-screen-pins-v1'
VERIFIED = ROOT/'ai/runs/strategic-correction-screen-verified-v1'


def get_pin(key):
    pin = read(PINS/(key+'.json'))
    validate_pin(pin, key, read(PROTOCOL))
    return pin


def folder(key, n, opponent, start, end, smoke=False):
    return VERIFIED/case_key(key, n, opponent, start, end, smoke)


def verify_saved(key, n, opponent, start, end, smoke):
    source, pin = read(SOURCE), get_pin(key)
    out = folder(key, n, opponent, start, end, smoke)
    saved = read(out/'verified.json')
    assert saved['verified'] and saved['source_revision'] == source['revision'] and saved['source_sha256'] == source['sha256']
    assert saved['protocol_sha256'] == digest(PROTOCOL) and saved['model_pin_sha256'] == pin_hash(pin)
    assert re.fullmatch('[0-9a-f]{40}', saved['revision'])
    assert saved['prefix'] == prefix(key, n, opponent, start, end, smoke)
    for name, sha in saved['artifacts'].items():
        assert Path(name).name == name and digest(out/name) == sha
    summary = verify_local(out, key, n, opponent, start, end, smoke, pin, source)
    from strategic_correction_screen import same
    same(summary, saved['summary'])
    return saved, summary


def admission(key):
    probes = {}
    for n in [2, 6]:
        saved, summary = verify_saved(key, n, 'search_geo', 0, 1, True)
        assert summary['games'] == 4*n and summary['seconds'] > 0 and math.isfinite(summary['seconds'])
        probes[str(n)] = {'revision': saved['revision'], 'seconds': summary['seconds'],
            'verified_sha256': digest(folder(key, n, 'search_geo', 0, 1, True)/'verified.json')}
    projected = 120+2*4*max(p['seconds'] for p in probes.values())
    hours = max(4, math.ceil(projected/(.75*3600)))
    return {'key': key, 'probes': probes, 'projected_seconds': projected,
        'timeout_hours': hours, 'admitted': hours <= 12,
        'scope': 'Same frozen candidate,2p/6p HF search smoke;2x worst endpoint linear projection for4 whole deals plus120s setup,25% timeout headroom. Planning only; no game cutoff changes.'}


def launch(a):
    source, protocol, pin = read(SOURCE), read(PROTOCOL), get_pin(a.key)
    check = read(ROOT/'ai/strong/strategic-correction-screen-preflight-v1.json')
    assert check['passed'] and check['games'] == 40 and check['nonzero_deal_offset_verified'] == 4
    assert check['source_revision'] == source['revision'] and check['source_sha256'] == source['sha256']
    assert digest(PROTOCOL) == source['protocol_sha256'] == check['protocol_sha256']
    assert all(digest(ROOT/name) == sha for name, sha in source['overlays'].items())
    contract(protocol, a.players, a.opponent, a.start, a.end, a.smoke)
    if a.smoke:
        assert a.players in [2, 6] and a.opponent == 'search_geo'
        runtime = {'timeout_hours': 4, 'admitted': True, 'scope': 'One whole deal for a measured runtime probe.'}
    else:
        runtime = admission(a.key)
        assert runtime['admitted'], 'Partition execution further; never reduce samples or game horizons'
    key = case_key(a.key, a.players, a.opponent, a.start, a.end, a.smoke)
    guards = ROOT/'ai/runs/strategic-correction-screen-launches-v1'
    guards.mkdir(exist_ok=True)
    guard = guards/(key+'.json')
    record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
        'key': a.key, 'players': a.players, 'opponent': a.opponent, 'start': a.start, 'end': a.end,
        'smoke': a.smoke, 'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'protocol_sha256': digest(PROTOCOL), 'model_pin_sha256': pin_hash(pin), 'model_pin': pin,
        'runtime_admission': runtime, 'timeout_hours': runtime['timeout_hours'], 'qualification_eligible': False}
    with guard.open('x') as stream:
        json.dump(record, stream, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance',
        '--timeout', str(runtime['timeout_hours'])+'h', '--secrets', 'HF_TOKEN',
        '--label', 'project=powergrid-ai', '--label', 'stage=strategic-correction-screen-v1-'+key]
    for name, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
        'SOURCE_SHA256': source['sha256'], 'MODEL_KEY': a.key, 'PLAYERS': str(a.players),
        'OPPONENT': a.opponent, 'START': str(a.start), 'END': str(a.end), 'SMOKE': '1' if a.smoke else '0',
        'MODEL_PIN': json.dumps(pin, sort_keys=True, separators=(',', ':')),
        'MODEL_PIN_SHA256': pin_hash(pin), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', name+'='+value]
    command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', '''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle: bundle.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
args=()
if [ "$SMOKE" = 1 ]; then args+=(--smoke); fi
python -u ai/strong/strategic_correction_screen.py "$MODEL_KEY" "$PLAYERS" "$OPPONENT" "$START" "$END" ai/runs/strategic-correction-screen-job "${args[@]}" --upload
''']
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        guard.with_suffix('.log').write_text(result.stdout+result.stderr)
        ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
        assert len(ids) == 1, 'Ambiguous launch: reconcile existing handles before retry'
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
        raise
    finally:
        write(guard, record)
    print({k:v for k,v in record.items() if k not in ['model_pin', 'runtime_admission']})


def collect(a):
    assert re.fullmatch('[0-9a-f]{40}', a.revision)
    source, protocol, pin = read(SOURCE), read(PROTOCOL), get_pin(a.key)
    contract(protocol, a.players, a.opponent, a.start, a.end, a.smoke)
    out = folder(a.key, a.players, a.opponent, a.start, a.end, a.smoke)
    out.mkdir(parents=True, exist_ok=False)
    remote = prefix(a.key, a.players, a.opponent, a.start, a.end, a.smoke)
    def fetch(name):
        assert Path(name).name == name
        target = out/name
        target.write_bytes(Path(hf_hub_download(protocol['repo'], remote+'/'+name, revision=a.revision)).read_bytes())
        return target
    status = read(fetch('screen-check.json'))
    for name, sha in status['artifacts'].items(): assert digest(fetch(name)) == sha
    summary = verify_local(out, a.key, a.players, a.opponent, a.start, a.end, a.smoke, pin, source)
    saved = {'verified': True, 'revision': a.revision, 'prefix': remote,
        'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'protocol_sha256': digest(PROTOCOL), 'model_pin_sha256': pin_hash(pin), 'model_pin': pin,
        'summary': summary, 'qualification_eligible': False,
        'artifacts': {p.name:digest(p) for p in out.iterdir() if p.is_file()}}
    write(out/'verified.json', saved)
    print({'case': out.name, **summary})


def compare():
    protocol, source = read(PROTOCOL), read(SOURCE)
    arms, raw, pending, provenance = {}, {}, [], {}
    for key in protocol['models']:
        arms[key], raw[key] = {}, {}
        for cell in protocol['screens']:
            n, opponent = cell['players'], cell['opponent']
            rows, pieces = [], []
            for start in range(0, cell['deals'], 4):
                out = folder(key, n, opponent, start, start+4)
                if not (out/'verified.json').exists():
                    pending.append(out.name)
                    continue
                saved, _ = verify_saved(key, n, opponent, start, start+4, False)
                pieces.append({'key': out.name, 'revision': saved['revision'], 'prefix': saved['prefix'],
                    'verified_sha256': digest(out/'verified.json'), 'evaluation_sha256': digest(out/'evaluation.json')})
                rows.extend(read(out/'evaluation.json')['results'])
            if len(pieces) != cell['deals']//4: continue
            validate_pairs(rows, n)
            assert len(rows) == cell['games'] and {r['episode'] for r in rows} == set(range(cell['games']))
            assert {r['gameSeed'] for r in rows} == {protocol['seed_template'].format(players=n)+'-'+str(i) for i in range(cell['deals'])}
            name = f'{opponent}/{n}p'
            raw[key][name] = rows
            provenance[key+'/'+name] = pieces
            arms[key][name] = {**summarize(rows, protocol), **search_summary(rows), 'stage': cell['stage'],
                'by_rules': {v+('/sealed' if s else '/open'): summarize(
                    [r for r in rows if r['variant'] == v and r['sealed'] == s], protocol)
                    for v in ['original', 'recharged'] for s in [False, True]}}
    comparisons = {}
    for key in ['11101', '11102']:
        comparisons[key+'-minus-parent'] = {}
        for cell, rows in raw[key].items():
            if cell not in raw['parent']: continue
            parent = raw['parent'][cell]
            def difference(a, b):
                return pairs.paired_difference(a, b, protocol['bootstrap_replicates'], protocol['bootstrap_seed'])
            comparisons[key+'-minus-parent'][cell] = {'overall': difference(rows, parent),
                'by_rules': {v+('/sealed' if s else '/open'): difference(
                    [r for r in rows if r['variant'] == v and r['sealed'] == s],
                    [r for r in parent if r['variant'] == v and r['sealed'] == s])
                    for v in ['original', 'recharged'] for s in [False, True]}}
    result = {'all_shards_verified': not pending, 'pending': pending, 'arms': arms, 'comparisons': comparisons,
        'games': sum(s['games'] for arm in arms.values() for s in arm.values()),
        'planned_games': protocol['planned_games_total'], 'source_revision': source['revision'],
        'source_sha256': source['sha256'], 'protocol_sha256': digest(PROTOCOL), 'provenance': provenance,
        'qualification_eligible': False, 'scope': protocol['analysis']}
    if not pending: assert result['games'] == protocol['planned_games_total']
    write(ROOT/'ai/strong/strategic-correction-screen-results-v1.json', result)
    print({'games': result['games'], 'pending_shards': len(pending), 'all_shards_verified': not pending})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['launch', 'collect']:
        p = sub.add_parser(name)
        p.add_argument('key', choices=['parent', '11101', '11102'])
        p.add_argument('players', type=int, choices=range(2, 7))
        p.add_argument('opponent')
        p.add_argument('start', type=int)
        p.add_argument('end', type=int)
        p.add_argument('--smoke', action='store_true')
        if name == 'collect': p.add_argument('revision')
    sub.add_parser('compare')
    args = parser.parse_args()
    if args.command == 'launch': launch(args)
    elif args.command == 'collect': collect(args)
    else: compare()
