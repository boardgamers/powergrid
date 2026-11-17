"""Badge-only geographic framing; never imported by viewer/gameplay.

Inputs are unwarped lon/lat geometries from the curated offline source, not
board-coordinate paths (the board warp can join islands and distort coastlines).
Windows below are editorial scope, not new territorial boundary claims.
"""
import json
import math
from pathlib import Path
from shapely.geometry import shape, box
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'viewer/scripts/geography/source.json'
# west, south, east, north; explicit scope and rationale for EVERY badge.
FRAMES = {
    'germany': ((5, 47, 16, 56), 'Germany mainland; omit subpixel coastal islets.'),
    'america': ((-125, 24, -66, 50), 'Contiguous USA; omit Alaska, Hawaii and overseas islands.'),
    'france': ((-6, 41, 10, 52), 'Metropolitan France including Corsica; omit overseas departments.'),
    'japan': ((128, 30, 146, 46), 'Four main islands in true geographic positions; omit remote Ryukyu/Bonin chain.'),
    'brazil': ((-75, -35, -34, 6), 'Continental Brazil; omit subpixel offshore islands.'),
    'spainportugal': ((-10, 35.5, 4.5, 44.5), 'Iberian mainland and Balearics; omit Azores, Madeira and Canaries.'),
    'indian': ((67, 6, 98, 37.5), 'Indian mainland; omit Andaman/Nicobar and Lakshadweep islets.'),
    'italy': ((6, 36, 19, 48), 'Peninsula, Sicily and Sardinia; omit subpixel islets.'),
    'quebec': ((-81, 44, -57, 63), 'Whole Quebec mainland, not just the southern city corridor.'),
    'middleeast': ((33, 12, 64, 40), 'Authored Middle East country union; omit distant/subpixel islands.'),
    'china': ((73, 18, 135.5, 54), 'Mainland and Hainan from curated active geometry.'),
    'benelux': ((2, 49, 8, 54), 'Belgium, Netherlands and Luxembourg union; omit subpixel islets.'),
    'russia': ((19, 40, 180, 78), 'Russian mainland to Bering Strait; omit dateline fragments and Arctic archipelagos below size cutoff.'),
    'centraleurope': ((9, 45, 25, 56), 'Complete authored Central Europe country union.'),
    'badenwurttemberg': ((7, 47, 11, 50), 'Complete Baden-Wuerttemberg provincial outline.'),
    'northerneurope': ((3, 53, 33, 72), 'Scandinavian/Baltic mainland and major Danish islands; omit Svalbard and remote Arctic islands.'),
    'korea': ((124, 32.7, 132, 44), 'Korean peninsula and Jeju; omit subpixel islets.'),
    'europe': ((-12, 34, 45, 72), 'European mainland to 45E plus Britain/Ireland and major Mediterranean islands; omit overseas territories and remote Arctic islands.'),
    'northamerica': ((-169, 7, -52, 75), 'Continental North America including Alaska, Canada and Mexico; omit Hawaii and far Arctic islands.'),
    'southafrica': ((16, -35, 33, -22), 'South African mainland; omit remote Prince Edward islands.'),
    'ukireland': ((-11, 49, 2, 61), 'Great Britain and Ireland, with larger coastal islands.'),
    'australia': ((112, -44, 154, -10), 'Australian mainland and Tasmania; omit external Indian/Pacific Ocean territories.'),
    'bremen': ((8.4, 52.98, 9.03, 53.27), 'Bremen city component; omit detached Bremerhaven to preserve city silhouette.'),
    'manhattan': ((-74.025, 40.68, -73.9, 40.885), 'Manhattan main island; omit tiny detached borough islets.'),
}

def polygons(geometry):
    return [geometry] if geometry.geom_type == 'Polygon' else [p for p in geometry.geoms if p.geom_type == 'Polygon']

def framed_map(name):
    data = json.loads((ROOT / SOURCE).read_text())['maps'][name]
    bounds, reason = FRAMES[name]
    # Local equirectangular projection preserves a sensible geographic aspect;
    # unlike the viewer's city-fitted warp it never joins separate islands.
    cosine = math.cos(math.radians((bounds[1] + bounds[3]) / 2))
    project = lambda x, y, z=None: (x * cosine, -y)
    selected = shape(data['active']).intersection(box(*bounds))
    projected = transform(project, selected)
    parts = polygons(projected)
    # Remove subpixel islands BEFORE fitting, so a remote speck cannot set scale.
    largest = max(p.area for p in parts)
    parts = [p for p in parts if p.area >= largest * .003]
    x0 = min(p.bounds[0] for p in parts); y0 = min(p.bounds[1] for p in parts)
    x1 = max(p.bounds[2] for p in parts); y1 = max(p.bounds[3] for p in parts)
    scale = min(90 / (x1-x0), 78 / (y1-y0))
    tx, ty = 64-(x0+x1)*scale/2, 70-(y0+y1)*scale/2
    screen = [transform(lambda x,y,z=None: (x*scale+tx,y*scale+ty), p) for p in parts]
    simplified = [p.simplify(.45, preserve_topology=True) for p in screen]
    paths = []
    for p in simplified:
        # Lakes and tiny interior holes are intentionally filled at badge scale.
        paths.append('M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in p.exterior.coords)+' Z')
    metrics = dict(window=list(bounds), reason=reason, components=len(parts),
                   bounds=[x0*scale+tx,y0*scale+ty,x1*scale+tx,y1*scale+ty],
                   principalSpan=max(max(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1]) for p in screen),
                   simplifyTolerance=.45, minRelativeArea=.003)
    return paths, metrics
