"""Verify and archive the isolated sealed-order audit; never starts jobs."""
import json
from pathlib import Path
import shutil

from population_policy_verification import digest, read, verify_decision
from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def semantic(row):
    return {k:v for k,v in row.items() if k != 'elapsedMs'}


def main():
    base = ROOT/'ai/runs/live-sealed-order-repair-v2'
    audit = ROOT/'ai/runs/live-sealed-order-audit-v1'
    original = ROOT/'ai/runs/population-hybrid-development-source-prepared-v1/layout'
    proof = read(base/'source-verification.json')
    assert proof['archived_files_verified'] == len(proof['files']) == 1463
    for name, sha in proof['files'].items():
        assert digest(original/name) == sha
        expected = proof['replacement_sha256'] if name == proof['isolated_overlay'] else sha
        assert digest(base/'runtime'/name) == expected
    assert digest(ROOT/'ai/strong/sealed-policy-beliefs-order-v2.cjs') == proof['replacement_sha256']
    plan = read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')
    for name,sha in plan['dependency_hashes'].items():
        assert digest(ROOT/name) == sha, name
    a, contract, trained = (read(audit/'assessment.json'),read(base/'checks/assessment.json'),read(base/'trained/assessment.json'))
    assert a['audit_complete'] and a['cases'] == 446 and a['canonical_controls'] == 2553
    assert contract['passed'] and contract['canonical_controls'] == 2553 and contract['subset_requests'] == 640
    assert trained['passed'] and trained['model_positions'] == trained['filter_positions'] == 1086
    assert trained['search_cases'] == 18 and trained['caps'] == 0
    assert a['checker_sha256'] == digest(ROOT/'ai/strong/audit-live-sealed-order-v1.cjs')
    assert contract['checker_sha256'] == digest(ROOT/'ai/strong/test-live-sealed-order-v2.cjs')
    assert trained['checker_sha256'] == digest(ROOT/'ai/strong/probe-live-sealed-order-v2.py')
    assert trained['request_sha256'] == contract['requests_sha256'] == digest(base/'checks/requests.jsonl')
    assert trained['source_verification_sha256'] == digest(base/'source-verification.json')
    for name,sha in trained['files'].items():
        assert digest(base/'trained'/name) == sha
    requests = [json.loads(line) for line in (base/'checks/requests.jsonl').open()]
    rows = [json.loads(line) for line in (base/'trained/model-filter.jsonl').open()]
    assert len(requests) == len(rows) == 1086
    for request,row in zip(requests,rows):
        assert request['label'] == row['label']
        q = request['request']
        for arm in ['model','filter']:
            result = row['results'][arm]
            verify_decision(result,{'players':len(q['state']['players']), 'arm':arm,
                'samples':8, 'model_sha256':trained['model_sha256']},q['player'])
            assert request['legal'][result['index']] == result['move']
    selected = read(base/'trained/selected-requests.json')
    controls = read(ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json')
    searches = [json.loads(line) for line in (base/'trained/search.jsonl').open()]
    assert len(searches) == len({row['label'] for row in searches}) == 18
    results = {}
    rollouts = 0
    for row in searches:
        label,result = row['label'],row['result']
        if label in selected:
            entry = selected[label]
        elif label.startswith(('old-','new-')):
            entry = controls[label[4:]]['fixture']
        elif label.startswith(('hidden-','partition-')):
            entry = selected['6p-recharged-committed']
        else:
            raise ValueError(label)
        q = entry['request']
        verify_decision(result,{'players':len(q['state']['players']), 'arm':'combined',
            'samples':8, 'model_sha256':trained['model_sha256']},q['player'])
        assert entry['legal'][result['index']] == result['move']
        if 'plan' in entry:
            for world in result['search']['worlds'].values():
                assert [bid['actor'] for bid in world['initialBelief']['committed']] == entry['plan']['submitted']
        results[label] = result
        rollouts += result['search']['evaluations']
    for name in ['2p-bid','6p-bid']:
        assert semantic(results['old-'+name]) == semantic(results['new-'+name])
    for prefix in ['hidden-','partition-']:
        name = '6p-recharged-committed'
        assert semantic(results[prefix+name]) == semantic(results[name])
    assert rollouts == trained['rollouts']
    evidence = ROOT/'ai/runs/live-sealed-order-evidence-v2'
    assert not evidence.exists()
    evidence.mkdir()
    sources = [ROOT/'ai/strong'/name for name in [
        'audit-live-sealed-order-v1.cjs','sealed-policy-beliefs-order-v2.cjs',
        'test-live-sealed-order-v2.cjs','probe-live-sealed-order-v2.py','collect-live-sealed-order-v2.py',
        'population-hybrid-development-source-v1.json','population-hybrid-development-protocol-v1.json',
        'population-hybrid-development-plan-v1.json','population_policy_verification.py',
        'production-engine-compatibility-v2.json','policy_iteration_evidence_archive.py',
    ]]
    sources += [p for p in audit.rglob('*') if p.is_file()]
    sources += [p for p in base.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(base).parts]
    sources += [ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json',
        ROOT/'ai/runs/production-engine-compatibility-v2/current/provenance.json']
    for source in sources:
        destination = evidence/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source,destination)
    summary = {
        'finding':'Frozen canonical adapter rejected legal asynchronous sealed-auction requests before inference.',
        'research_repair':'Separately versioned order-v2 belief module; only changed in an isolated runtime.',
        'canonical_preparations_identical':2553, 'reproduced_failures_fixed':446,
        'pending_subset_actor_cases':640, 'model_filter_decisions':2172,
        'full_search_cases':18, 'rollouts':rollouts, 'caps':0,
        'canonical_search_pairs_identical':2, 'secret_search_pair_identical':True,
        'worker_partition_pair_identical':True, 'source_archive_files_checked':1463,
        'model_sha256':trained['model_sha256'], 'belief_module_sha256':proof['replacement_sha256'],
        'frozen_evaluation_dependencies_unchanged':True,
        'history_assumption':contract['history_assumption'],
        'limits':['Research repair only; not wired into BGS or promoted into the running screen.',
            'Actual submitted order is unknown; public-order committed-bid prompts are an explicit approximation.',
            'No noncanonical-order strength estimate or target-CPU timing claim.',
            'Current canonical grid remains valid but cannot certify asynchronous platform play.'],
        'no_candidate_promotion':True, 'qualification_eligible':False,
        'reserved_final_seeds_used':False, 'new_hf_jobs':0, 'new_strength_games':0, 'gradients':False,
    }
    write(evidence/'assessment.json',summary)
    write(evidence/'manifest.json',{str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()})
    receipt = upload_evidence(evidence)
    descriptor = {**summary,**receipt}
    write(ROOT/'ai/strong/live-sealed-order-evidence-v2.json',descriptor)
    print(json.dumps(descriptor,indent=2))


if __name__ == '__main__':
    main()
