"""Independent audit of the immutable Germany neural screen (no training).

Run: ai/.venv/bin/python -B ai/multimap/audit_neural.py
Only WorkerRuntime/play_game are reused, and only for twelve deterministic
replays. Plan construction, validation, summaries, hashes and statistics below
are independent of neural_study's plan/validate_record/summarize helpers.
No observations, trajectories, requests, or new evaluation seeds are persisted.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import statistics
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = 'multimap-neural-screen-20261102-v1'
JOB = '6ae8ec0f0e0338d1bb7e8dad'
REPO = 'coyotte508/powergrid-ai-multimap-v1'
REVISION = '9362440850a7a523a0a7b90814bc3a7b8b224702'
SOURCE = '4ca026e34b7ba9743cfa4d4811277a8ac31258ba'
RECEIPT_COMMIT = '50e11bcf649b481c5dfbc14fbd92c96dac3607a9'
NAMESPACE = 'pg-multimap-neural-screen-20261102-v1'
POLICIES = ('ppo0', 'ppo1', 'ppo2', 'ensemble', 'teacher', 'reference')
LIMIT = 128 * 1024**2
ARTIFACT_NAMES = {'artifacts.json', 'environment.json', 'recovery.json', 'status.json',
                  'study/plan.json', 'study/games.jsonl', 'study/summary.json'}
SOURCE_NAMES = {f'ai/multimap/{n}' for n in (
    'neural_study.py', 'neural-study-v1.json', 'job_neural.py', 'candidate-pool-v1.json',
    'candidates.py', 'reference_evaluate.py', 'reference_recover.py', 'reference_game.cjs',
    'game_rl.cjs', 'game.cjs', 'features.cjs', 'teacher.cjs', 'model.py', 'residual.py',
    'data.py', 'protocol.json', 'ppo-protocol-v1.json', 'requirements-cpu.txt')}
SOURCE_NAMES |= {'ai/requirements-serve.txt', 'engine/package.json', 'engine/pnpm-lock.yaml'}
TERMINAL_FIELDS = ('allSeatCredit', 'steps', 'rounds', 'counts', 'decisions', 'hiddenChecks')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_source_difference(name, archived_sha, local_sha):
    if archived_sha == local_sha:
        return None
    # These three files do not execute in replay/serving. The frozen archive is
    # still checked byte-for-byte against its Git revision, including these files.
    allowed = {'ai/multimap/runs.json', 'ai/multimap/README.md', 'ai/multimap/launch.py'}
    require(name in allowed and name not in SOURCE_NAMES, 'Local serving/source drift: ' + name)
    return dict(sourceSha256=archived_sha, localSha256=local_sha,
                note='Explicit nonserving bookkeeping/docs/launcher change; archived Git source verified separately.')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def object_sha(value):
    return sha(canonical(value).encode())


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def git_bytes(name, revision=SOURCE):
    return subprocess.check_output(['git', 'show', f'{revision}:{name}'], cwd=ROOT)


def equal(actual, expected, label):
    """Strict structures/types, with tolerance only for floating arithmetic."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label + ': keys')
        for key in expected:
            equal(actual[key], expected[key], label + '.' + str(key))
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label + ': length')
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, label + f'[{i}]')
    elif type(expected) in (int, float) and type(actual) in (int, float):
        require(math.isfinite(actual) and math.isfinite(expected) and
                math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label + ': number')
    else:
        require(type(actual) is type(expected) and actual == expected, label + ': value')


def safe_name(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name and not p.is_absolute() and
            '..' not in p.parts and '\\' not in name and p.as_posix() == name, 'Unsafe path')
    return p


def expected_plan():
    """Hard-coded design, not a traversal of the uploaded plan/protocol."""
    tasks = []
    for n in range(2, 7):
        for variant in ('original', 'recharged'):
            for fast in (False, True):
                cell = f'Germany|{n}|{variant}|{int(fast)}'
                for deal in range(4):
                    for seat in range(n):
                        for policy in POLICIES:
                            tasks.append(dict(policy=policy, spec=dict(map='Germany', players=n,
                                variant=variant, fastBid=fast, cell=cell, deal=deal,
                                seed=f'{NAMESPACE}:{cell}:{deal}', focalSeat=seat, maxSteps=4000,
                                focalPolicy='selected' if policy in POLICIES[:4] else policy)))
    return tasks


def key(record):
    return record['spec']['seed'], record['spec']['focalSeat'], record['policy']


def finite(value, low=0, high=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_outcome(record, task, identity_sha):
    fields = {'schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', 'seconds', *TERMINAL_FIELDS}
    require(set(record) == fields, 'Outcome schema/extra field/error')
    require(record['schema'] == 'multimap-neural-outcome-v1' and
            record['identitySha256'] == identity_sha, 'Outcome identity')
    require(canonical(record['spec']) == canonical(task['spec']) and record['policy'] == task['policy'], 'Task spec')
    require(record['terminal'] is True, 'Failed/nonterminal outcome')
    require(finite(record['seconds']), 'Invalid timing')
    spec = task['spec']
    credits = record['allSeatCredit']
    require(isinstance(credits, list) and len(credits) == spec['players'] and
            all(finite(c, 0, 1) for c in credits), 'Credit vector dimensions/range')
    winners = sum(c > 0 for c in credits)
    # Merely checking sum=1 would admit impossible vectors such as [.2,.8].
    require(winners > 0 and all(c == 0 or c == 1 / winners for c in credits), 'Credit not equal 0 or 1/k')
    require(math.fsum(credits) == 1 and finite(record['credit'], 0, 1) and
            record['credit'] == credits[spec['focalSeat']], 'Focal/total credit')
    require(type(record['steps']) is int and 0 < record['steps'] <= spec['maxSteps'], 'Step cap')
    require(type(record['rounds']) is int and 0 < record['rounds'] <= record['steps'], 'Rounds')
    require(isinstance(record['decisions'], dict) and set(record['decisions']) == {'ppo', 'reference'}, 'Decision actors')
    require(all(type(v) is int and 0 <= v <= record['steps'] for v in record['decisions'].values()), 'Decision counts')
    counts = record['counts']
    require(isinstance(counts, dict) and set(counts) == {'ppo', 'reference', 'fixed'}, 'Phase actors')
    for phases in counts.values():
        require(isinstance(phases, dict) and set(phases) <= {'Auction', 'Building', 'Resources', 'Bureaucracy'} and
                all(type(v) is int and v > 0 for v in phases.values()), 'Phase count')
    require(sum(sum(phases.values()) for phases in counts.values()) == record['steps'], 'Phase total')
    for actor, count in record['decisions'].items():
        require(sum(counts[actor].values()) == count, 'Service/phase counts disagree')
    require(type(record['hiddenChecks']) is int and record['hiddenChecks'] == record['decisions']['reference'], 'Hidden checks')
    require(set(counts['ppo']) <= {'Auction', 'Building'}, 'PPO routed outside learned phases')
    # Forced single-legal moves are fixed even in Auction/Building; compact
    # counts cannot distinguish them from a hypothetical routing bug.
    if task['policy'] not in POLICIES[:4]:
        require(record['decisions']['ppo'] == 0 and counts['ppo'] == {}, 'Control routed to PPO')
    if task['policy'] == 'reference':
        require(counts['fixed'] == {} and record['decisions']['reference'] == record['steps'], 'Incomplete reference control')


def verify_outcomes(records, tasks, identity_sha):
    expected = {key(t): t for t in tasks}
    require(len(expected) == len(tasks), 'Duplicate planned task')
    actual = {}
    for record in records:
        k = key(record)
        require(k in expected and k not in actual, 'Duplicate/unplanned outcome')
        validate_outcome(record, expected[k], identity_sha)
        actual[k] = record
    require(actual.keys() == expected.keys(), 'Missing outcome/seat/policy/deal')
    controls = defaultdict(list)
    for r in records:
        if r['policy'] == 'reference':
            controls[r['spec']['seed']].append(r)
    baseline = []
    for seed, items in sorted(controls.items()):
        items.sort(key=lambda r: r['spec']['focalSeat'])
        require({r['spec']['focalSeat'] for r in items} == set(range(items[0]['spec']['players'])), 'Reference seats')
        for field in TERMINAL_FIELDS:
            require(all(r[field] == items[0][field] for r in items), 'Reference rotations disagree: ' + field)
        rational = [Fraction(1, sum(c > 0 for c in r['allSeatCredit'])) if r['credit'] else Fraction(0) for r in items]
        require(sum(rational) == 1 and math.fsum(r['credit'] for r in items) == 1, 'Reference focal credits must sum exactly one')
        baseline.append(dict(seed=seed, games=len(items), terminal=True, focalCreditSum=1.0,
                             sameCreditVector=True, passed=True))
    return actual, baseline


def read_outcomes(path):
    require(Path(path).stat().st_size <= LIMIT, 'Oversized outcomes')
    records = []
    with Path(path).open('rb') as stream:
        for line in stream:
            require(line.endswith(b'\n') and len(line) <= 64 * 1024, 'Truncated/oversized JSONL line')
            value = json.loads(line)
            require(line == (canonical(value) + '\n').encode(), 'Noncompact/noncanonical outcome JSONL')
            records.append(value)
    return records


def deal_table(records):
    rows = defaultdict(dict)
    for r in records:
        s = r['spec']
        k = (s['cell'], s['deal'], r['policy'])
        require(s['focalSeat'] not in rows[k], 'Duplicate paired seat')
        rows[k][s['focalSeat']] = r['credit']
    cells = sorted({k[0] for k in rows})
    require(set(rows) == {(c, d, p) for c in cells for d in range(4) for p in POLICIES}, 'Missing paired deal/policy')
    result = {}
    for (cell, deal, policy), seats in rows.items():
        n = int(cell.split('|')[1])
        require(set(seats) == set(range(n)), 'Missing paired seat')
        result[cell, deal, policy] = math.fsum(seats.values()) / n
    return cells, result


def stratified_estimate(strata):
    """Equal-stratum mean and unbiased variance of its paired-deal estimator.

    Each list is one fixed cell, with four independent deals. For H cells:
    Var(mean) = sum_h [s_h^2 / n_h] / H^2, s_h^2 uses n_h-1.
    Seats and policies stay paired *inside* each independent deal.
    """
    require(bool(strata) and all(len(xs) >= 2 and all(finite(x, -1, 1) for x in xs) for xs in strata), 'Invalid strata')
    point = statistics.fmean(statistics.fmean(xs) for xs in strata)
    se = math.sqrt(math.fsum(statistics.variance(xs) / len(xs) for xs in strata)) / len(strata)
    return dict(mean=point, unbiasedStratifiedPairedSE=se,
                approximateNormal95=[point - 1.96 * se, point + 1.96 * se])


def paired_statistics(records):
    cells, table = deal_table(records)
    groups = {'all': cells}
    for n in range(2, 7):
        groups[f'players:{n}'] = [c for c in cells if c.split('|')[1] == str(n)]
    for v in ('original', 'recharged'):
        groups['variant:' + v] = [c for c in cells if c.split('|')[2] == v]
    for f, name in ((0, 'open'), (1, 'sealed')):
        groups['auction:' + name] = [c for c in cells if c.split('|')[3] == str(f)]
    groups.update({'cell:' + c: [c] for c in cells})
    report = {}
    for label, group in groups.items():
        if not group:
            continue
        policies = {}
        for p in POLICIES:
            means = [[table[c, d, p] for d in range(4)] for c in group]
            contrasts = {}
            for control in ('reference', 'teacher'):
                xs = [[table[c, d, p] - table[c, d, control] for d in range(4)] for c in group]
                estimate = stratified_estimate(xs)
                estimate['difference'] = estimate.pop('mean')
                contrasts[control] = estimate
            selected = [r for r in records if r['policy'] == p and r['spec']['cell'] in group]
            policies[p] = dict(macroCellCredit=statistics.fmean(map(statistics.fmean, means)),
                gameMeanCredit=statistics.fmean(r['credit'] for r in selected),
                creditSum=math.fsum(r['credit'] for r in selected), games=len(selected),
                pairedDealDifferences=contrasts)
        report[label] = dict(strata=len(group), independentDeals=4 * len(group),
            seatsPerPolicy=sum(4 * int(c.split('|')[1]) for c in group), policies=policies)
    return report


def legacy_mean_se(values):
    return dict(mean=statistics.fmean(values), independentDeals=len(values),
                dealStandardError=statistics.stdev(values) / math.sqrt(len(values)))


def verify_summary(stored, records, baseline, identity_sha):
    """Verify original summary values, including its *unstratified* legacy SE.

    The new report uses fixed-cell stratified SE instead; source-summary SEs
    mix between-cell heterogeneity into variance and are not copied as inference.
    """
    cells, table = deal_table(records)
    cell_rows, policies = [], {}
    for c in cells:
        n = int(c.split('|')[1])
        for p in POLICIES:
            items = [r for r in records if r['policy'] == p and r['spec']['cell'] == c]
            cell_rows.append(dict(cell=c, policy=p, plannedGames=4*n, games=4*n, terminalGames=4*n,
                failures=0, creditSum=math.fsum(r['credit'] for r in items),
                gameMeanCredit=statistics.fmean(r['credit'] for r in items), plannedIndependentDeals=4,
                **legacy_mean_se([table[c, d, p] for d in range(4)])))
    for p in POLICIES:
        items = [r for r in records if r['policy'] == p]
        contrasts = {control: legacy_mean_se([table[c, d, p] - table[c, d, control]
                     for c in cells for d in range(4)]) for control in ('reference', 'teacher')}
        policies[p] = dict(games=320, plannedGames=320, failures=0,
            creditSum=math.fsum(r['credit'] for r in items), gameMeanCredit=statistics.fmean(r['credit'] for r in items),
            completeCells=20, macroCellCredit=statistics.fmean(table[c, d, p] for c in cells for d in range(4)),
            pairedDealDifferences=contrasts)
    expected = dict(schema='multimap-neural-summary-v1', games=1920, plannedGames=1920, complete=True,
        failures=0, cells=cell_rows, policies=policies, independentDeals=80, plannedIndependentDeals=80,
        allReferenceControl=baseline, baselineViolations=[], qualificationStopped=False, qualified=False,
        qualification_eligible=False, reserved_final_seeds_used=False, fitted=False, selected=False,
        identitySha256=identity_sha)
    require(set(stored) == set(expected) | {'note'} and isinstance(stored['note'], str), 'Summary fields')
    equal({k: stored[k] for k in expected}, expected, 'Independently reconstructed summary')


class RemoteFiles:
    """Metadata first, bounded individual files only; never snapshot_download."""
    def __init__(self, api):
        self.api = api
        self.accounted = set()
        self.bounded_bytes = 0
        self.evidence = []

    def describe(self, pin):
        from huggingface_hub import get_hf_file_metadata, hf_hub_url
        kind = pin.get('repo_type', 'model')
        info = self.api.repo_info(pin['repo'], repo_type=kind, revision=pin['revision'])
        require(info.private and info.sha == pin['revision'], 'Repository privacy/revision')
        entries = self.api.get_paths_info(pin['repo'], [pin['path']], repo_type=kind, revision=pin['revision'])
        require(len(entries) == 1, 'Missing remote path')
        entry = entries[0]
        meta = get_hf_file_metadata(hf_hub_url(pin['repo'], pin['path'], repo_type=kind, revision=pin['revision']))
        require(meta.commit_hash == pin['revision'] and type(meta.size) is int and meta.size > 0 and
                meta.size == entry.size, 'Metadata revision/size')
        if entry.lfs:
            equal(meta.etag, entry.lfs.sha256, 'LFS etag')
            equal(entry.lfs.size, entry.size, 'LFS size')
            equal(pin.get('sha256', entry.lfs.sha256), entry.lfs.sha256, 'Pinned LFS SHA')
            pointer = f'version https://git-lfs.github.com/spec/v1\noid sha256:{entry.lfs.sha256}\nsize {entry.size}\n'.encode()
            equal(git_blob(pointer), entry.blob_id, 'LFS pointer Git blob')
        else:
            equal(meta.etag, entry.blob_id, 'Git blob etag')
        return entry

    def get(self, pin, metadata=None, cached=None):
        from huggingface_hub import hf_hub_download
        entry = metadata if metadata is not None else self.describe(pin)
        identifier = (pin['repo'], pin['revision'], pin['path'])
        if identifier not in self.accounted:
            require(entry.size + self.bounded_bytes <= LIMIT, '128 MiB cumulative compact/source/model download budget')
            self.bounded_bytes += entry.size
            self.accounted.add(identifier)
        path = Path(cached) if cached else Path(hf_hub_download(pin['repo'], pin['path'],
            repo_type=pin.get('repo_type', 'model'), revision=pin['revision']))
        require(path.is_file() and path.stat().st_size == entry.size, 'Cached/downloaded size')
        checksum = digest(path)
        equal(checksum, pin.get('sha256', checksum), 'Artifact SHA256')
        if entry.lfs:
            equal(checksum, entry.lfs.sha256, 'LFS content SHA256')
        else:
            equal(git_blob(path.read_bytes()), entry.blob_id, 'Git content blob')
        self.evidence.append(dict(repo=pin['repo'], revision=pin['revision'], path=pin['path'],
            bytes=entry.size, sha256=checksum, gitBlob=entry.blob_id,
            lfsSha256=entry.lfs.sha256 if entry.lfs else None))
        return path


def verify_source(archive, plan):
    with tarfile.open(archive, 'r:gz') as tf:
        members = tf.getmembers()
        require(len({m.name for m in members}) == len(members), 'Duplicate archive name')
        require(sum(m.size for m in members) <= LIMIT, 'Source expanded byte budget')
        for m in members:
            safe_name(m.name)
            require(m.isfile() or m.isdir(), 'Nonregular source archive entry')
        manifest_raw = tf.extractfile('source-manifest.json').read()
        manifest = json.loads(manifest_raw)
        equal(manifest['gitCommit'], SOURCE, 'Packaged Git commit')
        files = manifest['files']
        require({m.name for m in members if m.isfile()} == set(files) | {'source-manifest.json'}, 'Full source manifest coverage')
        for name, checksum in files.items():
            with tf.extractfile(name) as stream:
                equal(hashlib.file_digest(stream, 'sha256').hexdigest(), checksum, 'Source member: ' + name)
    tracked = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', SOURCE], cwd=ROOT, text=True).splitlines())
    node = Path(subprocess.check_output(['node', '-p', 'process.execPath'], cwd=ROOT, text=True).strip())
    dependency_roots = {n: Path(subprocess.check_output(['node', '-p',
        f"require.resolve('{n}/package.json',{{paths:['./engine']}})"], cwd=ROOT, text=True).strip()).parent
        for n in ('lodash', 'seedrandom', 'delaunator')}
    git_count = 0
    receipt_differences = {}
    groups = defaultdict(dict)
    for name, checksum in files.items():
        if name in tracked:
            equal(sha(git_bytes(name)), checksum, 'Git source: ' + name)
            git_count += 1
        else:
            require(name.startswith(('engine/dist/', 'engine/node_modules/')) or name == 'runtime/node', 'Untracked source member: ' + name)
        local = ROOT / name
        if name == 'runtime/node':
            local = node
        elif name.startswith('engine/node_modules/'):
            dep, *rest = name.split('/')[2:]
            require(dep in dependency_roots, 'Unknown packaged Node dependency')
            local = dependency_roots[dep].joinpath(*rest)
        require(local.is_file(), 'Missing local source: ' + name)
        local_sha = digest(local)
        difference = local_source_difference(name, checksum, local_sha)
        if difference:
            receipt_differences[name] = difference
        fold = ('engine/dist' if name.startswith('engine/dist/') else
                'engine/node_modules' if name.startswith('engine/node_modules/') else
                'engine/src' if name.startswith('engine/src/') else name.split('/')[0])
        groups[fold][name] = checksum
    # Check both content and complete source sets, not only provided subsets.
    packaged_tracked = {n for n in tracked if n.startswith(('ai/multimap/', 'engine/src/')) or n in
        {'ai/core.cjs', 'ai/strong/economics.cjs', 'ai/requirements-serve.txt', 'engine/index.ts', 'engine/package.json', 'engine/pnpm-lock.yaml'}}
    require(packaged_tracked == set(files) & tracked, 'Missing tracked source in archive')
    local_dist = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'engine/dist').rglob('*') if p.is_file()}
    require(local_dist == {n for n in files if n.startswith('engine/dist/')}, 'Engine dist file set drift')
    equal(set(plan['sourceFiles']), SOURCE_NAMES, 'Full plan source identity coverage')
    for name, checksum in plan['sourceFiles'].items():
        equal(files[name], checksum, 'Plan source identity: ' + name)
    generator = {n: s for n, s in files.items() if n in {'ai/core.cjs', 'ai/strong/economics.cjs',
        'ai/multimap/features.cjs', 'ai/multimap/game.cjs', 'ai/multimap/teacher.cjs', 'ai/multimap/protocol.json'} or
        (n.startswith('engine/dist/') and n.endswith('.js'))}
    equal(sha(json.dumps(generator, sort_keys=True).encode()), plan['generatorDigest'], 'Independent generator source fold')
    equal(manifest['node'], plan['runtimeVersions']['node'], 'Packaged Node version')
    return dict(sourceManifestSha256=sha(manifest_raw), sourceManifestCanonicalSha256=object_sha(manifest),
        manifestFiles=len(files),
        gitFilesVerified=git_count, localFilesCompared=len(files), localFilesByteIdentical=len(files)-len(receipt_differences),
        nonServingLocalDifferences=receipt_differences, planSourceFiles=plan['sourceFiles'],
        generatorDigest=plan['generatorDigest'], generatorFiles=len(generator),
        folds={n: dict(files=len(v), sha256=object_sha(v)) for n, v in sorted(groups.items())},
        note='All archive members hash-checked without extracting. Tracked files checked against frozen Git; '
             'all packaged bytes compared locally, permitting only explicitly listed nonserving runs.json/README/launch.py differences. '
             'Serving bytes are unchanged, including generated engine, Node and three bundled dependencies.')


def verify_reference(protocol, recovery, remote):
    artifact = ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact'
    ref = protocol['reference']
    equal(digest(artifact / 'manifest.json'), ref['runtimeManifestSha256'], 'Reference manifest pin')
    equal(digest(artifact / 'policy.json'), ref['policySha256'], 'Reference descriptor pin')
    manifest = json.loads((artifact / 'manifest.json').read_text())
    actual = set()
    for p in artifact.rglob('*'):
        require(not p.is_symlink(), 'Reference artifact symlink')
        if p.is_file():
            actual.add(p.relative_to(artifact).as_posix())
    require(actual == set(manifest) | {'manifest.json', 'policy.json'}, 'Complete unchanged reference artifact')
    for name, checksum in manifest.items():
        safe_name(name)
        equal(digest(artifact / name), checksum, 'Reference member: ' + name)
    descriptor = json.loads((artifact / 'policy.json').read_text())
    equal(descriptor, dict(backend=ref['backend'], feature_revision=ref['featureRevision'],
        model=dict(path='policy.onnx', sha256=ref['modelSha256']),
        runtime_manifest=dict(path='manifest.json', sha256=ref['runtimeManifestSha256']), settings=ref['settings'], version=1), 'Exact FILTER descriptor/settings')
    equal(manifest['policy.onnx'], ref['modelSha256'], 'Reference ONNX manifest')
    for k in ('runtimeManifestSha256', 'policySha256'):
        equal(recovery[k], ref[k], 'Recovery ' + k)
    equal(recovery['pins']['source'], ref['sourcePin'], 'Recovery source pin')
    equal(recovery['pins']['model'], ref['modelPin'], 'Recovery model pin')
    remote_identity = {}
    for k in ('source', 'model', 'ppo'):
        entry = remote.describe(recovery['pins'][k])
        remote_identity[k] = dict(bytes=entry.size, gitBlob=entry.blob_id,
            lfsSha256=entry.lfs.sha256 if entry.lfs else None,
            contentVerification='Complete recovered artifact hashes' if k != 'source' else 'Metadata and prior receipt only; archive not redownloaded')
        equal(recovery['remote'][k], dict(bytes=entry.size, revision=recovery['pins'][k]['revision']), 'Recovery metadata ' + k)
        if k != 'source':
            p = artifact / 'policy.onnx' if k == 'model' else artifact.parent / 'ppo.pt'
            equal(digest(p), recovery['pins'][k]['sha256'], 'Recovered content ' + k)
            equal(p.stat().st_size, entry.size, 'Recovered bytes ' + k)
    require(recovery['exactServiceReady'] is True and recovery['blocker'] is None and recovery['omitted'] == [] and
            recovery['reserved_final_seeds_used'] is False, 'Incomplete/unsafe reference recovery')
    equal(recovery['locallyVerifiedFiles'], len(manifest), 'Recovered files')
    equal(recovery['verifiedArchiveManifestFiles'], len(manifest), 'Archived manifest count')
    artifact_bytes = sum((artifact / n).stat().st_size for n in actual)
    equal(recovery['fullArtifactBytes'], artifact_bytes, 'Complete artifact bytes')
    equal(recovery['diskBudgetBytes'], protocol['referenceCacheMaxBytes'], 'Reference disk budget')
    equal(recovery['compressedArchiveRamCapBytes'], protocol['compressedArchiveRamMaxBytes'], 'Reference RAM budget')
    require(recovery['cacheBytes'] <= protocol['referenceCacheMaxBytes'] and
            recovery['compressedArchiveRamBytes'] == recovery['remote']['source']['bytes'] <= protocol['compressedArchiveRamMaxBytes'], 'Reference resource limits')
    cache_bytes = sum(p.stat().st_size for p in artifact.parent.rglob('*') if p.is_file())
    require(cache_bytes <= protocol['referenceCacheMaxBytes'], 'Local reference cache limit')
    return dict(manifestFiles=len(manifest), artifactBytes=artifact_bytes, localCacheBytes=cache_bytes,
        runtimeManifestSha256=ref['runtimeManifestSha256'], policySha256=ref['policySha256'], modelSha256=ref['modelSha256'],
        settings=descriptor['settings'], recoveredArtifactAllHashesVerified=True,
        archivedSourceVerification='Old 130442976-byte compressed archive was NOT redownloaded; immutable HF metadata/LFS pointer '
            'and prior recovery receipt checked. All 1467 recovered manifest members independently rehashed locally; no loader bypass.',
        pins=recovery['pins'], immutableRemoteMetadata=remote_identity)


def verify_environment(protocol, environment, plan):
    equal(environment['versions'], plan['runtimeVersions'], 'Plan/environment identity')
    equal(environment['requirementsSha256'], protocol['referenceRequirementsSha256'], 'Requirements receipt')
    require(environment['referenceVenvBytes'] <= protocol['referenceVenvMaxBytes'], 'Reference environment size')
    code = ('import json,sys,importlib.metadata as m;print(json.dumps(dict(python=list(sys.version_info[:3]),'
            'packages={d.metadata["Name"]:d.version for d in m.distributions()})))')
    local_ref = json.loads(subprocess.check_output([str(ROOT / 'ai/.venv-reference/bin/python'), '-B', '-c', code], text=True))
    local = dict(reference=dict(python=local_ref['python'], numpy=local_ref['packages']['numpy'],
        onnxruntime=local_ref['packages']['onnxruntime']), candidate=dict(python=list(sys.version_info[:3]),
        **{n: importlib.metadata.version(n) for n in ('torch', 'numpy', 'huggingface-hub')}),
        node=subprocess.check_output(['node', '--version'], text=True).strip())
    for label, versions in (('HF', environment['versions']), ('local', local)):
        rp = versions['reference']
        expected_numpy = protocol['referenceEnvironment']['numpyPython312Plus' if rp['python'][:2] >= [3, 12] else 'numpyPython311']
        equal(rp['numpy'], expected_numpy, label + ' reference NumPy')
        equal(rp['onnxruntime'], protocol['referenceEnvironment']['onnxruntime'], label + ' reference ONNX')
        for name, version in protocol['torchEnvironment'].items():
            equal(versions['candidate'][name], version, label + ' candidate ' + name)
    equal(local, environment['versions'], 'Exact recorded local/HF principal versions')
    return dict(recorded=environment, replayVersions=local, localReferencePackages=local_ref['packages'],
        caveat='Historical requirements-serve pins only NumPy and ONNX Runtime. Transitive dependencies are not fully pinned '
               'and were not recorded by the HF job; matching principal versions is not a claim of a completely reproducible Python environment.')


def verify_candidates(pool, plan, remote):
    import torch
    result = []
    for index, pin in enumerate(pool['members']):
        path = remote.get(pin)
        saved = torch.load(path, map_location='cpu', weights_only=True)
        equal(saved['update'], pin['update'], 'Frozen candidate update')
        require(saved['config']['smoke'] is False, 'Smoke checkpoint')
        equal(saved['config']['generatorDigest'], plan['generatorDigest'], 'Candidate generator')
        config = saved['config']
        historical = 'a3b492b650dec51c34b6f9322d87088b1e863f0e' if index == 0 else SOURCE
        changes = []
        for name, checksum in config['sourceFiles'].items():
            safe_name(name)
            equal(sha(git_bytes('ai/multimap/' + name, historical)), checksum, 'Historical candidate source ' + name)
            if digest(HERE / name) != checksum:
                changes.append(name)
        equal(sorted(changes), ['ppo.py', 'rollout.py'] if index == 0 else [], 'Only historical nonserving training helpers may differ')
        equal(config['protocol']['seedNamespace'], 'pg-multimap-ppo-20261102-v1' + (f':replica-{index}' if index else ''), 'Training namespace')
        require(not NAMESPACE.startswith(config['protocol']['seedNamespace']), 'Screen/training seed namespace overlap')
        result.append(dict(**pin, historicalSourceCommit=historical, historicalSourceFiles=len(config['sourceFiles']),
            unchangedServingFilesVerified=True, nonservingHistoricalDifferences=changes,
            trainingNamespace=config['protocol']['seedNamespace']))
    return result


def replay_tasks(tasks):
    """Outcome-blind coverage design: two games/policy; every count and rule pair."""
    chosen = []
    for i in range(12):
        policy = POLICIES[i % 6]
        n = 2 + i % 5
        variant = ('original', 'recharged')[(i // 2) % 2]
        fast = bool(i % 2)
        choices = [t for t in tasks if t['policy'] == policy and t['spec']['players'] == n and
                   t['spec']['variant'] == variant and t['spec']['fastBid'] == fast]
        chosen.append(min(choices, key=object_sha))
    require(len({key(t) for t in chosen}) == 12, 'Duplicate replay')
    require({t['spec']['players'] for t in chosen} == set(range(2, 7)), 'Replay count coverage')
    require({(t['spec']['variant'], t['spec']['fastBid']) for t in chosen} ==
            {(v, f) for v in ('original', 'recharged') for f in (False, True)}, 'Replay rule coverage')
    require(Counter(t['policy'] for t in chosen) == Counter({p: 2 for p in POLICIES}), 'Replay policy coverage')
    return chosen


def replay(tasks, actual, identity_sha):
    # No other neural_study helper is used by this auditor.
    from neural_study import WorkerRuntime, play_game
    started = time.monotonic()
    runtime = WorkerRuntime(ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact', ROOT / 'ai/.venv-reference/bin/python')
    rows = []
    try:
        for task in replay_tasks(tasks):
            result = play_game(task, runtime.bridge, runtime.reference, runtime.models, identity_sha)
            validate_outcome(result, task, identity_sha)
            original = actual[key(task)]
            for field in ('schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', *TERMINAL_FIELDS):
                require(result[field] == original[field], 'Deterministic replay mismatch: ' + field)
            rows.append(dict(policy=task['policy'], spec=task['spec'], matched=True,
                seconds=result['seconds'], originalSeconds=original['seconds'], steps=result['steps'], rounds=result['rounds'],
                allSeatCredit=result['allSeatCredit'], credit=result['credit']))
            print(canonical(dict(stage='replay', completed=len(rows), policy=task['policy'], seconds=result['seconds'])), flush=True)
    finally:
        runtime.close()
    return dict(games=12, matched=12, seconds=time.monotonic() - started,
        selection='Two games per policy, all five counts and four variant/auction pairs; lexicographically minimum canonical-task SHA256 within each predefined slot, never by outcomes.',
        comparisonFields=['schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', *TERMINAL_FIELDS],
        note='Timing deliberately excluded from equality. Replays verify compact terminal evidence, not a saved action trace; no new deals or training data.', rows=rows)


def timings(records):
    result = {}
    for policy in ('all', *POLICIES):
        rows = records if policy == 'all' else [r for r in records if r['policy'] == policy]
        seconds = [r['seconds'] for r in rows]
        result[policy] = dict(games=len(rows), summedGameSeconds=math.fsum(seconds),
            meanGameSeconds=statistics.fmean(seconds), medianGameSeconds=statistics.median(seconds), maxGameSeconds=max(seconds),
            minSteps=min(r['steps'] for r in rows), maxSteps=max(r['steps'] for r in rows),
            totalSteps=sum(r['steps'] for r in rows), totalRounds=sum(r['rounds'] for r in rows),
            decisions={a: sum(r['decisions'][a] for r in rows) for a in ('ppo', 'reference')},
            hiddenChecks=sum(r['hiddenChecks'] for r in rows),
            phaseCounts={a: dict(sum((Counter(r['counts'][a]) for r in rows), Counter())) for a in ('ppo', 'reference', 'fixed')},
            tiedTerminalGames=sum(sum(c > 0 for c in r['allSeatCredit']) > 1 for r in rows))
    return result


def audit(output):
    from huggingface_hub import HfApi
    started = time.monotonic()
    api = HfApi()
    remote = RemoteFiles(api)
    receipt = json.loads((HERE / 'neural-launch-v1.json').read_text())
    equal(digest(HERE / 'neural-launch-v1.json'), sha(git_bytes('ai/multimap/neural-launch-v1.json', RECEIPT_COMMIT)), 'Pinned launch receipt bytes')
    equal(receipt['run'], RUN, 'Launch run')
    equal(receipt['jobId'], JOB, 'Launch job')
    equal(receipt['sourceCommit'], SOURCE, 'Launch Git source')
    job = api.inspect_job(job_id=JOB)
    require(job.status.stage == 'COMPLETED', 'HF job incomplete')
    equal(job.environment, receipt['env'], 'HF job/source environment')
    equal(job.docker_image, receipt['image'], 'HF Docker image')
    equal(job.flavor, receipt['flavor'], 'HF flavor')
    info = api.model_info(REPO, revision=REVISION, files_metadata=True)
    require(info.private and info.sha == REVISION, 'Wrong/private study repository pin')
    prefix = f'runs/{RUN}/'
    metadata = {s.rfilename[len(prefix):]: s for s in info.siblings if s.rfilename.startswith(prefix)}
    require(set(metadata) == ARTIFACT_NAMES, 'Unexpected/noncompact study artifacts')
    total_bytes = sum(s.size for s in metadata.values())
    require(total_bytes <= LIMIT, 'Study 128 MiB metadata budget')
    manifest_path = remote.get(dict(repo=REPO, revision=REVISION, path=prefix + 'artifacts.json'), metadata['artifacts.json'])
    manifest = json.loads(manifest_path.read_text())
    require(set(manifest) == ARTIFACT_NAMES - {'artifacts.json'}, 'Artifact manifest coverage')
    mapping = json.loads((ROOT / f'ai/runs/{RUN}/audit/files.json').read_text())
    require(set(mapping) == set(manifest), 'Cached compact file mapping')
    files = {name: remote.get(dict(repo=REPO, revision=REVISION, path=prefix + name, sha256=checksum),
             metadata[name], cached=mapping[name]) for name, checksum in manifest.items()}
    plan = json.loads(files['study/plan.json'].read_text())
    protocol = json.loads(git_bytes('ai/multimap/neural-study-v1.json'))
    pool = json.loads(git_bytes('ai/multimap/candidate-pool-v1.json'))
    equal(plan['protocol'], protocol, 'Frozen protocol')
    equal(plan['candidatePool'], pool, 'Entire frozen candidate pool; no best-seed substitution')
    equal(object_sha(pool), protocol['candidatePoolSha256'], 'Candidate pool canonical SHA')
    equal({p['name']: p['update'] for p in pool['members']}, protocol['candidateUpdates'], 'Candidate update pins')
    equal(pool['ensemble']['members'], list(POLICIES[:3]), 'Ensemble members')
    equal(pool['ensemble']['weights'], [1, 1, 1], 'Ensemble equal weights')
    require(set(plan) == {'schema', 'protocol', 'candidatePool', 'generatorDigest', 'sourceFiles', 'tasks', 'smoke', 'runtimeVersions', 'execution'}, 'Full identity fields')
    require(plan['schema'] == 'multimap-neural-plan-v1' and plan['smoke'] is False, 'Non-full plan')
    equal(plan['execution'], dict(workers=6, startMethod='spawn', torchThreads=1), 'Frozen execution')
    tasks = expected_plan()
    require(len(tasks) == 1920, 'Design arithmetic')
    equal(canonical(plan['tasks']), canonical(tasks), 'Independently derived full plan with exact JSON types')
    identity_sha = object_sha(plan)
    records = read_outcomes(files['study/games.jsonl'])
    actual, baseline = verify_outcomes(records, tasks, identity_sha)
    require(len(baseline) == 80, 'All-reference control deal coverage')
    stored = json.loads(files['study/summary.json'].read_text())
    verify_summary(stored, records, baseline, identity_sha)
    groups = paired_statistics(records)
    status = json.loads(files['status.json'].read_text())
    require(status['stage'] == 'complete' and 'error' not in status and 'resume' not in status, 'Status failed/resumed')
    equal(status['result'], stored, 'Status/summary equality')
    equal(status['protocol'], protocol, 'Status protocol')
    for field, expected in dict(run=RUN, smoke=False, workers=6, qualified=False, qualification_eligible=False, reserved_final_seeds_used=False).items():
        equal(status[field], expected, 'Status ' + field)
    for field, env in (('sourceRevision', 'SOURCE_REVISION'), ('sourceSha256', 'SOURCE_SHA256'),
                       ('sourcePath', 'SOURCE_PATH'), ('sourceRepo', 'DATASET_REPO')):
        equal(status[field], receipt['env'][env], 'Status source receipt ' + field)
    equal([x['stage'] for x in status['receipts']], ['runtime-ready', 'planned',
        *[f'games-{n}' for n in range(120, 1921, 120)], 'screen-complete'], 'All progress receipts')
    source_pin = dict(repo=receipt['env']['DATASET_REPO'], repo_type='dataset', revision=receipt['env']['SOURCE_REVISION'],
                      path=receipt['env']['SOURCE_PATH'], sha256=receipt['env']['SOURCE_SHA256'])
    source_report = verify_source(remote.get(source_pin), plan)
    recovery = json.loads(files['recovery.json'].read_text())
    equal(recovery['pins']['ppo'], {k: v for k, v in pool['members'][0].items() if k not in ('name', 'update')} | {'repo_type': 'model'}, 'Recovery main policy pin')
    reference_report = verify_reference(protocol, recovery, remote)
    environment_report = verify_environment(protocol, json.loads(files['environment.json'].read_text()), plan)
    candidate_report = verify_candidates(pool, plan, remote)
    print(canonical(dict(stage='audit-verified', games=len(records), independentDeals=80, artifactBytes=total_bytes)), flush=True)
    replays = replay(tasks, actual, identity_sha)
    log_path = ROOT / f'ai/runs/{RUN}/job.log'
    log = log_path.read_text()
    require('pass 13' in log and 'skipped 1' in log and 'Ran 24 tests' in log and '\nOK\n' in log and REVISION in log, 'HF job test log evidence')
    preflight = json.loads((HERE / 'reference-preflight-v1.json').read_text())
    equal(preflight['syntheticCompatibility']['cases'], 160, 'Separate preflight fixtures')
    equal(preflight['fullGames'], 20, 'Separate preflight games')
    equal(preflight['exactFullGameReplays'], 5, 'Separate preflight replays')
    report = dict(schema='multimap-independent-neural-audit-v1', repo=REPO, revision=REVISION, run=RUN, jobId=JOB,
        sourceCommit=SOURCE, launchReceiptSha256=digest(HERE / 'neural-launch-v1.json'),
        auditorSha256=digest(__file__), testsSha256=digest(HERE / 'test_audit_neural.py'),
        identitySha256=identity_sha, artifactManifestSha256=digest(manifest_path), artifactsVerified=len(manifest),
        artifactBytes=total_bytes, boundedInputBytes=remote.bounded_bytes, inputBudgetBytes=LIMIT,
        verifiedRemoteFiles=remote.evidence, source=source_report, reference=reference_report,
        environment=environment_report, candidates=candidate_report, ensemble=pool['ensemble'],
        coverage=dict(cells=20, dealsPerCell=4, independentDeals=80, seatsPerPolicy=320, policies=list(POLICIES),
            games=1920, terminalGames=1920, failures=0, caps=0, duplicateOutcomes=0, missingOutcomes=0,
            completePlanVerified=True, allCreditVectorsEqualWinnerShares=True, allReferenceDealsVerified=80,
            allReferenceTerminalFieldsIdenticalAcrossSeats=True, allReferenceFocalCreditSumsExactlyOne=True),
        groups=groups, timings=timings(records), errors=[], replays=replays,
        hfJob=dict(stage=job.status.stage, startedAt=str(job.started_at), finishedAt=str(job.finished_at),
            runningSeconds=job.durations.running_secs, totalSeconds=job.durations.total_secs,
            image=job.docker_image, flavor=job.flavor, nodeTestsPassed=13, nodeTestsSkipped=1, pythonTestsPassed=24,
            testLogSha256=digest(log_path), skipReason='Archived-reference compatibility test skipped before reference cache recovery; NOT fourteen passing Node tests.'),
        separatePriorLocalPreflight=dict(receiptSha256=digest(HERE / 'reference-preflight-v1.json'),
            syntheticFixtures=160, fullGames=20, deterministicReplays=5,
            note='Separate prior evidence, not extra HF-job tests and not rerun/countable as current audit replays.'),
        uncertainty=dict(primaryEstimand='Equal-weight macro credit over 20 fixed Germany cells; average all focal seats within each deal first.',
            independentUnit='80 paired independent deals, four per cell; 1920 seat/policy repeats are not independent trials.',
            formula='For H cells, paired difference = mean_h mean_d (seatMean(policy)-seatMean(control)); SE = sqrt(sum_h s_h^2/4)/H, sample variance uses ddof=1.',
            interval='Approximate normal point +/-1.96*unbiased stratified paired SE, no clipping, no bootstrap.',
            caveats=['Four clusters/cell is small; approximate normal intervals can be unreliable for individual cells.',
                'All six policies and both contrasts reported. No correction for multiple policy/subgroup comparisons; exploratory, not qualification.',
                'Reference control equals 1/n exactly after all-seat averaging; zero reference SE is a design identity, not certainty about general playing strength.',
                'Fixed policies/reference population and Germany only; no inference to humans, other maps or production.',
                'Original summary used unstratified paired-deal SE. Its numeric values were independently reproduced, but new intervals use fixed-cell stratification.',
                'No action traces were saved; legality is enforced by the unchanged authoritative bridge and checked on the replay subset, not independently reconstructed for every recorded move.']),
        qualified=False, qualification_eligible=False, fitted=False, selected=False, promoted=False,
        reserved_final_seeds_used=False, auditSeconds=time.monotonic() - started,
        conclusion='All four frozen candidates and the teacher trail the all-reference baseline on the primary macro-cell estimate; '
            'all five unadjusted approximate-normal 95% paired intervals versus reference lie below zero. '
            'No candidate-versus-teacher approximate interval excludes zero. These are exploratory comparisons, '
            'not multiplicity-adjusted significance or qualification. Report every candidate without best-seed selection or promotion.')
    output = Path(output)
    require(output.resolve() == (HERE / 'neural-results-v1.json').resolve(), 'Only the requested new result file may be written')
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(canonical(dict(stage='audit-complete', output=str(output), games=1920, replays=12,
        macroCredit={p: groups['all']['policies'][p]['macroCellCredit'] for p in POLICIES})), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'neural-results-v1.json')
    args = parser.parse_args()
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[name] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    audit(args.output)
