"""Bucket-retained external supervisor, derived from the frozen v2 capture core.

Only the transport receipt contract and checkpoint version change. Complete
pair capture, source/context binding, child ownership and failure handling retain
the v2 semantics. No job dispatch or qualification API.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import time

from checkpoint_bucket_archives_v3 import checked_receipt


class IncompleteWrite(Exception):
    pass


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def signature(path):
    value = Path(path).lstat()
    require(stat.S_ISREG(value.st_mode), 'Expected a regular file, never a symlink')
    return value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def copy_stable(source, target):
    """Stream a regular file and detect concurrent replacement/append/write."""
    before = signature(source); result = hashlib.sha256(); lines = 0; last = b''
    with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as src, Path(target).open('xb') as dst:
        opened = os.fstat(src.fileno())
        if (opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != before:
            raise IncompleteWrite('File changed before opening')
        for block in iter(lambda: src.read(1024*1024), b''):
            dst.write(block); result.update(block); lines += block.count(b'\n'); last = block[-1:]
        dst.flush(); os.fsync(dst.fileno())
    return {'sha256': result.hexdigest(), 'lines': lines, 'newline_terminated': last == b'\n',
        'signature': before, 'stable': signature(source) == before}


def capture_pair(evaluation, episode, destination, row):
    """Return a consistent complete pair, or None for a write still in progress.

Terminal caps/failures are preserved, never filtered by outcome. A consistent
pair is retention evidence only, not an independent game/decision audit.
"""
    try:
        return _capture_pair(evaluation, episode, destination, row)
    except (IncompleteWrite, FileNotFoundError):
        return None


def _capture_pair(evaluation, episode, destination, row):
    game = evaluation/f'game-{episode}.json'; decisions = evaluation/f'decisions-{episode}.jsonl'
    if not game.exists() or not decisions.exists():
        return None
    copied_game = destination/game.name; copied_decisions = destination/decisions.name
    game_meta = copy_stable(game, copied_game)
    if not game_meta['stable']:
        return None
    try:
        record = json.loads(copied_game.read_text())
    except json.JSONDecodeError:
        return None
    require(type(record) is dict and record.get('episode') == episode, 'Wrong completed episode')
    require(record.get('public_runtime_identity') == row['identity'], 'Different frozen policy')
    terminal = record.get('terminal', {}); n = row['players']; expected = row['shard']
    require(type(terminal) is dict and terminal.get('episode') == episode
        and terminal.get('playerCount') == n, 'Wrong terminal identity')
    require(terminal.get('gameSeed') == expected['seed']+'-'+str(episode//(4*n)), 'Different frozen deal')
    require(terminal.get('seat') == episode//4 % n
        and terminal.get('variant') == ('recharged' if episode % 2 else 'original')
        and terminal.get('sealed') is (episode % 4 < 2), 'Different seat/rule pairing')
    decision_meta = copy_stable(decisions, copied_decisions)
    if not decision_meta['stable'] or signature(game) != game_meta['signature']:
        return None
    require(type(record.get('decisions')) is int and record['decisions'] >= 0, 'Invalid decision count')
    if decision_meta['sha256'] != record.get('decision_receipt_sha256'):
        return None
    require(decision_meta['lines'] == record['decisions']
        and (record['decisions'] == 0 or decision_meta['newline_terminated']), 'Incomplete bound decision lines')
    return {'episode': episode, 'hashes': {game.name: game_meta['sha256'], decisions.name: decision_meta['sha256']},
        'signatures': {game.name: game_meta['signature'], decisions.name: decision_meta['signature']}}


class Checkpoints:
    def __init__(self, output, context, uploader):
        require(set(context) == {'attempt_id', 'decision_sha256', 'source_descriptor_sha256',
            'original_row_sha256', 'original_row'}, 'Unexpected context fields')
        require(re.fullmatch('[a-z0-9][a-z0-9-]{1,62}', context['attempt_id']) is not None, 'Unsafe attempt name')
        for key in ('decision_sha256', 'source_descriptor_sha256', 'original_row_sha256'):
            require(re.fullmatch('[a-f0-9]{64}', context[key]) is not None, 'Missing immutable context pin')
        self.context = json.loads(json.dumps(context)); self.row = self.context['original_row']
        encoded = json.dumps(self.row, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        require(hashlib.sha256(encoded).hexdigest() == context['original_row_sha256'], 'Original row differs')
        n = self.row['players']; shard = self.row['shard']
        require(type(n) is int and n in range(2, 7) and shard['players'] == n, 'Invalid player count')
        require(shard['seed'] == f'current-auction-confirmation-v1-{n}p', 'Only original confirmation seeds')
        require(type(shard['start']) is int and type(shard['deals']) is int
            and 0 <= shard['start'] < shard['start']+shard['deals'] <= 32, 'Invalid original range')
        self.episodes = set(range(shard['start']*4*n, (shard['start']+shard['deals'])*4*n))
        require(len(self.episodes) == shard['games'], 'Original count differs')
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=False)
        self.uploader = uploader; self.retained = {}; self.receipts = []; self.serial = 0
        self.failed = False
        save(self.output/'context.json', self.context)

    def capture(self, evaluation, *, full_recheck=False):
        require(not self.failed, 'Previous failure/unknown upload requires inspection; never retry')
        evaluation = Path(evaluation)
        if not evaluation.exists():
            return None
        require(evaluation.is_dir() and not evaluation.is_symlink(), 'Unsafe evaluator directory')
        try:
            # Retained files must remain immutable. Ordinary polls use file metadata;
            # final collection rehashes every retained pair without re-uploading it.
            for episode, kept in self.retained.items():
                for name, sha in kept['hashes'].items():
                    path = evaluation/name
                    require(signature(path) == tuple(kept['signatures'][name]), 'Previously retained file changed')
                    if full_recheck: require(digest(path) == sha, 'Previously retained bytes changed')
            found = set()
            for path in evaluation.glob('game-*.json'):
                match = re.fullmatch('game-([0-9]+)\\.json', path.name)
                require(match is not None, 'Noncanonical game filename')
                episode = int(match[1]); require(path.name == f'game-{episode}.json', 'Noncanonical episode')
                require(episode in self.episodes and episode not in found, 'Unexpected/duplicate original episode')
                found.add(episode)
            new = sorted(found-self.retained.keys())
            if not new: return None
            self.serial += 1
            name = f"{self.context['attempt_id']}-checkpoint-{self.serial:04d}"
            staging = self.output/(name+'.staging'); staging.mkdir()
            captured = []
            for episode in new:
                temporary = staging/f'pair-{episode}'; temporary.mkdir()
                pair = capture_pair(evaluation, episode, temporary, self.row)
                if pair is not None:
                    for child in temporary.iterdir(): child.rename(staging/child.name)
                    captured.append(pair)
                shutil.rmtree(temporary)
            if not captured:
                staging.rmdir(); return None
            save(staging/'checkpoint.json', {'version': 3, 'context': self.context,
                'episodes': [p['episode'] for p in captured],
                'pair_hashes': {str(p['episode']): p['hashes'] for p in captured},
                'scope': 'consistent completed pairs only; independent game audit still required',
                'raw_audited': False, 'execution_complete': False, 'qualified': False})
            save(staging/'manifest.json', {p.name: digest(p) for p in sorted(staging.iterdir())})
            sealed = self.output/name; staging.rename(sealed)
            intent = self.output/(name+'.upload-intent.json')
            save(intent, {'manifest_sha256': digest(sealed/'manifest.json'), 'automatic_retries': False})
            evidence = self.uploader(sealed)
            checked_receipt(evidence, name)
            require(evidence['manifest_sha256'] == digest(sealed/'manifest.json'), 'Uploaded checkpoint differs')
            receipt = {'context_sha256': digest(self.output/'context.json'), 'evidence': evidence,
                'episodes': [p['episode'] for p in captured], 'raw_audited': False, 'qualified': False}
            save(self.output/(name+'.receipt.json'), receipt)
            for pair in captured: self.retained[pair['episode']] = pair
            self.receipts.append(receipt)
            return receipt
        except BaseException:
            self.failed = True
            raise


def stop_group(process):
    """Only the new session created for this child belongs to the supervisor."""
    if process.poll() is not None:
        return
    try: os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        process.wait(timeout=5)


def supervise(command, evaluation, output, context, uploader, period_seconds=30):
    """Wrap a caller-admitted command. No CLI, source preparation, or HF job API."""
    require(isinstance(command, list) and command and all(isinstance(x, str) for x in command), 'Expected argument vector')
    require(type(period_seconds) in (int, float) and 0 < period_seconds <= 60, 'Invalid checkpoint period')
    keeper = Checkpoints(output, context, uploader); process = None
    state = {'stage': 'starting', 'attempt_id': context['attempt_id'], 'qualified': False, 'automatic_retries': False}
    try:
        with (keeper.output/'child.log').open('xb') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            save(keeper.output/'child-started.json', {**state, 'stage': 'running', 'pid': process.pid})
            while process.poll() is None:
                keeper.capture(evaluation)
                try: process.wait(timeout=period_seconds)
                except subprocess.TimeoutExpired: pass
            keeper.capture(evaluation, full_recheck=True)
            state.update(stage='child_exited', child_returncode=process.returncode,
                retained_episodes=sorted(keeper.retained), checkpoints=len(keeper.receipts),
                expected_episodes=len(keeper.episodes), raw_audited=False)
            return state
    except BaseException as error:
        state.update(stage='stopped_for_inspection', failure_type=type(error).__name__)
        raise
    finally:
        if process is not None: stop_group(process)
        save(keeper.output/'supervisor-result.json', state)
