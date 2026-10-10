"""Guarded HF launches and independent analysis for phase search ablations."""
import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import subprocess

from huggingface_hub import hf_hub_download
from phase_search_ablation import ROOT, PROTOCOL, PHASES, read, write, digest, module, verify, exact_control, case_for
from search_transfer import verify as verify_transfer, pairs

SOURCE = ROOT/'ai/strong/phase-search-ablation-source-v1.json'
checks = module('phase_summary_checks', 'collect-discard-correction-screen.py')


def directory(arm, case, smoke):
    return ROOT/('ai/runs/phase-search-ablation-'+('smoke-' if smoke else '')+'verified-v1')/(arm+'-'+case)


def baselines(protocol, case_id):
    case = case_for(protocol, case_id); result = {}
    for arm, pin in case['baselines'].items():
        path = Path(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']))
        assert digest(path) == pin['sha256']
        report = read(path)
        summary = verify_transfer(report, protocol, '10102', case, guided=arm == 'all')
        result[arm] = (path, report, summary)
    return result


def paired(left, right, protocol):
    def compare(a, b): return pairs.paired_difference(a, b, protocol['bootstrap_replicates'], protocol['bootstrap_seed'])
    return {'overall': compare(left, right), 'rules': {
        v+('/sealed' if s else '/open'): compare([r for r in left if r['variant'] == v and r['sealed'] == s],
                                              [r for r in right if r['variant'] == v and r['sealed'] == s])
        for v in ['original', 'recharged'] for s in [False, True]}}


def verify_local(out, arm, case_id, smoke):
    protocol = read(PROTOCOL); source = read(SOURCE); case = case_for(protocol, case_id)
    status = read(out/'phase-check.json')
    expected = {'arm': arm, 'case': case_id, 'smoke': smoke, 'status': 'complete',
        'games': (1 if smoke else case['deals'])*4*case['players'],
        'protocol_sha256': digest(PROTOCOL), 'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'trained': False, 'qualification_eligible': False, 'game_truncations': 0, 'search_truncations': 0}
    for k, v in expected.items(): assert status[k] == v, k
    assert {'checkpoint.json', 'search.json', 'summary.json'} <= set(status['artifacts'])
    for name, sha in status['artifacts'].items(): assert Path(name).name == name and digest(out/name) == sha
    assert read(out/'checkpoint.json') == protocol['models']['10102']
    report = read(out/'search.json'); summary = verify(report, protocol, case_id, arm, smoke)
    if arm == 'all':
        assert 'control.json' in status['artifacts']
        assert digest(out/'control.json') == case['baselines']['all']['sha256']
        baseline = read(out/'control.json'); verify_transfer(baseline, protocol, '10102', case)
        summary['control_parity'] = exact_control(report, baseline)
    checks.same_summary(summary, read(out/'summary.json'))
    result = {'phase': summary}
    if not smoke:
        result['baselines'] = {}; result['phase_minus_baseline'] = {}
        for kind, pin in case['baselines'].items():
            path = out/(kind+'-baseline.json'); assert digest(path) == pin['sha256']
            base = read(path)
            result['baselines'][kind] = verify_transfer(base, protocol, '10102', case, guided=kind == 'all')
            result['phase_minus_baseline'][kind] = paired(report['results'], base['results'], protocol)
    return result


def verified(arm, case, smoke):
    out = directory(arm, case, smoke); saved = read(out/'verified.json'); source = read(SOURCE)
    for k, v in {'arm': arm, 'case': case, 'smoke': smoke, 'verified': True,
                 'source_revision': source['revision'], 'source_sha256': source['sha256'],
                 'protocol_sha256': digest(PROTOCOL), 'qualification_eligible': False}.items(): assert saved[k] == v, k
    assert re.fullmatch('[a-f0-9]{40}', saved['revision'])
    for name, sha in saved['artifacts'].items(): assert Path(name).name == name and digest(out/name) == sha
    summary = verify_local(out, arm, case, smoke); checks.same_summary(summary, saved['summary'])
    return out, saved, summary


def collect(a):
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol = read(PROTOCOL); source = read(SOURCE)
    prefix = 'runs/phase-search-ablation-'+('smoke-' if a.smoke else '')+f'v1-{a.arm}-{a.case}'
    status_path = Path(hf_hub_download(protocol['repo'], prefix+'/phase-check.json', revision=a.revision))
    status = read(status_path); assert status['status'] == 'complete'
    out = directory(a.arm, a.case, a.smoke); out.mkdir(parents=True, exist_ok=False)
    (out/'phase-check.json').write_bytes(status_path.read_bytes())
    for name, sha in status['artifacts'].items():
        assert Path(name).name == name
        path = Path(hf_hub_download(protocol['repo'], prefix+'/'+name, revision=a.revision))
        assert digest(path) == sha; (out/name).write_bytes(path.read_bytes())
    if not a.smoke:
        for kind, (path, _, _) in baselines(protocol, a.case).items():
            (out/(kind+'-baseline.json')).write_bytes(path.read_bytes())
    summary = verify_local(out, a.arm, a.case, a.smoke)
    record = {'arm': a.arm, 'case': a.case, 'smoke': a.smoke, 'revision': a.revision, 'prefix': prefix,
              'games': summary['phase']['games'], 'source_revision': source['revision'], 'source_sha256': source['sha256'],
              'protocol_sha256': digest(PROTOCOL), 'verified': True, 'qualification_eligible': False, 'summary': summary,
              'artifacts': {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
    write(out/'verified.json', record)
    print({'arm': a.arm, 'case': a.case, 'smoke': a.smoke, 'games': record['games'],
           'seconds': summary['phase']['seconds'], 'phase_routing': summary['phase']['phase_routing'],
           'search_stats': summary['phase']['search_stats'], **({'control_parity': summary['phase']['control_parity']} if a.arm == 'all' else {})})


def profile(arm, case):
    assert arm in PHASES
    _, control, control_summary = verified('all', case, True)
    out, smoke, summary = verified(arm, case, True)
    assert control_summary['phase']['control_parity']['all_raw_game_rows_match']
    seconds = summary['phase']['seconds']; assert math.isfinite(seconds) and seconds > 0
    projected = 120+2*seconds*case_for(read(PROTOCOL), case)['deals']
    hours = max(4, math.ceil(projected/(.75*3600)))
    return {'arm': arm, 'case': case, 'probe_revision': smoke['revision'],
            'probe_verified_sha256': digest(out/'verified.json'), 'control_revision': control['revision'],
            'control_verified_sha256': digest(directory('all', case, True)/'verified.json'),
            'probe_seconds': seconds, 'projected_seconds': projected, 'timeout_hours': hours, 'admitted': hours <= 12}


def launch(a):
    protocol = read(PROTOCOL); source = read(SOURCE)
    assert a.arm != 'all' or a.smoke
    assert all(digest(ROOT/name) == sha for name, sha in source['overlays'].items())
    preflight = read(ROOT/'ai/strong/phase-search-ablation-preflight-v1.json')
    assert preflight['frozen_package_passed'] and preflight['source_sha256'] == source['sha256']
    record = {'arm': a.arm, 'case': a.case, 'smoke': a.smoke, 'stage': 'launch_intent',
              'created_at': datetime.now(timezone.utc).isoformat(), 'source_revision': source['revision'],
              'source_sha256': source['sha256'], 'protocol_sha256': digest(PROTOCOL), 'qualification_eligible': False}
    hours = 4
    if not a.smoke:
        admission = profile(a.arm, a.case); assert admission['admitted'], 'Split work; do not weaken horizons'
        baselines(protocol, a.case)
        record['runtime_admission'] = admission; hours = admission['timeout_hours']
    record['timeout_hours'] = hours
    suffix = ('smoke-' if a.smoke else '')+a.arm+'-'+a.case
    guards = ROOT/'ai/runs/phase-search-ablation-launches-v1'; guards.mkdir(exist_ok=True)
    guard = guards/(suffix+'.json')
    with guard.open('x') as f:
        import json
        json.dump(record, f, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', f'{hours}h',
               '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=phase-search-ablation-v1-'+suffix]
    for k, v in {'ARM': a.arm, 'CASE': a.case, 'SMOKE': '1' if a.smoke else '0',
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
python -u ai/strong/phase_search_ablation.py "$ARM" "$CASE" ai/runs/phase-ablation-run "${args[@]}" --upload
''']
    try:
        r = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        (guards/(suffix+'.log')).write_text(r.stdout+r.stderr)
        ids = set(re.findall(r'\b[0-9a-f]{24}\b', r.stdout)); assert len(ids) == 1, 'Ambiguous submission; inspect existing job label'
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as e:
        record.update(stage='launch_unknown', error=type(e).__name__+': '+str(e)); raise
    finally: write(guard, record)
    print(record)


def compare(cases):
    protocol = read(PROTOCOL); source = read(SOURCE)
    known = {c['id'] for c in protocol['cases']}; assert cases and len(cases) == len(set(cases)) and set(cases) <= known
    arms, rows, provenance = {}, {}, {}; games = 0
    for arm in PHASES:
        arms[arm], rows[arm], provenance[arm] = {}, {}, {}
        for case in cases:
            out, saved, summary = verified(arm, case, False)
            arms[arm][case] = summary; rows[arm][case] = read(out/'search.json')['results']; games += saved['games']
            provenance[arm][case] = {'revision': saved['revision'], 'prefix': saved['prefix'], 'verified_sha256': digest(out/'verified.json')}
    complete = set(cases) == known
    if complete: assert games == protocol['planned_new_full_games']
    result = {'cases': cases, 'all_cases_verified': complete, 'new_games': games, 'arms': arms, 'provenance': provenance,
              'building_minus_auction': {c: paired(rows['building'][c], rows['auction'][c], protocol) for c in cases},
              'source_revision': source['revision'], 'source_sha256': source['sha256'], 'protocol_sha256': digest(PROTOCOL),
              'game_truncations': 0, 'search_truncations': 0, 'qualification_eligible': False, 'scope': protocol['analysis']}
    write(ROOT/'ai/strong/phase-search-ablation-results-v1.json', result)
    print({'new_games': games, 'all_cases_verified': complete,
           'win_rates': {a: {c: s['phase']['win_rate'] for c, s in cells.items()} for a, cells in arms.items()}})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); sub = p.add_subparsers(dest='command', required=True)
    cases = ['search_geo-2p', 'search_geo-3p', 'a260-3p']
    for name in ['launch', 'collect', 'profile']:
        q = sub.add_parser(name); q.add_argument('arm', choices=['all', *PHASES]); q.add_argument('case', choices=cases)
        if name != 'profile': q.add_argument('--smoke', action='store_true')
        if name == 'collect': q.add_argument('revision')
    q = sub.add_parser('compare'); q.add_argument('--cases', nargs='+', choices=cases, default=cases)
    a = p.parse_args()
    if a.command == 'launch': launch(a)
    elif a.command == 'collect': collect(a)
    elif a.command == 'compare': compare(a.cases)
    else:
        result = profile(a.arm, a.case)
        write(ROOT/f'ai/strong/phase-search-ablation-{a.arm}-{a.case}-runtime-v1.json', result); print(result)
