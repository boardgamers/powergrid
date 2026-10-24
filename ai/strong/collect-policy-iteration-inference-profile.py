"""Pin and independently inspect the HF concurrency experiment outputs."""
import gzip
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def normalized(row):
    return {**{k: v for k, v in row.items() if k not in ['timing', 'rollouts']},
            'rollouts': sorted(row['rollouts'], key=lambda r: r['env'])}


def main():
    p = read(ROOT/'ai/strong/policy-iteration-inference-profile-protocol-v2.json')
    old = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    source = read(ROOT/'ai/strong/policy-iteration-inference-profile-source-v2.json')
    guard = read(ROOT/'ai/runs/policy-iteration-inference-profile-launch-v2.json')
    assert guard['stage'] == 'launched' and guard['source'] == source
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    print({'job_id': guard['job_id'], 'status': job.status.stage}, flush=True)
    if job.status.stage != 'COMPLETED':
        return
    out = ROOT/'ai/runs/policy-iteration-inference-profile-verified-v2'
    if out.exists():
        intent = read(out/'collection-intent.json')
        assert intent['job_id'] == guard['job_id'] and intent['source'] == source
    else:
        out.mkdir()
        intent = {'job_id': guard['job_id'], 'source': source, 'revision': api.model_info(old['repo']).sha,
                  'prefix': 'runs/policy-iteration-inference-hf-profile-v2'}
        write(out/'collection-intent.json', intent)
    for file in ['profile.json', 'microbenchmark.json', 'continuations.jsonl.gz']:
        data = Path(hf_hub_download(old['repo'], intent['prefix'] + '/' + file, revision=intent['revision'])).read_bytes()
        if (out/file).exists():
            assert (out/file).read_bytes() == data
        else:
            (out/file).write_bytes(data)
    report, micro = read(out/'profile.json'), read(out/'microbenchmark.json')
    assert report['passed'] and not report['small']
    assert report['source_revision'] == source['revision'] and report['source_sha256'] == source['sha256']
    assert report['protocol_sha256'] == source['protocol_sha256']
    assert report['model_sha256'] == micro['model_sha256'] == old['model']['sha256']
    assert micro['all_decisions_identical'] and micro['all_raw_outputs_identical'] and micro['positions'] == 2553
    for file, sha in report['artifacts'].items():
        assert digest(out/file) == sha
    with gzip.open(out/'continuations.jsonl.gz', 'rt') as f:
        rows = list(map(json.loads, f))
    assert [r['record'] for r in rows] == report['records']
    assert {(r['record']['rootId'], r['record']['mode']) for r in rows} == {(rid, m) for rid in p['root_ids'] for m in p['modes']}
    assert len(rows) == 4
    total = 0
    for item in rows:
        a, b, r = item['serial'], item['concurrent'], item['record']
        assert normalized(a) == normalized(b)
        assert a['rootId'] == r['rootId'] and a['mode'] == r['mode'] and a['samples'] == 96
        assert a['seed'] == 'strategic-teacher-public-v1-' + r['rootId'] + '-a'
        assert a['usable'] and a['outer_truncations'] == 0 and a['nested_search']['truncated'] == 0
        assert r['serial'] == a['timing'] and r['concurrent'] == b['timing']
        assert r['wall_speedup'] == a['timing']['seconds']/b['timing']['seconds']
        assert r['all_outcomes_identical'] and len(r['choice_trace']['choice_transcript_sha256']) == 64
        outcomes = {str(i): [None]*96 for i in a['options']}
        identities = set()
        for rollout in a['rollouts']:
            index, sample = rollout['actionIndex'], rollout['sample']
            assert (sample, index) not in identities and index in a['options'] and 0 <= sample < 96
            identities.add((sample, index))
            assert not rollout['truncated'] and 0 <= rollout['value'] <= 1 and 0 <= rollout['steps'] <= 2400
            outcomes[str(index)][sample] = rollout['value']
        assert len(identities) == r['rollouts_per_condition'] == 96*len(a['options'])
        assert outcomes == a['sample_outcomes']
        base = outcomes[str(a['model_proposal'])]
        assert a['paired_advantages_over_proposal'] == {k: [v-b for v, b in zip(vs, base)] for k, vs in outcomes.items()}
        total += 2*len(identities)
    assert report['rollouts'] == total
    result = {'verified': True, 'job_id': guard['job_id'], 'source': source,
              'revision': intent['revision'], 'prefix': intent['prefix'], 'rollouts': total,
              'full_continuation_cases': 4, 'cases': report['records'],
              'microbenchmark_positions': 2553, 'all_microbenchmark_raw_outputs_identical': True,
              'wall_speedup': sum(r['serial']['seconds'] for r in report['records'])/sum(r['concurrent']['seconds'] for r in report['records']),
              'cpu_count': report['cpu_count'], 'affinity_count': report['affinity_count'],
              'artifact_sha256': {f: digest(out/f) for f in ['profile.json', 'microbenchmark.json', 'continuations.jsonl.gz']},
              'scope': 'HF CPU inference-concurrency experiment; exact logged policy-choice transcripts checked inside the frozen worker, terminal data and pairing independently checked here. Not gradients, an8840U benchmark, or model strength.',
              'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-inference-hf-profile-v2.json', result)
    write(out/'verified.json', result)
    print({'verified': True, 'rollouts': total, 'wall_speedup': result['wall_speedup'], 'affinity': result['affinity_count']}, flush=True)


if __name__ == '__main__':
    main()
