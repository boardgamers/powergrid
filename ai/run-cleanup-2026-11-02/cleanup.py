"""Prune only large, archived run files; preserve recovery metadata and models.

Plan -> fresh HF hash check -> explicit file unlink, without following symlinks.
No simulations, job launches, remote writes, directory wipes or git operations.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import stat
import time

BASE = Path(__file__).resolve().parents[2]
RUNS = BASE / 'ai/runs'
OUT = Path(__file__).resolve().parent
MIN_BYTES = 1024 * 1024


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def archives(value):
    if isinstance(value, dict):
        if (value.get('storage') == 'hf_bucket' and value.get('download_verified') is True
                and all(value.get(k) for k in ['bucket', 'path', 'xet_hash', 'archive_sha256', 'manifest_sha256'])):
            yield {**value, 'repo': 'bucket:' + value['bucket'], 'revision': value['xet_hash'],
                   'archive_path': value['path'], 'remote_archive_verified': True}
        elif (value.get('remote_archive_verified') is True
                and all(value.get(k) for k in
                        ['repo', 'revision', 'archive_path', 'archive_sha256', 'manifest_sha256'])):
            yield value
        else:
            for v in value.values():
                yield from archives(v)
    elif isinstance(value, list):
        for v in value:
            yield from archives(v)


def identity(e):
    return '|'.join(e[k] for k in ['repo', 'revision', 'archive_path', 'archive_sha256'])


def plan():
    assert not (OUT / 'plan.json').exists()
    sources = []
    # Direct metadata only: do not traverse raw games to discover receipts.
    for root in RUNS.iterdir():
        if not root.is_dir() or root.is_symlink():
            continue
        parents = [root]
        if (root / 'jobs').is_dir():
            parents.append(root / 'jobs')
        for parent in parents:
            for d in parent.iterdir():
                if not d.is_dir() or d.is_symlink():
                    continue
                for name in ('verified.json', 'promotion-receipt.json', 'review.json', 'receipt.json'):
                    p = d / name
                    if p.is_file():
                        sources.append(p)
        for name in ('verified.json', 'promotion-receipt.json', 'review.json', 'receipt.json'):
            if (root / name).is_file():
                sources.append(root / name)
    sources += list((BASE / 'ai/strong').glob('*evidence*.json'))
    evidence = {}
    candidates = {}
    manifest_records = {}
    rejected = []

    def add_file(p, key, member, witness, expected_sha):
        if not p.is_file() or p.is_symlink():
            return
        try:
            relative = p.relative_to(RUNS)
            p.resolve().relative_to(RUNS.resolve())
        except ValueError:
            return
        # Keep all weights and all compact receipts/metadata locally.
        if p.suffix in ('.onnx', '.pt', '.pth', '.safetensors'):
            return
        st = p.stat()
        if st.st_size < MIN_BYTES or not stat.S_ISREG(st.st_mode):
            return
        # Any files modified after their archive receipt remain untouched.
        if st.st_mtime_ns > witness.stat().st_mtime_ns + 2_000_000_000:
            rejected.append({'path': str(relative), 'reason': 'newer_than_receipt'})
            return
        candidates.setdefault(str(relative), {
            'path': str(relative), 'archive': key, 'archive_member': member,
            'sha256_in_archived_manifest': expected_sha,
            'size': st.st_size, 'blocks': st.st_blocks, 'inode': st.st_ino,
            'device': st.st_dev, 'mtime_ns': st.st_mtime_ns,
        })

    for source in dict.fromkeys(sources):
        try:
            data = read(source)
        except (OSError, ValueError):
            continue
        for e in archives(data):
            key = identity(e)
            basename = Path(e['archive_path']).name
            if not basename.endswith('.tgz'):
                continue
            roots = [source.parent / 'artifacts', source.parent / 'raw', source.parent / basename[:-4],
                     source.parent / 'checkpoints' / basename[:-4], RUNS / basename[:-4]]
            valid_roots = []
            for root in dict.fromkeys(roots):
                m = root / 'manifest.json'
                if not m.is_file() or m.is_symlink():
                    continue
                if digest(m) != e['manifest_sha256']:
                    continue
                entries = read(m)
                if not isinstance(entries, dict) or not all(isinstance(v, str) for v in entries.values()):
                    continue
                valid_roots.append(root)
                evidence[key] = {**e, 'descriptor': str(source.relative_to(BASE))}
                manifest_records[str(m.relative_to(RUNS))] = e['manifest_sha256']
                for name, sha in entries.items():
                    if Path(name).is_absolute() or '..' in Path(name).parts:
                        raise ValueError('Unsafe manifest path')
                    add_file(root / name, key, name, source, sha)
                    # Versioned collections include exact copies of their original
                    # envelope and checkpoints. Preserve a mapping for both copies.
                    if source.name == 'promotion-receipt.json' and name.startswith(('envelope/', 'checkpoints/')):
                        add_file(source.parent / name, key, name, source, sha)
            if valid_roots:
                for archive in [source.parent / basename, RUNS / basename]:
                    add_file(archive, key, None, source, e['archive_sha256'])

    values = sorted(candidates.values(), key=lambda v: v['path'])
    totals = collections.Counter()
    for c in values:
        totals[Path(c['path']).parts[0]] += c['blocks'] * 512
    write(OUT / 'plan.json', {
        'created_at': time.time(), 'runs_root': str(RUNS), 'minimum_file_bytes': MIN_BYTES,
        'archives': evidence, 'manifests': manifest_records, 'files': values,
        'planned_allocated_bytes': sum(v['blocks'] * 512 for v in values),
        'by_directory': dict(totals.most_common()), 'preserved_newer_files': rejected,
    })
    print(json.dumps({'planned_files': len(values), 'archives': len(evidence),
                      'planned_GB': sum(totals.values()) / 1e9,
                      'top': totals.most_common(15), 'newer_files_retained': len(rejected)}), flush=True)


def verify_remote():
    from huggingface_hub import HfApi
    p = read(OUT / 'plan.json')
    api = HfApi()
    groups = collections.defaultdict(dict)
    for key, e in p['archives'].items():
        groups[e['repo']][e['archive_path']] = e['archive_sha256']
    tasks, heads = [], {}
    for repo, paths in groups.items():
        if repo.startswith('bucket:'):
            heads[repo] = {'bucket': repo[7:], 'versioned': False}
            names = list(paths)
            for i in range(0, len(names), 100):
                tasks.append((repo, None, names[i:i + 100]))
            continue
        info = api.repo_info(repo)
        heads[repo] = {'revision': info.sha, 'private': info.private}
        names = list(paths)
        for i in range(0, len(names), 100):
            tasks.append((repo, info.sha, names[i:i + 100]))

    def check(task):
        repo, rev, paths = task
        if repo.startswith('bucket:'):
            return [(repo, f.path, f.xet_hash, f.size)
                    for f in api.get_bucket_paths_info(repo[7:], paths)]
        rows = api.get_paths_info(repo, paths, revision=rev)
        return [(repo, f.path, getattr(getattr(f, 'lfs', None), 'sha256', None),
                 getattr(f, 'size', None)) for f in rows]

    found = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(check, tasks):
            for repo, path, sha, size in result:
                found[(repo, path)] = {'sha256': sha, 'size': size}
    verified, missing = {}, []
    for key, e in p['archives'].items():
        obj = found.get((e['repo'], e['archive_path']))
        expected = e['xet_hash'] if e['repo'].startswith('bucket:') else e['archive_sha256']
        if obj and obj['sha256'] == expected:
            if e['repo'].startswith('bucket:'):
                assert obj['size'] == e['bytes']
            verified[key] = {'verified_at_revision': heads[e['repo']].get('revision'), **obj}
        else:
            missing.append(key)
    write(OUT / 'remote-verification.json', {
        'checked_at': time.time(), 'heads': heads, 'verified': verified,
        'missing_or_mismatched': missing, 'plan_sha256': digest(OUT / 'plan.json'),
        'method': 'Fresh HF LFS object hash at pinned current revision matches previously download-verified immutable archive receipt',
    })
    print(json.dumps({'verified_archives': len(verified), 'unverified_preserved': len(missing),
                      'heads': heads}), flush=True)


def apply():
    p, r = read(OUT / 'plan.json'), read(OUT / 'remote-verification.json')
    assert digest(OUT / 'plan.json') == r['plan_sha256']
    assert time.time() - r['checked_at'] < 86400
    assert not (OUT / 'deleted.jsonl').exists(), 'Inspect previous outcome before retrying'
    assert RUNS.resolve() == Path(p['runs_root']).resolve()
    # Recheck recovery manifests immediately before any deletion.
    for name, sha in p['manifests'].items():
        assert digest(RUNS / name) == sha, name
    deleted, total, retained = 0, 0, []
    free_before = os.statvfs(RUNS).f_bavail * os.statvfs(RUNS).f_frsize
    with (OUT / 'deleted.jsonl').open('x') as log:
        for c in p['files']:
            if c['archive'] not in r['verified']:
                retained.append({'path': c['path'], 'reason': 'remote_not_verified'})
                continue
            path = RUNS / c['path']
            path.resolve().relative_to(RUNS.resolve())
            st = path.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_ino != c['inode'] or st.st_dev != c['device']
                    or st.st_size != c['size'] or st.st_mtime_ns != c['mtime_ns']):
                retained.append({'path': c['path'], 'reason': 'changed_since_plan'})
                continue
            path.unlink()
            log.write(json.dumps({'path': c['path'], 'archive': c['archive'],
                                  'archive_member': c['archive_member'], 'size': c['size'],
                                  'allocated_bytes': st.st_blocks * 512}) + '\n')
            deleted += 1
            total += st.st_blocks * 512
            if deleted % 1000 == 0:
                log.flush()
                os.fsync(log.fileno())
                print(json.dumps({'deleted_files': deleted, 'GB': total / 1e9}), flush=True)
        log.flush()
        os.fsync(log.fileno())
    free_after = os.statvfs(RUNS).f_bavail * os.statvfs(RUNS).f_frsize
    write(OUT / 'result.json', {'completed_at': time.time(), 'deleted_files': deleted,
        'deleted_allocated_bytes': total, 'filesystem_available_before': free_before,
        'filesystem_available_after': free_after, 'retained': retained,
        'plan_sha256': digest(OUT / 'plan.json'),
        'remote_verification_sha256': digest(OUT / 'remote-verification.json')})
    print(json.dumps({'complete': True, 'deleted_files': deleted, 'GB': total / 1e9,
                      'preserved': len(retained)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['plan', 'verify-remote', 'apply'])
    parser.add_argument('--batch', choices=['second'])
    args = parser.parse_args()
    if args.batch:
        OUT = OUT / args.batch
        OUT.mkdir(exist_ok=True)
    {'plan': plan, 'verify-remote': verify_remote, 'apply': apply}[args.operation]()
