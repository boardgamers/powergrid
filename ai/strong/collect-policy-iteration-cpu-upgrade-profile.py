"""Verify the alternative CPU workload against the pinned CPU Performance run."""
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def normalized(row):
    return {**{k: v for k, v in row.items() if k not in ['timing', 'rollouts']},
            'rollouts': sorted(row['rollouts'], key=lambda r: r['env'])}


def verify(directory, source, protocol, model_sha):
    report = read(directory/'profile.json')
    assert report['passed'] and not report['small'] and not report['gradients']
    assert report['source_revision'] == source['revision'] and report['source_sha256'] == source['sha256']
    assert report['protocol_sha256'] == source['protocol_sha256']
    assert report['model_sha256'] == model_sha
    assert report['artifacts'] == {'continuations.jsonl.gz': digest(directory/'continuations.jsonl.gz')}
    with gzip.open(directory/'continuations.jsonl.gz', 'rt') as stream:
        rows = list(map(json.loads, stream))
    assert len(rows) == 4 and [r['record'] for r in rows] == report['records']
    assert {(r['record']['rootId'], r['record']['mode']) for r in rows} == {
        (root, mode) for root in protocol['root_ids'] for mode in protocol['modes']}
    total = 0
    for item in rows:
        a, b, record = item['serial'], item['concurrent'], item['record']
        assert normalized(a) == normalized(b)
        assert a['rootId'] == record['rootId'] and a['mode'] == record['mode'] and a['samples'] == 96
        assert a['seed'] == 'strategic-teacher-public-v1-' + a['rootId'] + '-a'
        assert a['usable'] and a['outer_truncations'] == 0 and a['nested_search']['truncated'] == 0
        assert record['serial'] == a['timing'] and record['concurrent'] == b['timing']
        assert record['wall_speedup'] == a['timing']['seconds']/b['timing']['seconds']
        assert record['all_outcomes_identical'] and len(record['choice_trace']['choice_transcript_sha256']) == 64
        outcomes, identities = {str(i): [None]*96 for i in a['options']}, set()
        for rollout in a['rollouts']:
            index, sample = rollout['actionIndex'], rollout['sample']
            assert (sample, index) not in identities and index in a['options'] and 0 <= sample < 96
            assert not rollout['truncated'] and 0 <= rollout['value'] <= 1 and 0 <= rollout['steps'] <= 2400
            identities.add((sample, index))
            outcomes[str(index)][sample] = rollout['value']
        assert len(identities) == record['rollouts_per_condition'] == 96*len(a['options'])
        assert outcomes == a['sample_outcomes']
        parent = outcomes[str(a['model_proposal'])]
        assert a['paired_advantages_over_proposal'] == {k: [v-p for v, p in zip(vs, parent)] for k, vs in outcomes.items()}
        total += 2*len(identities)
    assert total == report['rollouts'] == 3072
    return report, {(r['record']['rootId'], r['record']['mode']): r for r in rows}


def main():
    source = read(ROOT/'ai/strong/policy-iteration-inference-profile-source-v2.json')
    protocol = read(ROOT/'ai/strong/policy-iteration-inference-profile-protocol-v2.json')
    teacher = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    guard = read(ROOT/'ai/runs/policy-iteration-cpu-upgrade-profile-launch-v2.json')
    reference_path = ROOT/guard['reference_file']
    reference = read(reference_path)
    assert digest(reference_path) == guard['reference_sha256']
    assert guard['stage'] == 'launched' and guard['source'] == source == reference['source']
    assert guard['flavor'] == 'cpu-upgrade' and not guard['full_label_jobs_changed']
    assert reference['verified'] and reference['rollouts'] == 3072
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    status = {'checked_at': datetime.now(timezone.utc).isoformat(), 'job_id': guard['job_id'],
              'stage': job.status.stage, 'message': job.status.message, 'started_at': str(job.started_at)}
    write(ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-status-v2.json', status)
    print(status, flush=True)
    if job.status.stage != 'COMPLETED':
        return
    out = ROOT/'ai/runs/policy-iteration-cpu-upgrade-profile-verified-v2'
    if out.exists():
        intent = read(out/'collection-intent.json')
        assert intent['job_id'] == guard['job_id'] and intent['source'] == source
        assert intent['prefix'] == guard['artifact_prefix']
    else:
        out.mkdir()
        intent = {'job_id': guard['job_id'], 'source': source, 'prefix': guard['artifact_prefix'],
                  'revision': api.model_info(teacher['repo']).sha}
        write(out/'collection-intent.json', intent)
    def download(pin, file, directory):
        data = Path(hf_hub_download(teacher['repo'], pin['prefix']+'/'+file, revision=pin['revision'])).read_bytes()
        target = directory/file
        if target.exists():
            assert target.read_bytes() == data
        else:
            target.write_bytes(data)
    files = ['profile.json', 'continuations.jsonl.gz', 'micro.json', 'environment.json']
    for file in files:
        download(intent, file, out)
    old = out/'reference'
    old.mkdir(exist_ok=True)
    for file in ['profile.json', 'continuations.jsonl.gz']:
        download(reference, file, old)
        assert digest(old/file) == reference['artifact_sha256'][file]
    report, rows = verify(out, source, protocol, teacher['model']['sha256'])
    previous, old_rows = verify(old, source, protocol, teacher['model']['sha256'])
    cases = []
    for key, row in rows.items():
        original = old_rows[key]
        for condition in ['serial', 'concurrent']:
            assert normalized(row[condition]) == normalized(original[condition]), (key, condition)
        assert row['record']['choice_trace'] == original['record']['choice_trace']
        cases.append({'rootId': key[0], 'mode': key[1], 'players': row['record']['players'],
                      'upgrade_seconds': row['concurrent']['timing']['seconds'],
                      'performance_seconds': original['concurrent']['timing']['seconds'],
                      'upgrade_slowdown': row['concurrent']['timing']['seconds']/original['concurrent']['timing']['seconds']})
    micro, environment = read(out/'micro.json'), read(out/'environment.json')
    assert micro['all_decisions_identical'] and micro['all_raw_outputs_identical'] and micro['positions'] == 2553
    assert micro['model_sha256'] == teacher['model']['sha256']
    assert environment['requested_flavor'] == 'cpu-upgrade'
    result = {'verified': True, 'job_id': guard['job_id'], 'source': source, 'reference': reference,
              'revision': intent['revision'], 'prefix': intent['prefix'], 'environment': environment,
              'rollouts': 3072, 'cases': cases, 'full_trajectories_and_choice_transcripts_match_reference': True,
              'microbenchmark_positions': 2553, 'all_microbenchmark_raw_outputs_identical': True,
              'upgrade_slowdown': sum(r['upgrade_seconds'] for r in cases)/sum(r['performance_seconds'] for r in cases),
              'worst_case_upgrade_slowdown': max(r['upgrade_slowdown'] for r in cases),
              'artifact_sha256': {file: digest(out/file) for file in files},
              'full_label_jobs_changed': False, 'gradients': False, 'qualification_eligible': False,
              'scope': 'Fixed-workload hardware measurement. Not trained-model strength or an AMD8840U benchmark.'}
    write(out/'verified.json', result)
    write(ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json', result)
    print({k: result[k] for k in ['verified', 'job_id', 'rollouts', 'upgrade_slowdown', 'worst_case_upgrade_slowdown']}, flush=True)


if __name__ == '__main__':
    main()
