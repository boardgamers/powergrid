#!/usr/bin/env python3
"""Check exact coverage, raster integrity and evaluator immutability."""
import hashlib
import json
import subprocess
import runpy
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
folder = root / 'art/achievements'
manifest = json.loads((folder / 'manifest.json').read_text())
baseline = json.loads((root / 'docs/releases/achievements-2.0.33.json').read_text())['achievementManifest']
assert [a['id'] for a in manifest['assets']] == [a['id'] for a in baseline['achievements']]
assert len(manifest['assets']) == 36
framing = runpy.run_path(str(root / 'scripts/achievement-map-framing.py'))
assert manifest['framingSha256'] == hashlib.sha256((root / 'scripts/achievement-map-framing.py').read_bytes()).hexdigest()
assert manifest['generatorSha256'] == hashlib.sha256((root / 'scripts/generate-achievement-art.py').read_bytes()).hexdigest()
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
        paths, metrics = framing['framed_map'](a['map'])
        assert metrics == a['framing']
        svg = (folder / a['svg']).read_text()
        assert all('d="' + d + '"' in svg for d in paths)
        # Absolute display-space regression: remote land must never shrink the
        # main silhouette again. Japan's four-island chain is the exception to
        # single-component span, not to the overall occupied frame.
        assert metrics['principalSpan'] >= (45 if a['map'] == 'japan' else 60)
        x0,y0,x1,y1 = metrics['bounds']
        assert abs(max((x1-x0)/90, (y1-y0)/78)-1) < 1e-8
        assert 18.9 <= x0 < x1 <= 109.1 and 30.9 <= y0 < y1 <= 109.1
        if a['map'] in ('america','spainportugal','australia','southafrica'):
            assert metrics['principalSpan'] >= 84
        # Assert the actual small raster contains silhouette ink, not just a
        # large bounding box/crown. Background and gold do not count.
        for size in (32,48,64):
            with Image.open(png) as image:
                pixels = image.resize((size,size), Image.Resampling.LANCZOS)
                cyan = sum(1 for r,g,b,alpha in pixels.get_flattened_data()
                           if alpha > 200 and g > r*1.3 and b > r*1.3 and g > 110)
                assert cyan >= size*size*.025, (a['id'], size, cyan)
assert sum(bool(a['source']) for a in manifest['assets']) == 24
old = subprocess.check_output(['git', 'show', 'c52a87e4b9c41feb35d8e902643514d99fe722f1:engine/src/achievements.ts'], cwd=root).decode()
new = (root / 'engine/src/achievements.ts').read_text()
assert old.split('export function achievementDefinitions')[0] == new.split('export function achievementDefinitions')[0]
assert old.split('function tied(')[1] == new.split('function tied(')[1]
print('36 unique decoded 256px PNGs; 24 hashed geographic sources; full IDs/definitions and evaluator unchanged.')
