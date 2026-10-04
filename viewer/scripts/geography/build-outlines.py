"""Build offline SVG land/water layers. Requires NumPy and Shapely >= 2.

Only geography is fitted. Engine coordinates and viewport geometry are untouched.
See source.json for pinned data, source IDs, attribution and authored coordinates.
"""
import json
from pathlib import Path
import numpy as np
from shapely.geometry import Point, Polygon, MultiPoint, LineString, box, shape
from shapely.ops import unary_union
from shapely import make_valid

HERE = Path(__file__).resolve().parent
SOURCE = json.loads((HERE / 'source.json').read_text())


def polygons(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    return [p for part in getattr(geometry, 'geoms', []) for p in polygons(part)]


def kernel(a, b):
    squared = ((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
    return squared * np.log(np.maximum(squared, 1e-20)) / 2


def projector(landmarks, smoothing=0.0002):
    ll = np.array([a['lonLat'] for a in landmarks])
    scale = np.array([np.cos(np.deg2rad(ll[:, 1].mean())), 1])
    center = (ll * scale).mean(axis=0)
    span = max(np.ptp(ll * scale, axis=0))
    anchors = (ll * scale - center) / span
    target = np.array([a['board'] for a in landmarks])
    p = np.column_stack([np.ones(len(anchors)), anchors])
    k = kernel(anchors, anchors) + np.eye(len(anchors)) * smoothing
    coefficients = np.linalg.solve(np.block([[k, p], [p.T, np.zeros((3, 3))]]),
                                   np.vstack([target, np.zeros((3, 2))]))

    def project(coords):
        points = (np.array(coords) * scale - center) / span
        return np.column_stack([kernel(points, anchors), np.ones(len(points)), points]) @ coefficients
    error = np.linalg.norm((project(ll) - target), axis=1)
    return project, error


def manhattan_projector(data):
    # M1..M83 are anonymous game spaces, not geocoded intersections. Align the
    # real island's long axis to the authored grid and fit its transverse width
    # to the grid's envelope. Northern Manhattan continues beyond the clipped
    # board; no fictitious coastline closes the cropped northern edge.
    land = max(polygons(shape(data['active'])), key=lambda p: p.area)
    cosine = np.cos(np.deg2rad(40.78))
    north = np.array([0.075 * cosine, 0.172]); north /= np.linalg.norm(north)
    east = np.array([north[1], -north[0]])
    origin = np.array([-74.015 * cosine, 40.703])
    def raw(coords):
        q = np.array(coords) * [cosine, 1] - origin
        return np.column_stack([q @ east, 1100 - (q @ north) * 9000])
    rawLand = Polygon(raw(land.exterior.coords))
    cityHull = MultiPoint([(c['x'], c['y']) for c in data['cities']]).convex_hull.buffer(36)
    ys = np.arange(80, 1141, 20)
    rows = []
    for y in ys:
        a = rawLand.intersection(LineString([(-10, y), (10, y)]))
        b = cityHull.intersection(LineString([(-1000, y), (2000, y)]))
        if not a.is_empty and not b.is_empty:
            rows.append([y, a.bounds[0], a.bounds[2], b.bounds[0], b.bounds[2]])
    rows = np.array(rows)
    def project(coords):
        points = raw(coords); y = points[:, 1]
        left, right, targetLeft, targetRight = [np.interp(y, rows[:, 0], rows[:, i]) for i in range(1, 5)]
        x = targetLeft + (points[:, 0] - left) / (right - left) * (targetRight - targetLeft)
        return np.column_stack([x, y])
    return project


def path_string(geometry, tolerance):
    paths = []
    for polygon in polygons(geometry.simplify(tolerance, preserve_topology=True)):
        if polygon.area < tolerance ** 2:
            continue
        rings = [polygon.exterior, *polygon.interiors]
        paths.append(''.join('M' + 'L'.join(f'{x:.0f},{y:.0f}' for x, y in ring.coords) + 'Z' for ring in rings))
    return paths


def build(key, data):
    ratio = np.array(data['ratio'])
    tolerance = 1.7 / max(ratio)
    clearance = 9 / max(ratio)
    allCities = [*data['cities'], *data['extraCities']]
    xy = np.array([[c['x'], c['y']] for c in allCities])
    bounds = [*xy.min(axis=0), *xy.max(axis=0)]
    # Cover the full authored board, including the market/player-board area.
    # A rotated map pivots around its selected cities. Bound every possible pivot
    # inside the authored city envelope so subsets also have geographic coverage.
    layout = data['layout']
    angle = np.deg2rad(-layout['mapRotation'])
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    w, h = layout['viewBox']
    corners = np.array([[-32,-32],[w+32,-32],[w+32,h+32],[-32,h+32]])
    pivots = np.array([[x,y] for x in [bounds[0]*ratio[0], bounds[2]*ratio[0]]
                       for y in [bounds[1]*ratio[1], bounds[3]*ratio[1]]])
    extents = np.vstack([(corners - layout['mapPosition'] - pivot) @ rotation.T + pivot for pivot in pivots]) / ratio
    lower = np.minimum(extents.min(axis=0), xy.min(axis=0) - 90/ratio)
    upper = np.maximum(extents.max(axis=0), xy.max(axis=0) + 90/ratio)
    # Portrait stacks move/scale the same layer under a taller scene. Keep a
    # generous geographic margin beyond the desktop coverage so a data boundary
    # cannot become a horizontal "coastline" beside the stacked controls.
    margin = np.array([w * 2, h * 3]) / ratio
    window = box(*(lower - margin), *(upper + margin))
    error = np.array([0.])
    if key == 'manhattan':
        project = manhattan_projector(data)
    else:
        smoothing = {'bremen':0.002, 'benelux':0.002, 'quebec':0.0008, 'northerneurope':0.001,
                     'korea':0.001, 'italy':0.0008, 'europe':0.001}.get(key,0.0002)
        project, error = projector(data['anchors'], smoothing)
    islandProjectors = {}
    if key == 'ukireland':
        for island in ['gb','ie']:
            islandProjectors[island], _ = projector([a for a in data['anchors'] if a['island']==island],0.004)
    invalid = 0
    def warp(geometry, active=False):
        nonlocal invalid
        fitted = []
        for polygon in polygons(geometry):
            if polygon.area < (0.00000001 if key == 'manhattan' else 0.0000001):continue
            c = polygon.centroid
            use = project
            island = None
            if key == 'ukireland' and c.y > 50 and c.x < 2:
                if polygon.area < 1:continue
                island = 'ie' if c.x < -6 else 'gb'
                use = islandProjectors[island]
            if key == 'manhattan' and active and polygon.area < 0.0002:continue
            span = max(polygon.bounds[2]-polygon.bounds[0],polygon.bounds[3]-polygon.bounds[1])
            def ring(coords):
                # Densify before warping curved fits, avoiding chord intersections.
                points = use(coords)
                if island == 'gb':
                    shore = np.interp(points[:,1],[200,280,320,360,420,470,510,550,600,660],
                                      [200,370,395,410,410,382,365,335,300,200],left=-10000,right=-10000)
                    west=points[:,0]<shore;points[west,0]=shore[west]+0.1*(points[west,0]-shore[west])
                return points
            dense=polygon.segmentize(max(span/300,0.0001))
            warped=Polygon(ring(dense.exterior.coords),[ring(r.coords) for r in dense.interiors])
            if not warped.is_valid:invalid+=1;warped=make_valid(warped)
            fitted.extend(polygons(warped))
        return unary_union(fitted).intersection(window)
    active=warp(shape(data['active']),True)
    context=warp(shape(data['context']))
    # Move generalized coastlines a few pixels outward to accommodate large
    # coastal city discs. Context includes the same correction: never blue land.
    active=active.buffer(clearance).intersection(window)
    context=unary_union([context,active])
    assert active.is_valid and context.is_valid and not active.is_empty,key
    outside=[{'city':c['name'],'distance':round(active.distance(Point(c['x'],c['y']))*max(ratio),1)} for c in allCities if not active.covers(Point(c['x'],c['y']))]
    assets={'name':data['name'],'land':path_string(active,tolerance),'context':path_string(context,tolerance*1.5),
            'cities':[[c['name'],c['x'],c['y']] for c in allCities]}
    report={'anchors':len(data['anchors']),'maxAnchorErrorPx':round(float(max(error))*max(ratio),1),
            'outside':outside,'repairedPolygons':invalid,'landPaths':len(assets['land'])}
    return assets,report

if __name__ == '__main__':
    output={};reports={}
    for key,data in SOURCE['maps'].items():
        output[key],reports[key]=build(key,data)
        print(key,json.dumps(reports[key]))
    target=HERE.parent.parent/'src/geography'
    target.mkdir(exist_ok=True)
    assets_dir = target/'assets'
    assets_dir.mkdir(exist_ok=True)
    for key, asset in output.items():
        (assets_dir/(key+'.json')).write_text(json.dumps(asset,separators=(',',':'),ensure_ascii=False)+'\n')
    (target/'names.json').write_text(json.dumps({asset['name']:key for key,asset in output.items()},separators=(',',':'),ensure_ascii=False)+'\n')
    # Literal imports work in both the browser build and the unit-test bundler.
    loaders = '// Generated by viewer/scripts/geography/build-outlines.py.\nexport const geographyLoaders = {\n'
    for key in output:
        loaders += f'    "{key}": () => import(/* webpackChunkName: "geography-{key}" */ "./assets/{key}.json"),\n'
    (target/'loaders.ts').write_text(loaders + '};\n')
    (HERE/'fit-report.json').write_text(json.dumps(reports,indent=2,ensure_ascii=False)+'\n')
    print('Runtime asset bytes', sum(path.stat().st_size for path in assets_dir.glob('*.json')))
