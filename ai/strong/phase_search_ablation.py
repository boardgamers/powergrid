"""Isolate the causal complete-game effects of auction versus building search."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import os
from pathlib import Path
import runpy
import sys

from huggingface_hub import HfApi, hf_hub_download
from search_transfer import ROOT, read, write, digest, verify as verify_transfer, module, summarize

PROTOCOL = ROOT/'ai/strong/phase-search-ablation-protocol-v1.json'
PHASES = ('auction', 'building')


class PhaseRouter:
    """Filter search requests using an extra public observation field only."""
    def __init__(self, arm):
        assert arm in ['all', *PHASES]
        self.arm = arm; self.observations = None; self.counts = {}

    def filter(self, request):
        if request['op'] != 'step': return request
        assert len(request['actions']) == len(self.observations)
        actions = []
        for action, row in zip(request['actions'], self.observations):
            if action is None:
                assert row is None; actions.append(action); continue
            if not isinstance(action, dict):
                actions.append(action); continue  # Frozen neural opponent or raw choice.
            assert row['roles'][row['seat']] == 'learner'
            phase = row['searchPhase']; assert phase in [*PHASES, 'other']
            searched = phase in PHASES and (self.arm == 'all' or self.arm == phase)
            if phase in PHASES:
                count = self.counts.setdefault(row['episode'], {p: {'opportunities': 0, 'searched': 0} for p in PHASES})[phase]
                count['opportunities'] += 1; count['searched'] += int(searched)
            actions.append(action if searched else action['proposal'])
        return {**request, 'actions': actions}

    def observe(self, response):
        self.observations = response['observations']
        for row in response['ended']:
            row['phaseRouting'] = self.counts.pop(row['episode'], {p: {'opportunities': 0, 'searched': 0} for p in PHASES})
        return response


def case_for(protocol, case_id):
    return next(c for c in protocol['cases'] if c['id'] == case_id)


def case_config(protocol, case_id, arm, smoke):
    case = dict(case_for(protocol, case_id))
    if smoke:
        case['deals'] = 1
        if arm != 'all': case['seed'] = protocol['smoke']['seed_template'].format(case=case_id)
    return case


def verify(report, protocol, case_id, arm, smoke):
    assert arm in ['all', *PHASES] and (arm != 'all' or smoke)
    case = case_config(protocol, case_id, arm, smoke)
    assert report['candidate_search_phases'] == arm
    summary = verify_transfer(report, protocol, '10102', case, guided=True)
    total = {p: {'opportunities': 0, 'searched': 0} for p in PHASES}
    for row in report['results']:
        counts = row['phaseRouting']; assert set(counts) == set(PHASES)
        for phase, values in counts.items():
            assert set(values) == {'opportunities', 'searched'}
            assert all(type(v) is int and v >= 0 for v in values.values())
            assert values['searched'] == (values['opportunities'] if arm in ['all', phase] else 0)
            for k in values: total[phase][k] += values[k]
        assert sum(v['searched'] for v in counts.values()) == row['searchStats'].get('learner', {}).get('decisions', 0)
    assert all(v['opportunities'] > 0 for v in total.values())
    assert sum(v['searched'] for v in total.values()) > 0
    return {**summary, 'phase_routing': total}


def exact_control(report, baseline):
    expected = {r['episode']: r for r in baseline['results']}
    for row in report['results']:
        original = {k: v for k, v in row.items() if k != 'phaseRouting'}
        assert original == expected[row['episode']], 'Instrumentation changed the all-search control'
    return {'games': len(report['results']), 'all_raw_game_rows_match': True}


def main(a):
    protocol = read(PROTOCOL); case = case_config(protocol, a.case, a.arm, a.smoke)
    assert a.arm != 'all' or a.smoke
    pin = protocol['models']['10102']; out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    status = {'arm': a.arm, 'case': a.case, 'smoke': a.smoke, 'status': 'running',
              'protocol_sha256': digest(PROTOCOL), 'source_revision': os.environ.get('SOURCE_REVISION'),
              'source_sha256': os.environ.get('SOURCE_SHA256'), 'trained': False, 'qualification_eligible': False}
    try:
        model = hf_hub_download(protocol['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']; write(out/'checkpoint.json', pin)
        argv = [str(ROOT/'ai/strong/evaluate.py'), model, '--players', str(case['players']),
                '--games', str(case['deals']*4*case['players']), '--workers', '24', '--seed', case['seed'],
                '--search-samples', '48', '--geographic-search', '--search-scope', 'all', '--output', str(out/'search.json')]
        if case['opponent'] == 'a260':
            other = protocol['frozen_opponent']; path = hf_hub_download(protocol['repo'], other['path'], revision=other['revision'])
            assert digest(path) == other['sha256']; argv += ['--opponent-model', path]
        else: argv += ['--opponent', case['opponent']]
        sys.path.insert(0, str(ROOT/'ai'))
        import pool
        original_pool = pool.EnginePool
        router = PhaseRouter(a.arm)
        class RoutedPool(original_pool):
            def call(self, request): return router.observe(super().call(router.filter(request)))
        pool.EnginePool = RoutedPool
        old_argv = sys.argv; old_node = os.environ.get('NODE_OPTIONS')
        assert not old_node, 'Unexpected node instrumentation'
        os.environ['NODE_OPTIONS'] = '--require '+str(ROOT/'ai/strong/capture-search-phase.cjs')
        sys.argv = argv
        try:
            with (out/'search.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                runpy.run_path(str(ROOT/'ai/strong/evaluate.py'), run_name='__main__')
        finally:
            sys.argv = old_argv; pool.EnginePool = original_pool
            os.environ.pop('NODE_OPTIONS', None)
        assert not router.counts
        report = read(out/'search.json'); report['candidate_search_phases'] = a.arm; write(out/'search.json', report)
        summary = verify(report, protocol, a.case, a.arm, a.smoke)
        if a.arm == 'all':
            base = case['baselines']['all']; path = hf_hub_download(protocol['repo'], base['path'], revision=base['revision'])
            assert digest(path) == base['sha256']; (out/'control.json').write_bytes(Path(path).read_bytes())
            summary['control_parity'] = exact_control(report, read(Path(path)))
        write(out/'summary.json', summary)
        status.update(status='complete', games=summary['games'], game_truncations=0, search_truncations=0)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        status['artifacts'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'phase-check.json', status)
        if a.upload: HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
            path_in_repo='runs/phase-search-ablation-'+('smoke-' if a.smoke else '')+f'v1-{a.arm}-{a.case}')
        print(status, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('arm', choices=['all', *PHASES])
    p.add_argument('case', choices=['search_geo-2p', 'search_geo-3p', 'a260-3p'])
    p.add_argument('output', type=Path); p.add_argument('--smoke', action='store_true'); p.add_argument('--upload', action='store_true')
    main(p.parse_args())
