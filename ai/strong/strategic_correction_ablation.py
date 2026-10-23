"""Isolate each learned strategic intervention on complete paired development games."""
import argparse
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
import gzip
import json
import os
from pathlib import Path
import runpy
import sys
from huggingface_hub import HfApi, hf_hub_download
from strategic_correction_screen import ROOT, read, write, digest, verifier, summarize, same

PROTOCOL = ROOT/'ai/strong/strategic-correction-ablation-protocol-v1.json'
PHASES = ('nomination','bid','building','other')


def phase(moves):
    if len(moves) < 2: return 'other'
    for name, kind in [('ChoosePowerPlant','nomination'),('Bid','bid'),('Build','building')]:
        if any(move['name'] == name for move in moves): return kind
    return 'other'


def model_path(pin):
    path = Path(hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision']))
    assert digest(path) == pin['files']['inference64.onnx']
    return path


def counts():
    return {kind:{'decisions':0,'disagreements':0,'applied':0} for kind in PHASES}


class Router:
    def __init__(self, arm, parent, decisions, roots):
        self.arm, self.parent = arm, parent
        self.decisions, self.roots = decisions, roots
        self.observations = None
        self.counts = {}; self.ordinals = Counter(); self.root_count = 0

    def filter(self, request):
        if request['op'] != 'step': return request
        assert len(request['actions']) == len(self.observations)
        actions = []
        for proposed,row in zip(request['actions'],self.observations):
            if proposed is None:
                assert row is None; actions.append(None); continue
            assert type(proposed) is int and row['roles'][row['seat']] == 'learner'
            assert row['featureRevision'] == '4.3-strategic-correction'
            parent,_ = self.parent.predict(row['state'][:1216],[a[:100] for a in row['actions']])
            root = row.get('strategicRoot')
            kind = phase(root['legal']) if root else 'other'
            assert (kind != 'other') == bool(row['state'][-1])
            different = proposed != parent
            if kind == 'other': assert not different, 'Correction changed an out-of-scope decision'
            applied = self.arm == 'all' or self.arm == kind
            chosen = proposed if applied else parent
            episode = row['episode']; ordinal = self.ordinals[episode]
            self.ordinals[episode] += 1
            stat = self.counts.setdefault(episode,counts())[kind]
            stat['decisions'] += 1; stat['disagreements'] += int(different)
            stat['applied'] += int(different and applied)
            record = {'episode':episode,'ordinal':ordinal,'seat':row['seat'],'round':row['round'],
                'variant':row['variant'],'sealed':row['sealed'],'phase':kind,
                'parent_index':parent,'candidate_index':proposed,'chosen_index':chosen,
                'different':different,'applied':different and applied}
            if root:
                moves = root['legal']; assert len(moves) == len(row['actions'])
                record.update(parent_move=moves[parent],candidate_move=moves[proposed],chosen_move=moves[chosen])
            self.decisions.write(json.dumps(record)+'\n')
            if different:
                self.roots.write(json.dumps({**record, **root})+'\n'); self.root_count += 1
            actions.append(chosen)
        return {**request,'actions':actions}

    def observe(self, response):
        self.observations = response['observations']
        for game in response['ended']:
            game['correctionRouting'] = self.counts.pop(game['episode'],counts())
        return response


def verify_local(out, key, n, arm, start, end, source=None, reencode=True):
    protocol = read(PROTOCOL); pin = protocol['models'][key]
    status = read(out/'ablation-check.json')
    expected = {'status':'complete','key':key,'players':n,'arm':arm,'start':start,'end':end,
        'protocol_sha256':digest(PROTOCOL),'games':(end-start)*4*n,
        'candidate_sha256':pin['files']['inference64.onnx'],
        'parent_sha256':protocol['models']['parent']['files']['inference64.onnx'],
        'game_truncations':0,'qualification_eligible':False}
    if source: expected.update(source_revision=source['revision'],source_sha256=source['sha256'])
    for name,value in expected.items(): assert status[name] == value, name
    for name,sha in status['artifacts'].items():
        assert Path(name).name == name and digest(out/name) == sha
    report = read(out/'evaluation.json')
    screen = {'players':n,'games':(end-start)*4*n,'opponent':'economic','deal_offset':start}
    verifier.verify_report(report,screen,{'hashes':{'latest.onnx':pin['files']['inference64.onnx']}},
        {'seed_template':protocol['seed_template'],'deal_offsets':list(range(start,end))},pin['feature_revision'])
    assert report['correction_arm'] == arm and report['async_rollout'] is False
    assert report['correction_parent_sha256'] == expected['parent_sha256']
    games = {r['episode']:r for r in report['results']}
    assert set(games) == set(range(start*4*n,end*4*n))
    totals = {}; ordinals = Counter(); disagreements = {}
    with gzip.open(out/'decisions.jsonl.gz','rt') as stream:
        for row in map(json.loads,stream):
            episode = row['episode']; game = games[episode]; kind = row['phase']
            assert kind in PHASES and row['ordinal'] == ordinals[episode]
            ordinals[episode] += 1
            assert row['seat'] == game['seat'] == episode//4%n
            assert row['variant'] == game['variant'] and row['sealed'] == game['sealed']
            different = row['parent_index'] != row['candidate_index']
            applied = different and arm in ['all',kind]
            assert row['different'] == different and row['applied'] == applied
            assert row['chosen_index'] == (row['candidate_index'] if arm in ['all',kind] else row['parent_index'])
            if kind == 'other': assert not different
            stat = totals.setdefault(episode,counts())[kind]
            stat['decisions'] += 1; stat['disagreements'] += int(different); stat['applied'] += int(applied)
            if different: disagreements[episode,row['ordinal']] = row
    for episode,game in games.items(): assert game['correctionRouting'] == totals.get(episode,counts())
    from infer import Model, Node
    parent = Model(model_path(protocol['models']['parent'])) if reencode else None
    candidate = Model(model_path(pin)) if reencode else None
    node = Node('strong/worker.cjs') if reencode else None
    seen = set()
    try:
        with gzip.open(out/'roots.jsonl.gz','rt') as stream:
            for row in map(json.loads,stream):
                identity = row['episode'],row['ordinal']; assert identity not in seen
                seen.add(identity); decision = disagreements[identity]
                # Capture's coarse auction/building phase is separate from the
                # exact nomination/bid/building tag used by the routing ledger.
                for name,value in decision.items():
                    if name != 'phase': assert row[name] == value
                assert phase(row['legal']) == decision['phase']
                q = row['request']; state = q['state']; assert q['player'] == row['seat']
                assert not state['powerPlantsDeck'] and not state['hiddenLog'] and state['seed'] == 'secret'
                assert 'powerPlantDeckAfterStep3' not in state and not state.get('automation',{}).get('plans')
                assert state['options']['showMoney'] and len(state['players']) == n
                if state['options']['fastBid']:
                    assert state['currentBid'] == 0
                    assert all(not p.get('bid') for i,p in enumerate(state['players']) if i != q['player'])
                for prefix in ['parent','candidate','chosen']:
                    assert row[prefix+'_move'] == row['legal'][row[prefix+'_index']]
                if reencode:
                    encoded = node.call({**q,'featureRevision':pin['feature_revision']})
                    assert encoded['moves'] == row['legal']
                    assert parent.predict(encoded['state'][:1216],[a[:100] for a in encoded['actions']])[0] == row['parent_index']
                    assert candidate.predict(encoded['state'],encoded['actions'])[0] == row['candidate_index']
    finally:
        if node: node.close()
    assert seen == set(disagreements) and len(seen) == status['disagreement_roots']
    combined = counts()
    for stats in totals.values():
        for kind in PHASES:
            for name,value in stats[kind].items(): combined[kind][name] += value
    return {**summarize(report['results'],protocol),'routing':combined,'disagreement_roots':len(seen),
        'public_choices_reproduced':len(seen) if reencode else None,'seconds':report['seconds'],
        'game_truncations':0,'qualification_eligible':False}


def run(args):
    protocol = read(PROTOCOL)
    assert args.key in ['11101','11102'] and args.players in protocol['players']
    assert args.arm in protocol['arms']+protocol['control_arms']
    assert args.start in range(0,16,4) and args.end in [args.start+1,args.start+4] and args.end<=16
    assert not os.environ.get('NODE_OPTIONS')
    pin = protocol['models'][args.key]; path = model_path(pin)
    sys.path.insert(0,str(ROOT/'ai'))
    from infer import Model
    import pool
    parent = Model(model_path(protocol['models']['parent']))
    out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    status = {'status':'running','key':args.key,'players':args.players,'arm':args.arm,'start':args.start,'end':args.end,
        'protocol_sha256':digest(PROTOCOL),'candidate_sha256':pin['files']['inference64.onnx'],
        'parent_sha256':parent.sha256,'source_revision':os.environ.get('SOURCE_REVISION'),
        'source_sha256':os.environ.get('SOURCE_SHA256'),'qualification_eligible':False}
    try:
        original = pool.EnginePool
        with gzip.open(out/'decisions.jsonl.gz','wt') as decisions, gzip.open(out/'roots.jsonl.gz','wt') as roots:
            router = Router(args.arm,parent,decisions,roots)
            class RoutedPool(original):
                def call(self, request): return router.observe(super().call(router.filter(request)))
            pool.EnginePool = RoutedPool
            argv = [str(ROOT/'ai/strong/evaluate.py'),str(path),'--players',str(args.players),
                '--deal-offset',str(args.start),'--games',str((args.end-args.start)*4*args.players),
                '--workers','24','--seed',protocol['seed_template'].format(players=args.players),
                '--opponent','economic','--output',str(out/'evaluation.json')]
            old_argv = sys.argv; sys.argv = argv
            os.environ['NODE_OPTIONS'] = '--require '+str(ROOT/'ai/strong/capture-strategic-training.cjs')
            try:
                with (out/'evaluation.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                    runpy.run_path(str(ROOT/'ai/strong/evaluate.py'),run_name='__main__')
            finally:
                sys.argv = old_argv; pool.EnginePool = original; os.environ.pop('NODE_OPTIONS',None)
            assert not router.counts
        report = read(out/'evaluation.json')
        report.update(correction_arm=args.arm,correction_parent_sha256=parent.sha256)
        write(out/'evaluation.json',report)
        assert report['truncated']==0
        status.update(status='complete',games=report['games'],disagreement_roots=router.root_count,game_truncations=0)
        status['artifacts'] = {p.name:digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'ablation-check.json',status)
        summary = verify_local(out,args.key,args.players,args.arm,args.start,args.end,reencode=True)
        write(out/'summary.json',summary)
    except BaseException as error:
        status.update(status='failed',error=type(error).__name__+': '+str(error)); raise
    finally:
        status['artifacts'] = {p.name:digest(p) for p in out.iterdir() if p.is_file() and p.name!='ablation-check.json'}
        write(out/'ablation-check.json',status)
        if args.upload:
            assert status['source_revision'] and status['source_sha256']
            HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,
                path_in_repo=f'runs/strategic-correction-ablation-v1-{args.key}-{args.players}p-{args.arm}-{args.start}-{args.end}')
        print(status,flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('key'); parser.add_argument('players',type=int); parser.add_argument('arm')
    parser.add_argument('start',type=int); parser.add_argument('end',type=int); parser.add_argument('output',type=Path)
    parser.add_argument('--upload',action='store_true')
    run(parser.parse_args())
