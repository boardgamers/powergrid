"""Collect original fresh-root jobs and freeze the complete outcome-independent corpus."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from surrogate_continuation_root_verification_v1 import verify_artifacts

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('fresh_root_launcher', STRONG/'launch-surrogate-continuation-roots-v1.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
COLLECTED = ROOT/'ai/runs/surrogate-continuation-roots-collected-v1'
FROZEN = ROOT/'ai/runs/surrogate-continuation-roots-frozen-v1'
INDEX = STRONG/'surrogate-continuation-roots-results-v1.json'
RUNTIME = ROOT/'ai/runs/surrogate-continuation-roots-source-prepared-v1/layout'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
ACTIVE = {'RUNNING', 'SCHEDULING'}


def code_hashes():
    return {**launcher.dependencies(), str(Path(__file__).relative_to(ROOT)): digest(__file__)}


def guard_for(case):
    plan, source, row = launcher.admission(case); path = launcher.GUARDS/(case+'.json'); guard = read(path)
    assert guard['stage'] == 'launched' and guard['case'] == case and guard['row'] == row
    assert guard['source'] == source and guard['plan_sha256'] == digest(launcher.PLAN)
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    return plan, source, row, guard, path


def verified_receipt(case):
    path = COLLECTED/case/'verified.json'
    if not path.exists(): return None
    _, source, row, guard, guard_path = guard_for(case); receipt = read(path)
    assert receipt['verified'] is True and receipt['authoritative_status'] == 'COMPLETED'
    assert receipt['case'] == case and receipt['job_id'] == guard['job_id'] and receipt['guard_sha256'] == digest(guard_path)
    assert receipt['source'] == source and receipt['plan_sha256'] == digest(launcher.PLAN) and receipt['row'] == row
    assert receipt['collector_code_hashes'] == code_hashes()
    assert receipt['review']['complete'] and receipt['review']['games'] == row['games'] and receipt['review']['caps'] == 0
    artifacts = path.parent/'artifacts'; manifest = read(artifacts/'manifest.json')
    assert digest(artifacts/'manifest.json') == receipt['evidence']['manifest_sha256']
    assert {str(p.relative_to(artifacts)) for p in artifacts.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert all(digest(artifacts/name) == sha for name, sha in manifest.items())
    return receipt


def inspect(case):
    _, _, _, guard, path = guard_for(case)
    stage = HfApi().inspect_job(job_id=guard['job_id']).status.stage
    return {'case': case, 'job_id': guard['job_id'], 'authoritative_status': stage,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'guard_sha256': digest(path)}


def collect(case):
    previous = verified_receipt(case)
    if previous: return previous
    _, source, row, guard, _ = guard_for(case); status = inspect(case)
    folder = COLLECTED/case; folder.mkdir(parents=True, exist_ok=True); write(folder/'status.json', status)
    if status['authoritative_status'] != 'COMPLETED': return status
    hashes = code_hashes()
    log = '\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=guard['job_id'], follow=False))
    (folder/'job.log').write_text(log); receipts = []
    for line in log.splitlines():
        if not line.startswith('{'): continue
        try: value = ast.literal_eval(line)
        except (ValueError, SyntaxError): continue
        if isinstance(value, dict) and value.get('status', {}).get('case') == case and 'evidence' in value: receipts.append(value)
    assert len(receipts) == 1, 'Missing or ambiguous original upload receipt'
    remote = receipts[0]; evidence = remote['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == f'archives/{case}.tgz'
    assert evidence['remote_archive_verified'] is True and evidence['format'] == 'tar.gz' and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']; artifacts = folder/'artifacts'
    if not artifacts.exists(): extract_verified(archive, artifacts)
    assert read(artifacts/'job.json') == remote['status']
    review = verify_artifacts(artifacts, evidence, source, read(launcher.PROTOCOL), RUNTIME, MODEL,
                              row['players'], row['start'], row['end'], 'root')
    assert review['games'] == row['games'] and review['twin_games'] == 0
    assert code_hashes() == hashes
    result = {**status, 'verified': True, 'source': source, 'row': row, 'plan_sha256': digest(launcher.PLAN),
              'protocol_sha256': digest(launcher.PROTOCOL), 'evidence': evidence, 'review': review,
              'collector_code_hashes': hashes, 'gradients': False, 'qualification_eligible': False,
              'reserved_final_seeds_used': False}
    temporary = folder/'verified.tmp.json'; write(temporary, result); temporary.replace(folder/'verified.json')
    return result


def build_manifest(plan, receipts):
    """No model outputs or terminal outcomes are available to this selection step."""
    assert set(receipts) == {row['case'] for row in plan['shards']}
    roots = []; games = []; coverage = Counter(); provenance = {}
    for row in sorted(plan['shards'], key=lambda r: (r['players'], r['start'])):
        case = row['case']; receipt = receipts[case]
        assert receipt['verified'] and receipt['row'] == row and receipt['review']['games'] == row['games']
        provenance[case] = {'job_id': receipt['job_id'], 'verified_sha256': digest(COLLECTED/case/'verified.json'),
                            'evidence': receipt['evidence']}
        for episode in range(row['start']*4*row['players'], row['end']*4*row['players']):
            folder = COLLECTED/case/'artifacts/games'/f'game-{episode}'; selected = read(folder/'roots.json'); q = read(folder/'contract.json')
            assert q['mode'] == 'root' and q['episode'] == episode and q['players'] == row['players']
            games.append({'identity': q, 'roots_sha256': digest(folder/'roots.json'), 'case': case,
                          'missing_phases': selected['missing_phases'], 'eligible_decisions': len(selected['eligible'])})
            for phase in ('plant', 'bid', 'building'):
                if phase not in selected['roots']: continue
                record = selected['roots'][phase]; assert record['identity'] == q and record['phase'] == phase
                same_phase = [r for r in selected['eligible'] if r['phase'] == phase]
                winner = min(same_phase, key=lambda r: (r['rank'], r['decision']))
                assert all(record[key] == value for key, value in winner.items())
                roots.append({'root_id': f'{q["players"]}:{episode}:{phase}', 'case': case, **record})
                coverage[f'{q["players"]}/{q["rule"]}/{phase}'] += 1
    expected_games = {(n, deal, seat, rule) for n in range(2, 7) for deal in range(2) for seat in range(n) for rule in range(4)}
    assert len(games) == plan['games'] == len(expected_games) == 160
    assert {(g['identity']['players'], g['identity']['deal'], g['identity']['seat'], g['identity']['rule']) for g in games} == expected_games
    assert set(coverage) == {f'{n}/{rule}/{phase}' for n in range(2, 7) for rule in range(4) for phase in ('plant', 'bid', 'building')}, 'Report missing coverage; do not substitute roots using outcomes'
    assert len(roots) == len({r['root_id'] for r in roots}) <= 480
    assert len(roots) == sum(receipt['review']['selected_roots'] for receipt in receipts.values())
    return {'version': 1, 'protocol_sha256': plan['protocol_sha256'], 'plan_sha256': digest(launcher.PLAN),
            'source_sha256': plan['source']['sha256'], 'focal_model_sha256': read(launcher.PROTOCOL)['focal_model_sha256'],
            'games': games, 'roots': roots, 'phase_counts': dict(sorted(coverage.items())), 'provenance': provenance,
            'selection': 'Fixed minimum identity hash per game and phase; no terminal outcomes, teacher values or surrogate scores.',
            'input_boundary': 'Only root.request enters continuation inference. Identity/game seeds/ranks are provenance, never model inputs.',
            'qualification_eligible': False, 'reserved_final_seeds_used': False}


def index():
    plan = read(launcher.PLAN); launcher.admission(plan['shards'][0]['case'])
    receipts = {row['case']: verified_receipt(row['case']) for row in plan['shards']}
    assert all(receipts.values()), 'All original shards must verify before freezing roots'
    manifest = build_manifest(plan, receipts); FROZEN.mkdir(parents=True, exist_ok=True)
    path = FROZEN/'roots.json'
    if path.exists(): assert read(path) == manifest
    else:
        temporary = FROZEN/'roots.tmp.json'; write(temporary, manifest); temporary.replace(path)
    result = {'complete': True, 'games': 160, 'selected_roots': len(manifest['roots']), 'phase_counts': manifest['phase_counts'],
              'plan_sha256': digest(launcher.PLAN), 'protocol_sha256': digest(launcher.PROTOCOL),
              'root_manifest': str(path.relative_to(ROOT)), 'root_manifest_sha256': digest(path),
              'cases': manifest['provenance'], 'source': plan['source'], 'code_hashes': code_hashes(),
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    frozen = FROZEN/'frozen.json'
    if frozen.exists(): assert read(frozen) == result
    else:
        temporary = FROZEN/'frozen.tmp.json'; write(temporary, result); temporary.replace(frozen)
    if INDEX.exists(): assert read(INDEX) == result
    else:
        temporary = INDEX.with_suffix('.tmp.json'); write(temporary, result); temporary.replace(INDEX)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'collect'): sub.add_parser(command).add_argument('case')
    sub.add_parser('index'); args = parser.parse_args()
    result = index() if args.command == 'index' else globals()[args.command](args.case)
    print(json.dumps({k: result[k] for k in ('case', 'job_id', 'authoritative_status', 'verified', 'complete', 'games', 'selected_roots') if k in result}))
