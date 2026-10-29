"""Actual public-request checks on first/last fixtures per count/rule/phase/menu."""
from collections import Counter
import json
import subprocess
import sys
from pathlib import Path
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest

BASE = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
ARTIFACT = ROOT/'ai/runs/nomination-discount-development-v1/artifact'
OUT = ROOT/'ai/runs/nomination-discount-serving-v1'
RESULT = ROOT/'ai/strong/nomination-discount-serving-v1.json'


class Service:
    def __init__(self, artifact, descriptor, log):
        self.p = subprocess.Popen([sys.executable, '-u', '-B', str(artifact/'ai/strong/public_policy_runtime_v1.py'),
            str(artifact), '--descriptor', descriptor, '--diagnostics'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=log, cwd='/tmp', text=True)
    def call(self, request):
        self.p.stdin.write(json.dumps(request, separators=(',', ':'))+'\n'); self.p.stdin.flush()
        line = self.p.stdout.readline(); assert line, 'Service exited; inspect preserved stderr'
        result = json.loads(line); assert 'error' not in result, result
        return result
    def close(self):
        self.p.stdin.close(); assert self.p.wait(timeout=30) == 0


def main():
    assert not OUT.exists() and not RESULT.exists()
    protocol = read(ROOT/'ai/strong/nomination-discount-development-protocol-v1.json')
    source = ROOT/'ai/runs/current-full-serving-8840u-prepared-v1/package/cases.jsonl'
    rows = [json.loads(line) for line in source.open()]; groups = {}
    for row in rows:
        key = row['players'], row['variant'], row['sealed'], row['stage'], tuple(sorted({m['name'] for m in row['legal']}))
        groups.setdefault(key, []).append(row)
    cases = sorted({row['index']: row for group in groups.values() for row in (group[0], group[-1])}.values(), key=lambda r: r['index'])
    assert set(r['players'] for r in cases) == set(range(2, 7))
    assert len({(r['players'], r['variant'], r['sealed']) for r in cases}) == 20
    OUT.mkdir(); parent_moves = {}; reports = []
    for arm in ['original_parent', *protocol['arms']]:
        artifact = BASE if arm == 'original_parent' else ARTIFACT
        descriptor = 'policies/filter.json' if arm == 'original_parent' else f'policies/nomination-{arm}.json'
        count = Counter()
        with (OUT/(arm+'.stderr.log')).open('x') as log, (OUT/(arm+'.jsonl')).open('x') as trace:
            service = Service(artifact, descriptor, log)
            try:
                for row in cases:
                    q = {**row['request'], 'requestId': f"fixture:{row['index']}", 'revision': row['index']}
                    answer = service.call(q); move = answer['move']; choice = row['legal'].index(move)
                    assert answer['requestId'] == q['requestId'] and answer['revision'] == q['revision']
                    assert answer['playerOrder'] == row['player_order'] and answer['decision']['index'] == choice
                    if arm == 'original_parent': parent_moves[row['index']] = move
                    else:
                        identity = protocol['identities'][arm]
                        assert all(answer[k] == v for k, v in identity.items())
                        nomination = any(m['name'] == 'ChoosePowerPlant' for m in row['legal'])
                        if arm == 'parent' or not nomination:
                            assert move == parent_moves[row['index']], (arm, row['index'], 'Other phase changed')
                            count['parent_preserved'] += 1
                        if move != parent_moves[row['index']]: count['nomination_changes'] += 1
                    count['requests'] += 1
                    trace.write(json.dumps({'case': row['index'], 'choice': choice, 'move': move,
                                            'filter_applied': answer['decision']['filterApplied']})+'\n')
            finally: service.close()
        reports.append({'arm': arm, **count, 'trace_sha256': digest(OUT/(arm+'.jsonl'))})
        print(reports[-1], flush=True)
    save(RESULT, {'complete': True, 'protocol_sha256': digest(ROOT/'ai/strong/nomination-discount-development-protocol-v1.json'),
        'fixture_source_sha256': digest(source), 'selected_case_indices': [r['index'] for r in cases], 'cases': len(cases),
        'count_rule_cells': 20, 'groups': len(groups), 'arms': reports, 'new_games': 0, 'new_gradients': 0,
        'qualified': False, 'checker_sha256': digest(__file__)})


if __name__ == '__main__': main()
