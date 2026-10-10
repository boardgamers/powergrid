"""Guarded launches and independent collection of the 3–6p search extension."""
import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import subprocess

from huggingface_hub import hf_hub_download
from multiplayer_search_transfer import ROOT, PROTOCOL, read, write, digest, case_for, verify
from search_transfer import module, pairs

SOURCE = ROOT/'ai/strong/multiplayer-search-transfer-source-v1.json'
RAW_ROOT = ROOT/'ai/runs/discard-opponents-verified-v1'
SMOKE_ROOT = ROOT/'ai/runs/multiplayer-search-transfer-smoke-verified-v1'
FULL_ROOT = ROOT/'ai/runs/multiplayer-search-transfer-verified-v1'
checks = module('mp_search_summary_checks', 'collect-discard-correction-screen.py')
raw_checks = module('mp_search_raw_checks', 'collect-discard-opponents.py')


def raw_baseline(key, n, protocol):
    contract = protocol['baseline_contract']
    assert contract['source'] == read(ROOT/'ai/strong/discard-opponents-source-v1.json')
    assert contract['protocol_sha256'] == digest(ROOT/'ai/strong/discard-opponents-protocol-v1.json')
    assert contract['models_manifest_sha256'] == digest(ROOT/'ai/strong/discard-correction-screen-models-v1.json')
    out = RAW_ROOT/f'{key}-{n}p'; saved = read(out/'verified.json')
    assert re.fullmatch('[a-f0-9]{40}', saved['revision'])
    for k, v in {'key': key, 'players': n, 'smoke': False, 'verified': True,
                 'prefix': contract['prefix_template'].format(key=key, players=n),
                 'source_revision': contract['source']['revision'],
                 'source_sha256': contract['source']['sha256']}.items(): assert saved[k] == v, k
    for name, sha in saved['artifacts'].items():
        assert Path(name).name == name and digest(out/name) == sha
    summaries = raw_checks.verify_local(out, key, n)
    checks.same_summary(summaries, saved['summary'])
    report = read(out/'search_geo.json'); summary = verify(report, protocol, key, n, guided=False)
    pin = {'revision': saved['revision'], 'prefix': saved['prefix'],
           'raw_job_id': contract['jobs'][f'{key}-{n}p'], 'verified_sha256': digest(out/'verified.json'),
           'artifact_sha256': digest(out/'search_geo.json'), 'source': contract['source']}
    return out/'search_geo.json', report, summary, pin


def paired_summary(guided, baseline, protocol):
    def difference(a, b):
        return pairs.paired_difference(a, b, protocol['bootstrap_replicates'], protocol['bootstrap_seed'])
    rules = {}
    for variant in ['original', 'recharged']:
        for sealed in [False, True]:
            select = lambda rows: [r for r in rows if r['variant'] == variant and r['sealed'] == sealed]
            rules[variant+('/sealed' if sealed else '/open')] = difference(select(guided), select(baseline))
    return {'overall': difference(guided, baseline), 'rules': rules}


def verify_local(out, key, n, smoke):
    protocol = read(PROTOCOL); source = read(SOURCE); status = read(out/'search-transfer-check.json')
    games = (1 if smoke else case_for(protocol, n)['deals'])*4*n
    expected = {'key': key, 'players': n, 'smoke': smoke, 'status': 'complete', 'games': games,
                'protocol_sha256': digest(PROTOCOL), 'source_revision': source['revision'],
                'source_sha256': source['sha256'], 'game_truncations': 0, 'search_truncations': 0,
                'trained': False, 'qualification_eligible': False}
    for k, v in expected.items(): assert status[k] == v, k
    assert {'checkpoint.json', 'search.json', 'summary.json'} <= set(status['artifacts'])
    for name, sha in status['artifacts'].items():
        assert Path(name).name == name and digest(out/name) == sha, name
    assert read(out/'checkpoint.json') == protocol['models'][key]
    report = read(out/'search.json'); summary = verify(report, protocol, key, n, smoke)
    checks.same_summary(summary, read(out/'summary.json'))
    result = {'search': summary}
    if not smoke:
        baseline_path, baseline, baseline_summary, pin = raw_baseline(key, n, protocol)
        assert digest(out/'baseline.json') == digest(baseline_path)
        assert read(out/'baseline-provenance.json') == pin
        result.update(baseline=baseline_summary, baseline_provenance=pin,
                      search_minus_raw=paired_summary(report['results'], baseline['results'], protocol))
    return result


def collect(a):
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol = read(PROTOCOL); source = read(SOURCE)
    if a.smoke: assert a.key == protocol['smoke']['model']
    prefix = 'runs/multiplayer-search-transfer-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.players}p'
    out = (SMOKE_ROOT/f'{a.players}p' if a.smoke else FULL_ROOT/f'{a.key}-{a.players}p')
    out.mkdir(parents=True, exist_ok=False)
    def fetch(name):
        assert Path(name).name == name
        p = out/name
        p.write_bytes(Path(hf_hub_download(protocol['repo'], prefix+'/'+name, revision=a.revision)).read_bytes())
        return p
    status = read(fetch('search-transfer-check.json'))
    for name, sha in status['artifacts'].items(): assert digest(fetch(name)) == sha, name
    if not a.smoke:
        path, _, _, pin = raw_baseline(a.key, a.players, protocol)
        (out/'baseline.json').write_bytes(path.read_bytes()); write(out/'baseline-provenance.json', pin)
    summary = verify_local(out, a.key, a.players, a.smoke)
    result = {'key': a.key, 'players': a.players, 'smoke': a.smoke, 'revision': a.revision, 'prefix': prefix,
              'games': summary['search']['games'], 'protocol_sha256': digest(PROTOCOL),
              'source_revision': source['revision'], 'source_sha256': source['sha256'],
              'verified': True, 'qualification_eligible': False, 'summary': summary,
              'artifacts': {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
    write(out/'verified.json', result)
    print({'key': a.key, 'players': a.players, 'smoke': a.smoke, 'games': result['games'],
           'seconds': summary['search']['seconds'], 'search_stats': summary['search']['search_stats'],
           **({'search_minus_raw': summary['search_minus_raw']['overall']} if not a.smoke else {})})


def runtime_admission(n):
    out = SMOKE_ROOT/f'{n}p'; saved = read(out/'verified.json'); protocol = read(PROTOCOL); source = read(SOURCE)
    assert saved['key'] == '10102' and saved['players'] == n and saved['smoke'] and saved['verified']
    assert saved['source_revision'] == source['revision'] and saved['source_sha256'] == source['sha256']
    assert saved['protocol_sha256'] == digest(PROTOCOL)
    for name, sha in saved['artifacts'].items(): assert Path(name).name == name and digest(out/name) == sha
    summary = verify_local(out, '10102', n, True); checks.same_summary(summary, saved['summary'])
    seconds = summary['search']['seconds']; assert math.isfinite(seconds) and seconds > 0
    projected = 120 + 2*seconds*case_for(protocol, n)['deals']
    hours = max(4, math.ceil(projected/(.75*3600)))
    return {'players': n, 'smoke_revision': saved['revision'], 'verified_sha256': digest(out/'verified.json'),
            'smoke_seconds': seconds, 'projected_shard_seconds': projected, 'timeout_hours': hours,
            'admitted': hours <= 12, 'source_revision': source['revision'],
            'source_sha256': source['sha256'], 'protocol_sha256': digest(PROTOCOL)}


def compare(counts):
    protocol = read(PROTOCOL); source = read(SOURCE)
    assert counts and len(set(counts)) == len(counts) and set(counts) <= {3, 4, 5, 6}
    summaries, rows, provenance = {}, {}, {}
    games = 0
    for key in protocol['models']:
        summaries[key], rows[key], provenance[key] = {}, {}, {}
        for n in counts:
            out = FULL_ROOT/f'{key}-{n}p'; saved = read(out/'verified.json')
            expected = {'key': key, 'players': n, 'smoke': False, 'verified': True,
                        'games': case_for(protocol, n)['games'], 'protocol_sha256': digest(PROTOCOL),
                        'source_revision': source['revision'], 'source_sha256': source['sha256'],
                        'prefix': f'runs/multiplayer-search-transfer-v1-{key}-{n}p',
                        'qualification_eligible': False}
            for k, v in expected.items(): assert saved[k] == v, k
            assert re.fullmatch('[a-f0-9]{40}', saved['revision'])
            for name, sha in saved['artifacts'].items():
                assert Path(name).name == name and digest(out/name) == sha
            summary = verify_local(out, key, n, False); checks.same_summary(summary, saved['summary'])
            summaries[key][str(n)] = summary; rows[key][str(n)] = read(out/'search.json')['results']
            provenance[key][str(n)] = {'revision': saved['revision'], 'prefix': saved['prefix'],
                'verified_sha256': digest(out/'verified.json'), 'baseline': summary['baseline_provenance']}
            games += saved['games']
    contrasts = {left+'-minus-'+right: {str(n): paired_summary(rows[left][str(n)], rows[right][str(n)], protocol)
                                      for n in counts}
                 for left, right in [('10101', 'parent'), ('10102', 'parent'), ('10102', '10101')]}
    complete = set(counts) == {3, 4, 5, 6}
    if complete: assert games == protocol['planned_new_games']
    result = {'verified_players': counts, 'all_counts_verified': complete, 'new_games': games,
              'paired_baseline_games': games, 'protocol_sha256': digest(PROTOCOL),
              'source_revision': source['revision'], 'source_sha256': source['sha256'],
              'summaries': summaries, 'between_model_search_contrasts': contrasts, 'provenance': provenance,
              'game_truncations': 0, 'search_truncations': 0, 'qualification_eligible': False,
              'scope': protocol['analysis']}
    write(ROOT/'ai/strong/multiplayer-search-transfer-results-v1.json', result)
    print({'new_games': games, 'all_counts_verified': complete,
           'paired_deltas': {k: {n: r['search_minus_raw']['overall'] for n, r in cells.items()}
                             for k, cells in summaries.items()}})


def launch(a):
    protocol = read(PROTOCOL); source = read(SOURCE)
    assert all(digest(ROOT/p) == sha for p, sha in source['overlays'].items())
    preflight = read(ROOT/'ai/strong/multiplayer-search-transfer-preflight-v1.json')
    assert preflight['source_sha256'] == source['sha256'] and preflight['frozen_package_passed']
    record = {'key': a.key, 'players': a.players, 'smoke': a.smoke, 'stage': 'launch_intent',
              'created_at': datetime.now(timezone.utc).isoformat(), 'source_revision': source['revision'],
              'source_sha256': source['sha256'], 'protocol_sha256': digest(PROTOCOL), 'qualification_eligible': False}
    hours = 4
    if a.smoke: assert a.key == protocol['smoke']['model']
    else:
        admission = runtime_admission(a.players); assert admission['admitted'], 'Partition job; do not change horizons'
        _, _, _, baseline_pin = raw_baseline(a.key, a.players, protocol)
        record.update(runtime_admission=admission, baseline=baseline_pin); hours = admission['timeout_hours']
    record['timeout_hours'] = hours
    suffix = ('smoke-' if a.smoke else '')+f'{a.key}-{a.players}p'
    directory = ROOT/'ai/runs/multiplayer-search-transfer-launches-v1'; directory.mkdir(exist_ok=True)
    guard = directory/(suffix+'.json')
    with guard.open('x') as f:
        import json
        json.dump(record, f, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', f'{hours}h',
        '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=multiplayer-search-transfer-v1-'+suffix]
    for k, v in {'MODEL_KEY': a.key, 'PLAYER_COUNT': str(a.players), 'SMOKE': '1' if a.smoke else '0',
        'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
        'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items(): command += ['--env', k+'='+v]
    command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as f:f.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as f:f.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
args=()
if [ "$SMOKE" = 1 ]; then args+=(--smoke); fi
python -u ai/strong/multiplayer_search_transfer.py "$MODEL_KEY" "$PLAYER_COUNT" ai/runs/multiplayer-search-transfer-run "${args[@]}" --upload
''']
    try:
        r = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        (directory/(suffix+'.log')).write_text(r.stdout+r.stderr)
        ids = set(re.findall(r'\b[0-9a-f]{24}\b', r.stdout))
        if len(ids) != 1: raise RuntimeError('Ambiguous launch; inspect existing HF jobs before retry')
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error)); raise
    finally: write(guard, record)
    print(record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); sub = p.add_subparsers(dest='command', required=True)
    for verb in ['launch', 'collect']:
        q = sub.add_parser(verb); q.add_argument('key', choices=['parent', '10101', '10102'])
        q.add_argument('players', type=int, choices=range(3, 7)); q.add_argument('--smoke', action='store_true')
        if verb == 'collect': q.add_argument('revision')
    q = sub.add_parser('profile'); q.add_argument('players', type=int, choices=range(3, 7))
    q = sub.add_parser('compare'); q.add_argument('--players', type=int, nargs='+', choices=range(3, 7), default=[3, 4, 5, 6])
    a = p.parse_args()
    if a.command == 'launch': launch(a)
    elif a.command == 'collect': collect(a)
    elif a.command == 'compare': compare(a.players)
    else:
        r = runtime_admission(a.players)
        write(ROOT/f'ai/strong/multiplayer-search-transfer-{a.players}p-runtime-v1.json', r); print(r)
