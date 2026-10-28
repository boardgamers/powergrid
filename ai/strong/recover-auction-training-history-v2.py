"""Recover omitted low-cash states from the remaining predefined training deals.

No inference, continuations, rewards, new games, new targets or final seeds.
"""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/auction-training-history-v2'
DEALS = (2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15)
RESULT = ROOT / 'ai/strong/auction-training-history-results-v2.json'


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, data):
    with p.open('x') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect preserved history recovery before retrying'
    protocol_path = ROOT / 'ai/strong/policy-iteration-collection-protocol-v2.json'
    protocol = read(protocol_path)
    source_path = ROOT / 'ai/strong/policy-iteration-collection-source-v2.json'
    source = read(source_path)
    collection = read(ROOT / 'ai/strong/policy-iteration-collection-results-v2.json')
    assert collection['complete'] and collection['games'] == 7680
    assert collection['source'] == source and collection['protocol_sha256'] == digest(protocol_path)
    runtime = ROOT / 'ai/runs/policy-iteration-collection-collector-v2'
    bundle = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
        repo_type='dataset', revision=source['revision']))
    assert digest(bundle) == source['sha256']
    with tarfile.open(bundle) as archive:
        for item in archive.getmembers():
            if item.isfile():
                assert digest(runtime / item.name) == hashlib.sha256(archive.extractfile(item).read()).hexdigest()
    current = ROOT / 'ai/runs/current-engine-compatibility-v1'
    proof = read(ROOT / 'ai/strong/current-engine-compatibility-evidence-v1.json')
    assert digest(current / 'build.json') == proof['build_sha256']
    for name, sha in read(current / 'build.json')['compiled_files'].items():
        assert digest(current / 'source/engine' / name) == sha
    worker = ROOT / 'ai/strong/recover-auction-training-history-v1.cjs'
    prior = ROOT / 'ai/strong/auction-training-history-results-v1.json'
    prior_report = read(prior)
    assert prior_report['passed'] and prior_report['prefixes_verified'] == 160
    assert prior_report['coverage']['splits'] == {'validation': 4}
    assert [d for d in range(protocol['deals']) if d not in protocol['validation_deals'] and d != 1] == list(DEALS)
    OUT.mkdir()
    design = {'created_at': datetime.now(timezone.utc).isoformat(),
        'selection': 'For each 2–6-player parent/economic collection case, take the last recorded strategic root outside an unresolved sealed auction in every game of the remaining original training deals 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15. The already checked training deal 1 and all validation deals are excluded. All seats and all four rules; no outcome selection. Unresolved sealed auctions omit pending moves from their public log and cannot be reconstructed from that log alone.',
        'expected_prefixes': 880, 'deals': list(DEALS), 'source': source,
        'prior_report_sha256': digest(prior), 'prior_training_prefixes': 80, 'prior_training_roots': 0,
        'protocol_sha256': digest(protocol_path),
        'collection_results_sha256': digest(ROOT / 'ai/strong/policy-iteration-collection-results-v2.json'),
        'current_engine_commit': proof['current_engine_commit'],
        'current_engine_build_sha256': digest(current / 'build.json'),
        'runtime': str(runtime.relative_to(ROOT)), 'current_engine': str((current / 'source/engine').relative_to(ROOT)),
        'code': {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), worker, ROOT / 'ai/strong/features-v4_4.cjs']},
        'scope': 'Fixed recorded action-prefix recovery; new choices are unlabelled and not a strength evaluation.',
        'new_hf_jobs': 0, 'new_inference': 0, 'new_rollouts': 0, 'new_games': 0, 'new_gradients': 0,
        'qualified': False, 'reserved_final_seeds_used': False}
    save(OUT / 'design.json', design)
    provenance = {}
    prefixes = []
    for n in range(2, 7):
        case = f'{n}p-parent-economic'
        folder = ROOT / 'ai/runs/policy-iteration-collection-verified-v2' / case
        pin = collection['cases'][case]
        assert digest(folder / 'verified.json') == pin['verified_sha256']
        assert digest(folder / 'roots.jsonl.gz') == pin['artifacts']['roots.jsonl.gz']
        selected = {}
        with gzip.open(folder / 'roots.jsonl.gz', 'rt') as f:
            for line in f:
                row = json.loads(line)
                if row['deal'] not in DEALS:
                    continue
                assert row['players'] == n and row['behavior'] == 'parent' and row['mode'] == 'economic'
                assert row['deal'] == row['episode'] // (4 * n)
                assert row['split'] == 'train' and row['deal'] not in protocol['validation_deals']
                assert row['gameSeed'] == protocol['seed_template'].format(players=n, behavior='parent', opponent='economic') + '-' + str(row['deal'])
                assert row['public_root_sha256'] == hashlib.sha256(json.dumps(row['request'], sort_keys=True).encode()).hexdigest()
                assert row['request']['player'] == row['episode'] // 4 % n
                if row['sealed'] and row['request']['state'].get('chosenPowerPlant'):
                    continue
                previous = selected.get(row['episode'])
                assert previous is None or row['ordinal'] > previous['ordinal']
                selected[row['episode']] = row
        assert set(selected) == {deal * (4 * n) + i for deal in DEALS for i in range(4 * n)}
        prefixes.extend(selected[ep] for ep in sorted(selected))
        provenance[case] = {k: pin[k] for k in ['revision', 'prefix', 'verified_sha256', 'artifacts']}
        print({'selected_case': case, 'historical_prefixes': len(selected)}, flush=True)
    assert len(prefixes) == 880
    assert Counter(r['split'] for r in prefixes) == {'train': 880}
    assert len({(r['players'], r['episode']) for r in prefixes}) == 880
    with gzip.open(OUT / 'prefixes.jsonl.gz', 'xt') as f:
        for row in prefixes:
            f.write(json.dumps(row, allow_nan=False) + '\n')
    save(OUT / 'provenance.json', provenance)
    with (OUT / 'replay.log').open('x') as log:
        subprocess.run(['node', str(worker), str(ROOT), str(OUT)], cwd='/tmp',
            stdout=log, stderr=subprocess.STDOUT, check=True)
    report = read(OUT / 'assessment.json')
    assert report['passed'] and report['prefixes_verified'] == 880
    report.update(design_sha256=digest(OUT / 'design.json'),
        artifacts={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        new_hf_jobs=0, new_inference=0, new_rollouts=0, new_games=0, new_gradients=0,
        qualification_eligible=False, reserved_final_seeds_used=False,
        training_ready=False)
    save(RESULT, report)
    print(json.dumps({k: report[k] for k in ['passed', 'prefixes_verified', 'transitions',
        'newly_affordable_roots', 'coverage']}), flush=True)


if __name__ == '__main__':
    main()
