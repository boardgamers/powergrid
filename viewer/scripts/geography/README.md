# Geographic outline exploration

Local preview only. No production viewer, rules, city coordinates, links, or BGS
assets changed. Germany and UK/Ireland are the first two examples.

From the repository root, after building the engine and viewer normally:

```sh
node viewer/scripts/geographic-preview.mjs
```

Open <http://127.0.0.1:5209/>. Compare soft land + outline, outline only, and off.
The map selector, all/selected regions, full-board view, and light/dark page theme
are local preview controls, not proposed additions to the game's toolbar. All
regions is an illustrative display using the authored full map; selected regions
uses a real seeded three-player setup. The preview has no move endpoint.

The preview uses the existing built viewer to draw the network. Its map-only
view copies that SVG; the full-board view places the background behind all game
UI, so the income track and controls stay on top. No external assets or GIS
libraries are downloaded by the browser. The generated path data is ~7 KB.

## Data and fitting

[Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) is public
domain. `natural-earth-source.json` contains a small subset of its 1:50m country
outlines and 1:10m populated-place coordinates. Exact upstream URLs, Git revision
and full-file hashes are recorded in that file. No copyrighted board image was
used. The input subset and generated output are checked in for offline use.

`build-outlines.py` requires NumPy and Shapely 2.x, **for asset generation only**:

```sh
python3 viewer/scripts/geography/build-outlines.py
```

The generator fits thin-plate splines using 33 city anchors for Germany and 32
for UK/Ireland. It warps geography to the existing board, never the other way
around. England's duplicate London nodes share one geographic location; only
London 1 is used as an anchor. Britain and Ireland are fitted independently.
Small offshore islands and distant territories are omitted. Country polygons
are merged into the two islands, so the background does not introduce internal
political/game-region boundaries. The land receives ten board units of clearance
for the large city discs and generalized coastline, then is simplified.

The schematic UK map leaves too little sea for a literal coastline. Its western
Scottish coast therefore has an explicit, editable clearance envelope in the
generator. That preserves the visible sea gap without moving any cities. This
is a geographic backdrop fitted for gameplay, not a geospatially exact map.

Generation checks valid polygons, two separate UK/Ireland islands and a sea gap
above 12 board units. All 65 matched city-anchor centres are covered by the land. A separate check
confirmed that all 82 authored city centres (including unmatched cities) are
inside the generated outlines.
The first prototype was also checked against the source maps: all displayed city
coordinates and connection data are unchanged, for both full and selected views.

## Before production or expanding the map list

- Get visual feedback on the soft fill versus outline-only treatment.
- Add each map deliberately with suitable landmarks; a single global bounding-box
  stretch is not sufficient for the schematic layouts, islands and rotations.
- Move approved paths into a viewer-native SVG background layer. Keep it beneath
  UI and out of pointer hit testing, account for map rotation/adjustRatio and
  stacked portrait measurements, and test historical states and region drafts.
- Decide how much unused geography to show when only some regions are in play.
  This prototype retains the whole country/islands for orientation.
- Audit edge clipping in authored full-board layouts. UK/Ireland and Germany
  currently have little spare board space; map-only view includes complete bounds.

No publication has been performed.
