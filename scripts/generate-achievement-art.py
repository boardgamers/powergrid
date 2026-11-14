#!/usr/bin/env python3
"""Offline achievement exports. Requires CairoSVG 2.9.1, Pillow 13.0.0, Shapely 2.1.2."""
import hashlib
import json
import math
import runpy
from pathlib import Path
import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'art/achievements'
OUT.mkdir(parents=True, exist_ok=True)
GOLD, INK, BLUE, WHITE = '#ffcf66', '#102b3b', '#65d4d1', '#f4f5de'
BASE = json.loads((ROOT / 'docs/releases/achievements-2.0.33.json').read_text())['achievementManifest']
FRAMING = runpy.run_path(str(ROOT / 'scripts/achievement-map-framing.py'))
MAPS = dict(zip([d['id'] for d in BASE['achievements'][3:27]], ['germany','america','france','japan','brazil','spainportugal','indian','italy','quebec','middleeast','china','benelux','russia','centraleurope','badenwurttemberg','northerneurope','korea','europe','northamerica','southafrica','ukireland','australia','bremen','manhattan']))
def path(d, fill=BLUE, stroke=INK, width=2):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
def line(a,b,color=BLUE,width=3):
    return path(f'M{a[0]},{a[1]} L{b[0]},{b[1]}','none',color,width)
def house(x,y,s=1,lit=False):
    return f'<g transform="translate({x} {y}) scale({s})">'+path('M-8,0 L0,-8 L8,0 V10 H-8 Z',GOLD if lit else WHITE)+path('M-2,3 H2 V10 H-2 Z',INK,'none')+'</g>'
def crown(x=64,y=24):
    return f'<g transform="translate({x} {y})">'+path('M-15,-5 L-9,2 L0,-9 L9,2 L15,-5 L11,10 H-11 Z',GOLD)+'</g>'
def label(t):
    return f'<rect x="42" y="91" width="44" height="20" rx="7" fill="{INK}"/><text x="64" y="106" text-anchor="middle" font-family="DejaVu Sans" font-size="16" font-weight="bold" fill="{GOLD}">{t}</text>'
def bolt(x,y,s=1):
    return f'<g transform="translate({x} {y}) scale({s})">'+path('M2,-15 L-10,3 H-1 L-4,15 L11,-5 H2 Z',GOLD)+'</g>'
def turbine(x,y,s=1):
    return f'<g transform="translate({x} {y}) scale({s})">'+line((0,0),(0,32),WHITE,3)+''.join(line((0,0),(18*math.cos(a),18*math.sin(a)),WHITE,4) for a in [-math.pi/2,math.pi/6,5*math.pi/6])+f'<circle r="4" fill="{GOLD}"/></g>'
def plant(x,y):
    return f'<g transform="translate({x} {y})">'+path('M-16,12 V-7 L-5,-2 V-9 L7,-2 V-17 H15 V12 Z',WHITE)+bolt(0,0,.55)+'</g>'
def notes(x,y):
    return f'<g transform="translate({x} {y})">'+path('M-24,-13 H24 V13 H-24 Z',BLUE)+path('M-18,-7 H18 V7 H-18 Z','none',INK,1.5)+bolt(0,0,.65)+'</g>'
def motif(id):
    if id in MAPS:
        paths, _ = FRAMING['framed_map'](MAPS[id])
        body=''.join(path(d,BLUE,WHITE,1.25) for d in paths)
        return body+crown(64,21), FRAMING['SOURCE']
    if id=='grid-champion':
        return crown()+path('M64,38 L46,91 M64,38 L82,91 M49,58 H79 M44,73 H84 M55,62 L75,84 M73,62 L53,84','none',BLUE,4)+house(33,85,.8,True)+house(95,85,.8,True),None
    if id=='head-to-head':
        return crown()+line((35,67),(93,67),BLUE,5)+house(35,64,1.5,True)+house(93,64,1.5)+bolt(64,87,.65),None
    if id=='full-table':
        points=[(64+35*math.cos(a*math.pi/3),65+33*math.sin(a*math.pi/3)) for a in range(6)]
        return ''.join(line(points[i],points[(i+1)%6]) for i in range(6))+''.join(house(x,y,.83,i==4) for i,(x,y) in enumerate(points))+crown(64,61),None
    if id.startswith('power-') or id=='fully-supplied':
        n=3 if id=='power-fifteen' else 4
        points=[(29+i*70/(n-1),77) for i in range(n)]
        body=plant(64,44)+''.join(line((64,57),(x,y),GOLD,3)+house(x,y,.8,True) for x,y in points)
        if id=='power-eighteen':
            body=plant(43,40)+plant(85,40)+''.join(line((43 if i<2 else 85,53),(x,y),GOLD,3)+house(x,y,.8,True) for i,(x,y) in enumerate(points))
        if id=='fully-supplied': body=path('M25,39 A45,45 0 1 0 103,39','none',BLUE,5)+body
        return body+label({'power-fifteen':'15','power-eighteen':'18','fully-supplied':'15+'}[id]),None
    if id.startswith('network-'):
        pts=[(35,43),(77,39),(94,67),(65,79),(30,76)]
        edges=[(0,1),(1,2),(1,3),(3,4)]
        if id=='network-twenty': pts.extend([(61,57),(92,94)]); edges.extend([(0,5),(5,2),(4,5),(3,6),(2,6)])
        return ''.join(line(pts[a],pts[b]) for a,b in edges)+''.join(house(x,y,.7) for x,y in pts)+label('17' if id.endswith('seventeen') else '20'),None
    if id=='cash-reserve': return notes(64,62)+house(64,39,.8)+label('100'),None
    if id=='deep-reserves': return path('M28,32 H89 V89 H28 Z',WHITE)+path('M89,32 L105,43 V96 L89,89 Z',BLUE)+notes(60,56)+notes(60,75)+label('200'),None
    if id=='wind-farm': return turbine(39,51,.8)+turbine(76,38,1)+line((39,79),(87,79))+house(89,78,.8,True)+label('8+'),None
    if id=='atomic-power': return path('M24,39 H41 V63 H24 Z',BLUE)+f'<text x="32" y="56" text-anchor="middle" font-size="15" font-family="DejaVu Sans" font-weight="bold" fill="{INK}">U</text>'+line((42,52),(56,52),GOLD)+plant(75,49)+line((75,62),(75,74),GOLD)+house(75,78,.8,True)+label('8+'),None
    raise ValueError(id)

manifest=[]
for definition in BASE['achievements']:
    id=definition['id']; body,source=motif(id); key='achievement-'+id
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 128 128"><circle cx="64" cy="64" r="61" fill="{INK}" stroke="{GOLD}" stroke-width="3"/>{body}</svg>'
    (OUT/(key+'.svg')).write_text(svg+'\n')
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/(key+'.png')))
    manifest.append(dict(id=id,key=key,svg=key+'.svg',png=key+'.png',sha256=hashlib.sha256((OUT/(key+'.png')).read_bytes()).hexdigest(),source=source,sourceSha256=hashlib.sha256((ROOT/source).read_bytes()).hexdigest() if source else None))
for item in manifest:
    if item['id'] in MAPS:
        item['map'] = MAPS[item['id']]
        item['framing'] = FRAMING['framed_map'](item['map'])[1]
(OUT/'manifest.json').write_text(json.dumps(dict(game='powergrid',engine='2.0.34',revision=3,provenance='PROVENANCE.md',framingSha256=hashlib.sha256((ROOT/'scripts/achievement-map-framing.py').read_bytes()).hexdigest(),generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),assets=manifest),indent=2)+'\n')
# Actual raster exports composited at display sizes, not enlarged SVG screenshots.
for size in [32,48,64]:
    sheet=Image.new('RGB',(960,6*(size+55)*2),'#eef1f3'); draw=ImageDraw.Draw(sheet)
    for i,item in enumerate(manifest):
        col,row=i%6,i//6
        for theme,bg in enumerate(['#eef1f3',INK]):
            x,y=col*160,(theme*6+row)*(size+55)
            draw.rectangle((x,y,x+159,y+size+54),fill=bg)
            im=Image.open(OUT/item['png']).resize((size,size),Image.Resampling.LANCZOS)
            sheet.paste(im,(x+(160-size)//2,y+4),im)
            text=item['id'].replace('-champion','').replace('-','\n',1)
            draw.multiline_text((x+6,y+size+8),text,fill=INK if theme==0 else WHITE)
    sheet.save(OUT/f'contact-{size}.png')
print(f'Generated {len(manifest)} assets and 32/48/64px light/dark contact sheets.')
