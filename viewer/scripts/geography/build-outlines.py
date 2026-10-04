"""Generate fitted SVG geography for the LOCAL map preview (NumPy + Shapely).

Coordinates stay in the existing board's space. Only the backdrop is warped.
The input is a small, pinned public-domain Natural Earth subset, not board art.
"""
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
source = json.loads((HERE / 'natural-earth-source.json').read_text())
output = {}


def kernel(a, b):
    squared = ((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
    return squared * np.log(np.maximum(squared, 1e-20)) / 2


def projector(landmarks, smoothing):
    # Local equirectangular coordinates; thin-plate spline accounts for the
    # original board's deliberately non-geographic spacing and rotation.
    scale = np.array([np.cos(np.deg2rad(53)), 1])
    anchors = np.array([a['lonLat'] for a in landmarks]) * scale
    target = np.array([a['board'] for a in landmarks])
    p = np.column_stack([np.ones(len(anchors)), anchors])
    k = kernel(anchors, anchors) + np.eye(len(anchors)) * smoothing
    system = np.block([[k, p], [p.T, np.zeros((3, 3))]])
    coefficients = np.linalg.solve(system, np.vstack([target, np.zeros((3, 2))]))

    def project(coords):
        points = np.array(coords) * scale
        return np.column_stack([kernel(points, anchors), np.ones(len(points)), points]) @ coefficients

    errors = np.linalg.norm(project([a['lonLat'] for a in landmarks]) - target, axis=1)
    return project, float(max(errors))


for key, data in source['maps'].items():
    groups = [None] if key == 'germany' else ['gb', 'ie']
    projections = {group: projector([a for a in data['anchors'] if a['island'] == group],
                                    0.025 if key == 'germany' else 0.2) for group in groups}

    land = unary_union([shape(g) for g in data['geometry']])
    polygons = list(land.geoms) if land.geom_type == 'MultiPolygon' else [land]
    fitted = []
    for polygon in polygons:
        # Keep mainland(s) and sizeable nearshore islands; omit distant overseas
        # territories and the far northern island groups outside this game board.
        c = polygon.centroid
        if polygon.area < (0.015 if key == 'germany' else 1) or not (-11 < c.x < 16 and 47 < c.y < 59):
            continue
        if key == 'ukireland' and c.y > 58.8:
            continue
        group = None if key == 'germany' else ('ie' if c.x < -6 else 'gb')
        project, _ = projections[group]
        coords = project(polygon.simplify(0.012, preserve_topology=True).exterior.segmentize(0.01).coords)
        if group == 'gb':
            # The schematic squeezes the Irish Sea: an unconstrained fit merges
            # the islands. Art-directed western-shore envelope, in board units,
            # compresses only the coastline beside Ireland, never city positions.
            ys = [200, 280, 320, 360, 420, 470, 510, 550, 600, 660]
            xs = [200, 370, 395, 410, 410, 382, 365, 335, 300, 200]
            shore = np.interp(coords[:, 1], ys, xs, left=-1000, right=-1000)
            west = coords[:, 0] < shore
            coords[west, 0] = shore[west] + 0.1 * (coords[west, 0] - shore[west])
        fitted.append(Polygon(coords))
    assert all(p.is_valid for p in fitted), f'{key}: warped coastline crossed itself'
    # Small cartographic clearance for large city discs and generalized coastlines.
    backdrop = unary_union(fitted).buffer(10, join_style='round').simplify(1.4, preserve_topology=True)
    assert backdrop.is_valid
    polygons = list(backdrop.geoms) if backdrop.geom_type == 'MultiPolygon' else [backdrop]
    paths = []
    for polygon in polygons:
        points = list(polygon.exterior.coords)
        paths.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in points) + 'Z')
    uncovered = [a['city'] for a in data['anchors'] if not backdrop.covers(Point(a['board']))]
    output[key] = {'name': data['name'], 'paths': paths, 'bounds': list(backdrop.bounds),
                   'anchorCount': len(data['anchors']), 'maxAnchorError': round(max(e for _, e in projections.values()), 2),
                   'uncoveredAnchors': uncovered}
    if key == 'ukireland':
        assert len(paths) == 2, 'Keep Great Britain and Ireland separate'
        assert polygons[0].distance(polygons[1]) > 12, 'Keep the sea gap legible'
    print(key, 'paths', len(paths), 'bounds', backdrop.bounds, 'outside', uncovered)

(HERE / 'outlines.json').write_text(json.dumps(output, indent=2) + '\n')
