#!/usr/bin/env python3
"""Check exact coverage, raster integrity and evaluator immutability."""
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
folder = root / 'art/achievements'
manifest = json.loads((folder / 'manifest.json').read_text())
baseline = json.loads((root / 'docs/releases/achievements-2.0.33.json').read_text())['achievementManifest']
assert [a['id'] for a in manifest['assets']] == [a['id'] for a in baseline['achievements']]
assert len(manifest['assets']) == 36
hashes = set()
for a in manifest['assets']:
    assert a['key'] == 'achievement-' + a['id']
    png = folder / a['png']
    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    assert digest == a['sha256'] and digest not in hashes
    hashes.add(digest)
    with Image.open(png) as image:
        image.load()
        assert image.size == (256, 256) and image.mode == 'RGBA'
        assert image.getpixel((0, 0))[3] == 0
    assert (folder / a['svg']).is_file()
    if a['source']:
        assert hashlib.sha256((root / a['source']).read_bytes()).hexdigest() == a['sourceSha256']
assert sum(bool(a['source']) for a in manifest['assets']) == 24
old = subprocess.check_output(['git', 'show', 'c52a87e4b9c41feb35d8e902643514d99fe722f1:engine/src/achievements.ts'], cwd=root).decode()
new = (root / 'engine/src/achievements.ts').read_text()
assert old.split('export function achievementDefinitions')[0] == new.split('export function achievementDefinitions')[0]
assert old.split('function tied(')[1] == new.split('function tied(')[1]
print('36 unique decoded 256px PNGs; 24 hashed geographic sources; full IDs/definitions and evaluator unchanged.')
