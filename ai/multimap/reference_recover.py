"""Bounded, immutable recovery for the Germany FILTER comparison (no snapshots).

Run with ai/.venv/bin/python -B ai/multimap/reference_recover.py.
Only pinned files are downloaded. Compressed source stays in <=256 MiB RAM;
the complete unchanged artifact stays under a 512 MiB disk cap, without a
duplicate archive. Never prune HF's shared cache. The serving virtualenv is
separate from training; archived non-runtime fixtures are verified, not used.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile

# Prevent a second Xet chunk cache when this standalone helper imports HF.
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'ai/runs/multimap-reference-preflight-v1'
MAX_ARCHIVE = 256 * 1024**2
MAX_CACHE = 512 * 1024**2
MANIFEST_SHA = 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'
DESCRIPTOR_SHA = '3b492c71ac5653ac7c41dfefd1c397e74e14df6f57629a455c61c8e45f55f52a'
PINS = {
    'source': dict(repo='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
        revision='7db94147918597e1da1e8ee2f4bd12b96aa067b5',
        path='strong-source-current-auction-grid-v1.tgz',
        sha256='bb2ef01bc09f176c62545971aa02b5e9dadc947fb14dd52ca191667ba456bfe0'),
    'model': dict(repo='coyotte508/powergrid-ai-germany-v1', repo_type='model',
        revision='6b6009756d7b5968bc5b6425efc84a94aab2a1d6',
        path='runs/policy-iteration-training-v2-frozen/ensemble-1/derivative/inference64.onnx',
        sha256='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'),
    'ppo': dict(repo='coyotte508/powergrid-ai-multimap-v1', repo_type='model',
        revision='b1392c4dea3eb956b0e171d558f2f642c0367831',
        path='runs/multimap-ppo-20261102-v1/ppo/best.pt',
        sha256='50ac24ad28d8fced065133e90980286e0cf4c592afe81df07aaed33cbf181e0c'),
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cache_bytes(cache):
    return sum(p.stat().st_size for p in Path(cache).rglob('*') if p.is_file())


def budget(cache, additional=0):
    size = cache_bytes(cache) + additional
    if size > MAX_CACHE:
        raise ValueError(f'Reference cache budget exceeded: {size} > {MAX_CACHE}')
    return size


def remote_metadata(pin):
    from huggingface_hub import get_hf_file_metadata, hf_hub_url, get_token
    meta = get_hf_file_metadata(hf_hub_url(pin['repo'], pin['path'],
        repo_type=pin['repo_type'], revision=pin['revision']), token=get_token())
    if meta.commit_hash != pin['revision'] or not isinstance(meta.size, int) or meta.size <= 0:
        raise ValueError('Missing size or immutable revision mismatch')
    if meta.size > MAX_ARCHIVE:
        raise ValueError(f'Refusing oversized remote file: {meta.size} > {MAX_ARCHIVE}')
    return dict(bytes=meta.size, revision=meta.commit_hash)


def download(pin, cache, destination):
    """Inspect size first; local_dir avoids an additional shared-cache blob."""
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    from huggingface_hub import hf_hub_download
    meta = remote_metadata(pin)
    if destination.exists():
        if digest(destination) != pin['sha256']:
            raise ValueError('Existing destination hash mismatch')
        return meta
    budget(cache, meta['bytes'])
    staging = cache / 'download-staging'
    path = Path(hf_hub_download(pin['repo'], pin['path'], repo_type=pin['repo_type'],
        revision=pin['revision'], local_dir=staging))
    if digest(path) != pin['sha256'] or path.stat().st_size != meta['bytes']:
        raise ValueError('Downloaded bytes do not match immutable pin')
    destination.parent.mkdir(parents=True, exist_ok=True)
    path.replace(destination)
    shutil.rmtree(staging)
    budget(cache)
    return meta


def memory_archive(pin, metadata):
    """Pinned compressed bytes in bounded RAM; no simultaneous disk archive."""
    from huggingface_hub import hf_hub_url, get_token
    from huggingface_hub.utils import build_hf_headers, get_session
    size = metadata['bytes']
    if not 0 < size <= MAX_ARCHIVE or metadata['revision'] != pin['revision']:
        raise ValueError('Invalid memory archive budget/revision')
    stream = io.BytesIO()
    checksum = hashlib.sha256()
    try:
        url = hf_hub_url(pin['repo'], pin['path'], repo_type=pin['repo_type'], revision=pin['revision'])
        with get_session().stream('GET', url, headers=build_hf_headers(token=get_token()),
                                  follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes(chunk_size=1024**2):
                if stream.tell() + len(chunk) > size:
                    raise ValueError('Memory archive exceeded advertised size')
                checksum.update(chunk)
                stream.write(chunk)
        if stream.tell() != size or checksum.hexdigest() != pin['sha256']:
            raise ValueError('Memory archive hash/size mismatch')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def open_archive(archive):
    if hasattr(archive, 'read'):
        archive.seek(0)
        return tarfile.open(fileobj=archive, mode='r:gz')
    return tarfile.open(archive, 'r:gz')


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or not path.parts:
        raise ValueError('Unsafe archive path')
    return path


def extract_selected(archive, output, members, cache):
    """Extract regular files only, explicit original-name -> relative-path map."""
    found = set()
    with open_archive(archive) as tf:
        for member in tf:
            if member.name not in members:
                continue
            relative = safe_name(members[member.name])
            if not member.isfile() or member.name in found:
                raise ValueError('Non-regular or duplicate selected archive member')
            found.add(member.name)
            target = output.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(output.resolve()):
                raise ValueError('Escaped extraction target')
            budget(cache, member.size)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(member) as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst)
    if found != set(members):
        raise ValueError('Missing selected archive members')


def verify_artifact(artifact, *, require_complete=True):
    manifest_path = artifact / 'manifest.json'
    descriptor_path = artifact / 'policy.json'
    if digest(manifest_path) != MANIFEST_SHA or digest(descriptor_path) != DESCRIPTOR_SHA:
        raise ValueError('Wrong FILTER runtime manifest or descriptor')
    manifest = json.loads(manifest_path.read_text())
    present = 0
    missing = []
    for name, expected in manifest.items():
        path = artifact.joinpath(*safe_name(name).parts)
        if not path.resolve().is_relative_to(artifact.resolve()):
            raise ValueError('Escaped runtime file: ' + name)
        if not path.is_file():
            if not require_complete and runtime_member(name):
                raise ValueError('Missing required runtime file: ' + name)
            missing.append(name)
            continue
        if digest(path) != expected:
            raise ValueError('Runtime file mismatch: ' + name)
        present += 1
    if manifest.get('policy.onnx') != PINS['model']['sha256']:
        raise ValueError('Wrong retained model')
    if require_complete and missing:
        raise ValueError(f'Exact archived load_artifact requires {len(missing)} omitted non-runtime assets; '
                         'compact recovery is NOT a runnable exact artifact')
    return dict(present=present, missing=missing)


def runtime_member(name):
    # The retained FILTER does not consume training roots, serving fixtures, or
    # opponent models. Keep all code/dependencies/configs, plus its own ONNX.
    path = safe_name(name)
    return not ({'fixtures', 'data'} & set(path.parts)) and (
        not name.endswith(('.onnx', '.pt', '.jsonl', '.gz')) or name == 'policy.onnx')


def inspect_archive(archive):
    """Inspect the complete member table before writing a single expanded byte."""
    manifests, descriptors, sizes = [], [], {}
    with open_archive(archive) as tf:
        for member in tf:
            safe_name(member.name)
            if member.name in sizes:
                raise ValueError('Duplicate archive path')
            sizes[member.name] = (member.size, member.isfile())
            if member.isfile() and member.size < 2 * 1024**2 and member.name.endswith('.json'):
                data = tf.extractfile(member).read()
                sha = hashlib.sha256(data).hexdigest()
                if sha == MANIFEST_SHA:
                    manifests.append((member.name, json.loads(data)))
                if sha == DESCRIPTOR_SHA:
                    descriptors.append(member.name)
    if len(manifests) != 1 or not descriptors:
        raise ValueError('Pinned exact runtime/descriptor not uniquely found')
    manifest_name, manifest = manifests[0]
    prefix = str(PurePosixPath(manifest_name).parent) + '/'
    members = {prefix + name: name for name in manifest}
    members[manifest_name] = 'manifest.json'
    members[descriptors[0]] = 'policy.json'
    if any(name not in sizes or not sizes[name][1] for name in members):
        raise ValueError('Missing or non-regular artifact member')
    selected = {old: new for old, new in members.items() if runtime_member(new)}
    omitted = [dict(path=new, bytes=sizes[old][0], sha256=manifest[new])
               for old, new in members.items() if old not in selected]
    return dict(manifest=manifest, prefix=prefix, selected=selected, members=members, omitted=omitted,
        fullArtifactBytes=sum(sizes[name][0] for name in members),
        compactArtifactBytes=sum(sizes[name][0] for name in selected))


def verify_archived_members(archive, plan):
    """Hash all immutable manifest bytes in bounded memory, without saving roots."""
    wanted = {plan['prefix'] + name: sha for name, sha in plan['manifest'].items()}
    found = set()
    with open_archive(archive) as tf:
        for member in tf:
            if member.name in wanted:
                if not member.isfile() or member.name in found:
                    raise ValueError('Invalid manifest member')
                with tf.extractfile(member) as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != wanted[member.name]:
                        raise ValueError('Archived manifest member hash mismatch: ' + member.name)
                found.add(member.name)
    if found != set(wanted):
        raise ValueError('Missing archived manifest member')
    return len(found)


def recover(cache=CACHE):
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    metadata = {key: remote_metadata(pin) for key, pin in PINS.items()}
    budget(cache)
    artifact = cache / 'artifact'
    receipt_path = cache / 'recovery.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['pins'] != PINS:
            raise ValueError('Wrong prior recovery pins')
        checked = verify_artifact(artifact, require_complete=False)
        if digest(cache / 'ppo.pt') != PINS['ppo']['sha256']:
            raise ValueError('Wrong PPO checkpoint')
        if receipt['exactServiceReady'] and not checked['missing']:
            return receipt
    elif artifact.exists():
        raise ValueError('Partial artifact exists; inspect/remove only this generated directory before retry')
    # The complete unchanged manifest fits on disk. Its compressed source stays
    # in <=256 MiB RAM, not beside the expanded fixtures. No loader bypass and
    # no fixture is used as training/evaluation data; these bytes are hash-only.
    with memory_archive(PINS['source'], metadata['source']) as archive:
        plan = inspect_archive(archive)
        extra_ppo = 0 if (cache / 'ppo.pt').exists() else metadata['ppo']['bytes']
        budget(cache, plan['fullArtifactBytes'] - cache_bytes(artifact) + extra_ppo)
        verified = verify_archived_members(archive, plan)
        missing = {old: new for old, new in plan['members'].items() if not (artifact / new).exists()}
        extract_selected(archive, artifact, missing, cache)
    checked = verify_artifact(artifact)
    download(PINS['ppo'], cache, cache / 'ppo.pt')
    receipt = dict(pins=PINS, remote=metadata, runtimeManifestSha256=MANIFEST_SHA,
        policySha256=DESCRIPTOR_SHA, verifiedArchiveManifestFiles=verified,
        locallyVerifiedFiles=checked['present'], omitted=[],
        fullArtifactBytes=plan['fullArtifactBytes'], compactArtifactBytes=plan['compactArtifactBytes'],
        compressedArchiveRamBytes=metadata['source']['bytes'],
        diskBudgetBytes=MAX_CACHE, compressedArchiveRamCapBytes=MAX_ARCHIVE,
        recoveryMode='complete-unchanged-manifest-with-compressed-source-in-bounded-RAM',
        cacheBytes=budget(cache), reserved_final_seeds_used=False,
        exactServiceReady=True, blocker=None)
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--inspect-only', action='store_true')
    args = parser.parse_args()
    result = {key: remote_metadata(pin) for key, pin in PINS.items()} if args.inspect_only else recover(args.cache)
    print(json.dumps(result, indent=2))
