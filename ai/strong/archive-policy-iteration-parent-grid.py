"""Save all parent reference handles and the exact verified runtime admission."""
from collections import Counter
import argparse
import importlib.util
from pathlib import Path
import re
import shutil
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--name', default='policy-iteration-parent-grid-launch-evidence-v2')
    parser.add_argument('--diagnostic', type=Path)
    args = parser.parse_args()
    assert re.fullmatch(r'policy-iteration-parent-[a-z0-9-]+', args.name)
    diagnostic = read(args.diagnostic) if args.diagnostic else None
    spec = importlib.util.spec_from_file_location('grid_archive_manager', ROOT/'ai/strong/manage-policy-iteration-development-grid.py')
    grid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grid)
    plan = grid.require_plan('parent')
    if diagnostic:
        assert diagnostic['source'] == plan['source'] and diagnostic['parent_pin'] == plan['model_pin']
        assert diagnostic['protocol_sha256'] == plan['protocol_sha256']
        assert not diagnostic['qualification_eligible'] and not diagnostic['reserved_final_seeds_used']
    status = read(ROOT/'ai/strong/policy-iteration-development-status-v2.json')
    current = {j['case']: j for j in status['jobs']}
    guards = []
    for row in plan['shards']:
        path = grid.manager.GUARDS/(row['case']+'.json')
        guard = grid.matching_guard(path, row, plan)
        assert current[row['case']]['job_id'] == guard['job_id']
        guards.append(path)
    assert len(guards) == len({read(p)['job_id'] for p in guards}) == 108
    out = ROOT/'ai/runs'/args.name
    out.mkdir(exist_ok=False)
    names = ['policy-iteration-development-protocol-v2.json', 'policy-iteration-development-source-v2.json',
             'policy-iteration-development-preflight-v2.json', 'policy-iteration-development-runtime-probes-v2.json',
             'policy-iteration-development-status-v2.json', 'manage-policy-iteration-development.py',
             'manage-policy-iteration-development-grid.py', 'compare-policy-iteration-development.py',
             'policy-iteration-collection-grid-controls-v2.json', 'archive-policy-iteration-parent-grid.py',
             'policy_iteration_evidence_archive.py']
    for name in names:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    if diagnostic:
        shutil.copy2(args.diagnostic, out/args.diagnostic.name)
        shutil.copy2(ROOT/'ai/strong/inspect-policy-iteration-reference.py', out/'inspect-policy-iteration-reference.py')
    shutil.copy2(grid.plan_path('parent'), out/'parent-plan.json')
    (out/'guards').mkdir()
    for path in grid.manager.GUARDS.glob('*.json'):
        shutil.copy2(path, out/'guards'/path.name)
    for n in [2,6]:
        name=f'smoke-parent-{n}p-search_geo-0-1'
        shutil.copytree(grid.manager.VERIFIED/name, out/name)
    verified_parent = []
    for row in plan['shards']:
        if diagnostic and row['case'] not in diagnostic['provenance']:
            continue
        directory = grid.manager.VERIFIED/row['case']
        if (directory/'verified.json').exists():
            report = read(directory/'verified.json')
            if diagnostic:
                assert digest(directory/'verified.json') == diagnostic['provenance'][row['case']]['verified_sha256']
            assert report['verified'] and report['source'] == plan['source']
            assert report['model_pin_sha256'] == plan['model_pin_sha256']
            for file, sha in report['artifacts'].items():
                assert digest(directory/file) == sha
            shutil.copytree(directory, out/row['case'])
            verified_parent.append(report)
    if diagnostic:
        assert len(verified_parent) == diagnostic['verified_shards']
        assert sum(r['summary']['games'] for r in verified_parent) == diagnostic['verified_games']
    for name in ['policy-iteration-development-parent-grid-dry-v2.log', 'policy-iteration-development-parent-grid-launch-v2.log']:
        shutil.copy2(ROOT/'ai/runs'/name, out/name)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    archive = upload_evidence(out)
    report = {**archive,
              'shards_submitted':108, 'planned_games':6720, 'plan_sha256':digest(grid.plan_path('parent')),
              'status_checked_at':status['checked_at'],
              'status_counts':dict(Counter(current[row['case']]['authoritative_status'] for row in plan['shards'])),
              'timeout_hours':plan['runtime_admission']['timeout_hours'], 'flavor':'cpu-upgrade',
              'both_runtime_probes_verified':True, 'probe_games':32, 'parent_is_unqualified':True,
              'verified_parent_cases':len(verified_parent),
              'verified_parent_games':sum(r['summary']['games'] for r in verified_parent),
              'gradients':False, 'qualification_eligible':False, 'reserved_final_seeds_used':False}
    if diagnostic:
        report.update(diagnostic=args.diagnostic.name, diagnostic_sha256=digest(args.diagnostic),
                      development_point_deficits=diagnostic['development_point_deficits'])
    write(ROOT/'ai/strong'/(args.name+'.json'),report)
    print(report,flush=True)


if __name__ == '__main__':
    main()
