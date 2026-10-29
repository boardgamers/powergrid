"""Independent raw-game audit using the pinned isolated runtime's verifier."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def read(path): return json.loads(Path(path).read_text())


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ('artifact', 'bundle', 'raw', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--name', required=True); a = p.parse_args()
    assert not a.output.exists()
    artifact = a.artifact.resolve(); sys.path.insert(0, str(artifact/'ai/strong'))
    from public_policy_final_audit_v1 import artifact_identity, audit_shard
    from public_policy_final_contract_v1 import audit_execution_binding
    protocol = read(a.bundle/'protocol.json'); row = next(r for r in protocol['rows'] if r['name'] == a.name)
    origin = read(a.raw/'origin.json'); status = read(a.raw/'status.json'); evaluation = a.raw/'evaluation'
    assert origin['row'] == row and origin['protocol_sha256'] == digest(a.bundle/'protocol.json')
    assert status['complete'] and status['returncode'] == 0
    identity = artifact_identity(artifact, row['descriptor']); assert identity == protocol['identities'][row['arm']]
    assert digest(evaluation/'candidate.json') == digest(a.bundle/row['candidate'])
    assert digest(evaluation/'contract.json') == digest(a.bundle/row['contract'])
    checked = audit_shard(evaluation, row['shard'], identity, reserved=False)
    checked['execution_binding'] = audit_execution_binding(evaluation, identity, digest(artifact/'ai/strong/public_policy_final_runner_v1.py'))
    assert checked == read(evaluation/'audit.json'), 'Independent raw audit differs'
    result = read(evaluation/'evaluation.json')
    assert result['all_complete'] and result['passed'] and not result['errors']
    assert result['completed_games'] == row['shard']['games'] and result['game_caps'] == result['rollout_caps'] == 0
    assert not result['reserved_final_seeds_used']
    report = {'independently_audited': True, 'name': a.name, 'row': row, 'games': row['shard']['games'], 'caps': 0,
              'protocol_sha256': digest(a.bundle/'protocol.json'), 'runtime_manifest_sha256': digest(artifact/'manifest.json'),
              'raw_manifest_sha256': digest(a.raw/'manifest.json'), 'independent_audit': checked,
              'auditor_sha256': digest(__file__), 'seconds': status['seconds'], 'qualified': False, 'reserved_final_seeds_used': False}
    with a.output.open('x') as f: json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    print({'name': a.name, 'independently_audited_games': row['shard']['games'], 'caps': 0}, flush=True)


if __name__ == '__main__': main()
