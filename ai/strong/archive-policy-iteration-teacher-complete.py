"""Archive the full pilot assessment/provenance without duplicating pinned labels."""
import shutil
import statistics

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest


def main():
    result_path = ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json'
    result = read(result_path)
    assessment = read(ROOT/'ai/strong/policy-iteration-teacher-pilot-assessment-v2.json')
    status = read(ROOT/'ai/strong/policy-iteration-teacher-pilot-status-v2.json')
    assert result['complete'] and result['complete_cases'] == 60 and result['rollouts'] == 705408
    assert assessment['pilot_results_sha256'] == digest(result_path)
    assert status['status_counts'] == {'COMPLETED': 60}
    probe = read(ROOT/'ai/strong/policy-iteration-teacher-probe-results-v2.json')
    cases = {}
    for case, r in result['cases'].items():
        small = sum(t['seconds'] for t in probe['cases'][case]['timings'])
        wall = sum(t['seconds'] for t in r['timings'])
        cases[case] = {'rollouts': r['rollouts'], 'search_wall_seconds': wall,
                       'policy_seconds': sum(t['policy_seconds'] for t in r['timings']),
                       'engine_rpc_seconds': sum(t['engine_seconds'] for t in r['timings']),
                       'large_to_probe_wall_ratio': wall/small, 'linear_sample_ratio': 48}
    throughput = {'complete_pilot': True, 'cases': cases,
                  'median_large_to_probe_wall_ratio': statistics.median(c['large_to_probe_wall_ratio'] for c in cases.values()),
                  'policy_fraction_of_search_wall': sum(c['policy_seconds'] for c in cases.values())/sum(c['search_wall_seconds'] for c in cases.values()),
                  'note': 'Measured complete pilot only. Engine RPC includes serialization, pipe waits and JS computation; it does not isolate engine CPU time. No model-strength conclusion.',
                  'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-teacher-throughput-complete-v2.json', throughput)
    out = ROOT/'ai/runs/policy-iteration-teacher-pilot-complete-evidence-v2'
    out.mkdir(exist_ok=False)
    files = ['policy-iteration-teacher-pilot-results-v2.json', 'policy-iteration-teacher-pilot-assessment-v2.json',
             'policy-iteration-teacher-throughput-complete-v2.json', 'policy-iteration-teacher-pilot-status-v2.json',
             'policy-iteration-teacher-source-v2.json', 'policy-iteration-teacher-protocol-v2.json',
             'policy-iteration-teacher-preflight-v2.json', 'policy-iteration-teacher-assessment-preflight-v2.json',
             'manage-policy-iteration-teacher.py', 'archive-policy-iteration-teacher-complete.py']
    for file in files:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    for directory, pattern, destination in [
        ('policy-iteration-teacher-pilot-launches-v2', '*.json', 'guards'),
        ('policy-iteration-teacher-pilot-verified-v2', '*/verified.json', 'verified')]:
        for src in sorted((ROOT/'ai/runs'/directory).glob(pattern)):
            target = out/destination/(src.parent.name + '.json' if destination == 'verified' else src.name)
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(src, target)
    manifest = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    write(out/'manifest.json', manifest)
    prefix = 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id='coyotte508/powergrid-ai-germany-v1', folder_path=out, path_in_repo=prefix)
    descriptor = {'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': digest(out/'manifest.json'),
                  'file_count': len(manifest), 'complete_cases': 60, 'rollouts': 705408,
                  'assessment_sha256': digest(ROOT/'ai/strong/policy-iteration-teacher-pilot-assessment-v2.json'),
                  'trained': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-teacher-pilot-complete-evidence-v2.json', descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
