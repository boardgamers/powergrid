"""Check batch packing and measure an unchanged trained search on existing data.

No new HF jobs, game seeds, gradients, candidate selection or default change.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import time

from huggingface_hub import hf_hub_download
import hybrid_search as hybrid
from hybrid_packed_inference import batch_layout, packed_predict

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('hybrid_profile', ROOT/'ai/strong/profile-trained-hybrid-search.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
read, write, digest = profile.read, profile.write, profile.digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prior = ROOT/'ai/runs/trained-hybrid-probe-v2'
    reference = read(prior/'assessment.json')
    assert reference['contracts_passed'] and reference['all_searches_usable']
    runtime = prior/'runtime'
    hashes = {ROOT/name: sha for name, sha in reference['code_hashes'].items()}
    hashes.update({runtime/name: sha for name, sha in reference['frozen_runtime_hashes'].items()})
    hashes[runtime/'ai/strong/hybrid-continuations.cjs'] = digest(ROOT/'ai/strong/hybrid-continuations.cjs')
    for name in ['probe-hybrid-batch-packing.py', 'hybrid_packed_inference.py', 'profile-trained-hybrid-search.py']:
        hashes[ROOT/'ai/strong'/name] = digest(ROOT/'ai/strong'/name)
    assert all(digest(p) == sha for p, sha in hashes.items())
    hybrid.WORKER = str(runtime/'ai/strong/hybrid-continuations.cjs')
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    manifest = read(prepared/'manifest.json')
    assert digest(prepared/'manifest.json') == reference['trained_manifest_sha256']
    parent = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    paths = {'parent': Path(hf_hub_download(parent['repo'], parent['model']['path'], revision=parent['model']['revision']))}
    paths.update({key: prepared/('local-package-'+key)/'policy.onnx' for key in manifest['models']})
    assert all(digest(path) == reference['models'][key] for key, path in paths.items())
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'code_hashes': {str(p.relative_to(ROOT)): sha for p, sha in hashes.items()},
        'source_probe_sha256': digest(prior/'assessment.json'), 'trained_manifest_sha256': digest(prepared/'manifest.json'),
        'models': reference['models'], 'batch_checks': {}, 'records': [], 'host': platform.node(),
        'processor': next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                          if line.startswith('model name')), 'threads': 4, 'workers': 4, 'samples_per_mode': 8,
        'layout_order': ['plain64', 'packed16', 'packed8', 'packed8', 'packed16', 'plain64'],
        'defaults_changed': False, 'gradients': False, 'hf_jobs_submitted': 0,
        'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'All 2553 existing serving roots plus prior-bid observations for public-0; 80 rule/count/phase '
            'cells for all five models. Six repetitions of one existing six-player Recharged/sealed building '
            'fixture measure cost and internal trace parity. No fresh strength or representative latency claim.'}
    started = time.perf_counter()
    node = hybrid.Node(hybrid.WORKER)
    try:
        fixtures = [json.loads(line) for line in (prepared/'fixtures.jsonl').open()]
        assert len(fixtures) == 2553
        cells = {}
        for fixture in fixtures:
            q = fixture['request']; s = q['state']
            cell = len(s['players']), s['options']['variant'], bool(s['options']['fastBid']), s['phase']
            cells.setdefault(cell, fixture)
        assert len(cells) == 80
        rows_by_revision = {}
        for revision in hybrid.FORMATS:
            rows = []
            for fixture in cells.values():
                data = node.call({**fixture['request'], 'op': 'prepare', 'featureRevision': revision})
                assert data['moves'] == fixture['legal']
                rows.extend([data['observation'], *[p['encoded'] for p in data['prior']]])
            rows_by_revision[revision] = rows
        full_rows = []
        for fixture in fixtures:
            data = node.call({**fixture['request'], 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
            assert data['moves'] == fixture['legal']
            full_rows.extend([data['observation'], *[p['encoded'] for p in data['prior']]])
        for key, path in paths.items():
            model = hybrid.Model(path, threads=4)
            rows = full_rows if key == 'public-0' else rows_by_revision[hybrid.model_revision(model)]
            serial = [model.predict(row['state'], row['actions'])[0] for row in rows]
            assert hybrid.predict_batch(model, rows) == serial
            for group_size in [8, 16]:
                assert packed_predict(model, rows, group_size, predict=hybrid.predict_batch) == serial
                assert packed_predict(model, list(reversed(rows)), group_size, predict=hybrid.predict_batch) == list(reversed(serial))
            assert packed_predict(model, [], 16, predict=hybrid.predict_batch) == []
            report['batch_checks'][key] = {'rows': len(rows), 'cells': 80,
                'root_fixtures': 2553 if key == 'public-0' else 80,
                'serial_plain_packed_and_reversed_rows_identical': True}
            print({'model': key, **report['batch_checks'][key]}, flush=True)
            write(args.output/'assessment.json', report)
            del model
        selected = read(prior/'selected-fixtures.json')['6p-building']
        write(args.output/'fixture.json', selected)
        expected = read(ROOT/'ai/runs/trained-hybrid-profile-v1/profile.json')['records'][0]
        for layout in report['layout_order']:
            model = hybrid.Model(paths['public-0'], threads=4)
            with batch_layout(layout):
                with profile.measured(model) as stats:
                    with hybrid.HybridSearch(model, samples=8, workers=4) as search:
                        result = search.choose(selected['fixture']['request'])
            row = {'layout': layout, 'stats': stats, 'result': result}
            report['records'].append(row)
            write(args.output/'assessment.json', report)
            assert profile.comparable(result) == profile.comparable(expected['result'])
            assert stats['choice_transcript_sha256'] == expected['stats']['choice_transcript_sha256']
            assert result['search']['truncated'] == 0
            print({'layout': layout, 'seconds': result['elapsedMs']/1000, 'onnx_seconds': stats['onnx_seconds'],
                'onnx_calls': stats['onnx_calls'], 'action_slot_utilization': stats['legal_action_slots']/stats['padded_action_slots'],
                'all_choices_and_outcomes_identical': True}, flush=True)
            del model
        assert len(report['records']) == 6
        assert all(digest(p) == sha for p, sha in hashes.items())
        report['passed'] = True
        report['all_internal_choices_and_terminal_outcomes_identical'] = True
    finally:
        node.close()
        report['seconds'] = time.perf_counter()-started
        write(args.output/'assessment.json', report)
    print({'passed': report['passed'], 'search_runs': len(report['records'])}, flush=True)


if __name__ == '__main__':
    main()
