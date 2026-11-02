"""Remove remaining large files only after exact-byte matching to checked backups."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run_cleanup', HERE / 'cleanup.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
OUT = HERE / 'duplicates'
OUT.mkdir(exist_ok=True)


def plan():
    assert not (OUT / 'plan.json').exists()
    proofs, verified, archive_data = {}, {}, {}
    checks = []
    for batch in [HERE, HERE / 'second']:
        p, r = c.read(batch / 'plan.json'), c.read(batch / 'remote-verification.json')
        assert c.digest(batch / 'plan.json') == r['plan_sha256']
        checks.append(r['checked_at'])
        archive_data.update(p['archives'])
        verified.update(r['verified'])
        by_manifest = {}
        for key, e in p['archives'].items():
            if key in r['verified']:
                by_manifest.setdefault(e['manifest_sha256'], key)
        for relative, sha in p['manifests'].items():
            key = by_manifest.get(sha)
            m = c.RUNS / relative
            if key is None or not m.is_file() or c.digest(m) != sha:
                continue
            for member, value in c.read(m).items():
                proofs.setdefault(value, (key, member, relative, sha))
        for f in p['files']:
            if f['archive'] in r['verified']:
                proofs.setdefault(f['sha256_in_archived_manifest'],
                                  (f['archive'], f['archive_member'], None, None))
    assert time.time() - min(checks) < 86400
    candidates = []
    for directory, dirs, files in os.walk(c.RUNS):
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
        for name in files:
            p = Path(directory) / name
            if p.suffix in ('.onnx', '.pt', '.pth', '.safetensors'):
                continue
            st = p.lstat()
            if stat.S_ISREG(st.st_mode) and st.st_size >= c.MIN_BYTES:
                candidates.append((p, st))
    print(json.dumps({'hashing_files': len(candidates),
                      'GB_to_read': sum(st.st_size for p, st in candidates) / 1e9}), flush=True)

    def check(item):
        p, st = item
        sha = c.digest(p)
        if sha not in proofs:
            return None
        now = p.lstat()
        assert (st.st_size, st.st_mtime_ns, st.st_ino) == (now.st_size, now.st_mtime_ns, now.st_ino)
        key, member, mpath, msha = proofs[sha]
        return ({'path': str(p.relative_to(c.RUNS)), 'archive': key, 'archive_member': member,
                 'sha256_in_archived_manifest': sha, 'size': st.st_size, 'blocks': st.st_blocks,
                 'inode': st.st_ino, 'device': st.st_dev, 'mtime_ns': st.st_mtime_ns}, mpath, msha)

    found, manifests, used = [], {}, set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i, result in enumerate(pool.map(check, candidates), 1):
            if result:
                row, mpath, msha = result
                found.append(row)
                used.add(row['archive'])
                if mpath:
                    manifests[mpath] = msha
            if i % 500 == 0:
                print(json.dumps({'hashed': i, 'matched': len(found)}), flush=True)
    c.write(OUT / 'plan.json', {'created_at': time.time(), 'runs_root': str(c.RUNS),
        'minimum_file_bytes': c.MIN_BYTES, 'archives': {k: archive_data[k] for k in used},
        'manifests': manifests, 'files': found,
        'planned_allocated_bytes': sum(f['blocks'] * 512 for f in found),
        'method': 'Actual SHA-256 of each remaining file matches a file in a remotely verified archive'})
    c.write(OUT / 'remote-verification.json', {'checked_at': min(checks),
        'verified': {k: verified[k] for k in used}, 'missing_or_mismatched': [],
        'plan_sha256': c.digest(OUT / 'plan.json'),
        'method': 'Reuse the fresh archive object checks of the first and second cleanup passes'})
    print(json.dumps({'matched_files': len(found),
                      'GB': sum(f['blocks'] * 512 for f in found) / 1e9,
                      'unmatched_files_preserved': len(candidates) - len(found)}), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['plan']:
        plan()
    elif sys.argv[1:] == ['apply']:
        c.OUT = OUT
        c.apply()
    else:
        raise SystemExit('Use plan or apply')
