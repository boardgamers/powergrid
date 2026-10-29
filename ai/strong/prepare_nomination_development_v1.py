"""Prepare an isolated schema-4.4 research runtime and paired development screen."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest

OUT = ROOT/'ai/runs/nomination-discount-development-v1'
BASE = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
PROTOCOL = ROOT/'ai/strong/nomination-discount-development-protocol-v1.json'
ARMS = ('parent', 'd0-all0', 'd0-all1', 'd1-all0', 'd1-all1')
PATCHES = {
 'ai/strong/hybrid-continuations.cjs': ("const REVISIONS = ['4.2-discard-correction', '4.3-strategic-correction'];", "const REVISIONS = ['4.2-discard-correction', '4.3-strategic-correction', '4.4-auction-discount'];"),
 'ai/strong/encoders.cjs': ("    if (revision === '4.3-strategic-correction')", "    if (revision === '4.4-auction-discount') return require('./features-v4_4.cjs');\n    if (revision === '4.3-strategic-correction')"),
 'ai/strong/hybrid_search.py': ("'4.3-strategic-correction': (1217, 101)}", "'4.3-strategic-correction': (1217, 101), '4.4-auction-discount': (1218, 103)}"),
 'ai/strong/public_policy_runtime_v1.py': ("spec['feature_revision'] != '4.3-strategic-correction'", "spec['feature_revision'] not in ('4.3-strategic-correction', '4.4-auction-discount')"),
 'ai/strong/public_policy_final_audit_v1.py': ("identity['featureRevision'] == '4.3-strategic-correction'", "identity['featureRevision'] in ('4.3-strategic-correction', '4.4-auction-discount')"),
 'ai/strong/population_policy_verification.py': ("row['featureRevision'] == '4.3-strategic-correction'", "row['featureRevision'] in ('4.3-strategic-correction', '4.4-auction-discount')"),
 'ai/strong/public_policy_final_contract_v1.py': ("contract['purpose'] in ('engineering', 'final')", "contract['purpose'] == 'engineering'"),
}


def main():
    assert not OUT.exists() and not PROTOCOL.exists(), 'Inspect existing source, never overwrite'
    training = read(ROOT/'ai/strong/nomination-discount-training-results-v1.json')
    exports = read(ROOT/'ai/strong/nomination-discount-export-v1.json')
    assert training['complete'] and exports['complete'] and len(exports['arms']) == 4
    assert read(ROOT/'ai/strong/nomination-discount-training-evidence-v1.json')['remote_archive_verified']
    old = read(BASE/'manifest.json')
    assert digest(BASE/'manifest.json') == 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'
    assert all(digest(BASE/name) == sha for name, sha in old.items())
    OUT.mkdir(); artifact = OUT/'artifact'; shutil.copytree(BASE, artifact)
    bundle = OUT/'bundle'; overlay = bundle/'overlay'; overlay.mkdir(parents=True)
    changed = []
    for name, (before, after) in PATCHES.items():
        path = artifact/name; text = path.read_text(); assert text.count(before) == 1, name
        path.write_text(text.replace(before, after)); changed.append(name)
    name = 'ai/strong/features-v4_4.cjs'; shutil.copyfile(ROOT/name, artifact/name); changed.append(name)
    for arm in exports['arms']:
        name = 'models/'+arm['arm']+'.onnx'; target = artifact/name; target.parent.mkdir(exist_ok=True)
        source = ROOT/f"ai/runs/nomination-discount-export-v1/{arm['arm']}/inference64.onnx"
        assert digest(source) == arm['files']['inference64.onnx']; shutil.copyfile(source, target); changed.append(name)
    pins = {**old, **{name: digest(artifact/name) for name in changed}}
    (artifact/'manifest.json').write_text(json.dumps(pins, indent=2)+'\n')
    changed.append('manifest.json'); manifest_sha = digest(artifact/'manifest.json')
    base_spec = read(BASE/'policies/filter.json'); identities = {}; descriptors = {}
    now = datetime.now(timezone.utc).isoformat(); controls = bundle/'controls'; controls.mkdir()
    from public_policy_final_audit_v1 import PROTOCOL_SHA
    for arm in ARMS:
        model_path = 'policy.onnx' if arm == 'parent' else 'models/'+arm+'.onnx'
        revision = '4.3-strategic-correction' if arm == 'parent' else '4.4-auction-discount'
        spec = {**base_spec, 'feature_revision': revision, 'model': {'path': model_path, 'sha256': digest(artifact/model_path)},
                'runtime_manifest': {'path': 'manifest.json', 'sha256': manifest_sha}}
        name = f'policies/nomination-{arm}.json'; save(artifact/name, spec); descriptors[arm] = name; changed.append(name)
        identity = {'policySha256': digest(artifact/name), 'runtimeManifestSha256': manifest_sha,
                    'modelSha256': spec['model']['sha256'], 'featureRevision': revision,
                    'backend': spec['backend'], 'settings': spec['settings']}
        identities[arm] = identity
        save(controls/(arm+'.candidate.json'), {'status': 'engineering', 'frozen_at': now, 'identity': identity,
             'protocol_sha256': PROTOCOL_SHA, 'selection_evidence': None})
    rows = []
    for arm in ARMS:
        for opponent in ('search_geo', 'a260'):
            for n in range(2, 7):
                name = f'pg-nom-dev-v1-{arm}-{opponent.replace("_", "-")}-{n}p'
                shard = {'name': name, 'group': f'{opponent}/{n}p', 'players': n, 'start': 0, 'deals': 4,
                         'seed': f'nomination-discount-development-v1-{n}p', 'opponent': opponent,
                         'opponent_sha256': digest(artifact/'final-opponent-a260.onnx') if opponent == 'a260' else None,
                         'games': 16*n}
                contract = {'version': 1, 'purpose': 'engineering', 'created_at': now,
                            'candidate_sha256': digest(controls/(arm+'.candidate.json')), 'protocol_sha256': PROTOCOL_SHA,
                            'identity': identities[arm], 'shard': shard, 'launch_authorization': None}
                save(controls/(name+'.contract.json'), contract)
                rows.append({'name': name, 'arm': arm, 'descriptor': descriptors[arm], 'shard': shard,
                             'candidate': f'controls/{arm}.candidate.json', 'contract': f'controls/{name}.contract.json',
                             'opponent_model': 'final-opponent-a260.onnx' if opponent == 'a260' else None})
    assert len(rows) == 50 and sum(r['shard']['games'] for r in rows) == 3200
    protocol = {'created_at': now, 'purpose': 'Paired whole-game development screen; no qualification or final evaluation',
        'arms': list(ARMS), 'identities': identities, 'rows': rows, 'games': 3200, 'jobs': 50,
        'rules': ['original/open', 'original/sealed', 'recharged/open', 'recharged/sealed'], 'players': [2, 3, 4, 5, 6],
        'independent_deals_per_cell': 4, 'seat_rotations': 'All seats in each deal/rule cell',
        'primary_comparison': 'Each trained arm versus unchanged parent control on identical deals/seats/opponents; summarize paired deal-level win-credit differences. Four deals is a screen, not precise qualification.',
        'all_arms_retained': True, 'candidate_search': False, 'loss_filter': 'Unchanged frozen parent building-loss filter',
        'workers': 4, 'threads': 1, 'flavor': 'cpu-upgrade', 'timeout': '5h',
        'base_source': read(ROOT/'ai/strong/auction-discount-teacher-protocol-v2.json')['current_source'],
        'base_artifact_manifest_sha256': digest(BASE/'manifest.json'), 'runtime_manifest_sha256': manifest_sha,
        'training_results_sha256': digest(ROOT/'ai/strong/nomination-discount-training-results-v1.json'),
        'exports_sha256': digest(ROOT/'ai/strong/nomination-discount-export-v1.json'),
        'changed_runtime_files': changed, 'reserved_final_seeds_used': False, 'qualified': False}
    # Validate the real runner in its isolated copy; this does not execute games.
    for row in rows:
        command = [sys.executable, '-B', str(artifact/'ai/strong/public_policy_final_runner_v1.py'),
            '--artifact', str(artifact), '--descriptor', row['descriptor'], '--candidate', str(bundle/row['candidate']),
            '--contract', str(bundle/row['contract']), '--workers', '4', '--output', str(OUT/'never-executed'/row['name'])]
        if row['opponent_model']: command += ['--opponent-model', str(artifact/row['opponent_model'])]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    assert not (OUT/'never-executed').exists()
    for name in changed:
        target = overlay/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact/name, target)
    save(bundle/'overlay.json', {'expected_base_manifest_sha256': digest(BASE/'manifest.json'),
        'files': {name: {'before': digest(BASE/name) if (BASE/name).exists() else None, 'after': digest(artifact/name)} for name in changed}})
    shutil.copyfile(ROOT/'ai/strong/run_nomination_development_v1.py', bundle/'run_nomination_development_v1.py')
    shutil.copytree(ROOT/'ai/runs/auction-discount-teacher-prepared-v1/bundle/transport', bundle/'transport')
    save(bundle/'protocol.json', protocol); save(PROTOCOL, protocol)
    save(bundle/'manifest.json', {str(p.relative_to(bundle)): digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()})
    print({'prepared': True, 'jobs': 50, 'games': 3200, 'validated_job_contracts': 50, 'changed_runtime_files': len(changed)}, flush=True)


if __name__ == '__main__': main()
