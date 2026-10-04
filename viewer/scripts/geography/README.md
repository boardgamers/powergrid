# Geographic backgrounds

The viewer-native background covers all 24 authored maps. Development history is
on `codex/geographic-outlines-preview`; the release is included in viewer 2.2.0.
Full-board preview URLs can include `&view=full`.

Build the engine and viewer, then start the local preview:

```sh
pnpm --dir engine build
NODE_OPTIONS=--openssl-legacy-provider pnpm --dir viewer package
node viewer/scripts/geographic-preview.mjs
```

Open <http://127.0.0.1:5209/?map=ukireland&style=terrain&regions=selected>.
The map/rules selectors, backdrop treatments, all/selected regions, full-board
view and page theme are local preview controls, not new game toolbar controls.
Full-region view is illustrative; selected regions uses a seeded three-player
setup. There is no move endpoint. `/gallery?page=0` through `3` provide a compact
review of all generated assets with the authored city network.

The default treatment uses muted blue water, darker green neighbouring land,
and lighter green land belonging to the named map. `wash`, `line` and `none`
remain available through the viewer's `geographicBackground` preference for
comparison. Different game regions retain their original city colours.

## Unchanged framing and gameplay

`GeographicBackground.vue` is a decorative sibling **outside** the measured
`slotMap` group. It receives the exact same position, rotation and portrait slot
transform as the network. The full board draws the larger geographic area behind
the controls and is
cropped only by the original root SVG viewport. No geography contributes to
layout measurements. Map-only preview keeps its original network clip plus 24
units of decorative padding.

- Desktop retains the authored `map.viewBox`.
- Portrait keeps measuring the original city/network SVG, so selected regions
  retain the previous framing and zoom behaviour.
- Map-only preview measures that same network before copying any background;
  geography does not expand its viewBox either.
- The background has no pointer hit testing and does not change city positions,
  connections, rules, move legality or region selection.
- Unknown layouts and randomized city coordinates receive no geographic layer.
  Recognition checks authored city names and scaled coordinates, allowing region
  subsets and the Original/Recharged variants.

## Sources and attribution

`source.json` is the curated offline generator input. It records source URLs,
SHA-256 hashes, downloaded dates where appropriate, geographic geometries,
GeoNames landmark IDs and raw authored board coordinates. The initial Germany
and UK/Ireland Natural Earth landmark inputs remain in
`natural-earth-source.json`; the initial two-map output `outlines.json` is
historical and is no longer loaded by the preview or viewer.

- [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/), public
  domain: 1:50m country boundaries and lakes; 1:10m populated places and province
  boundaries. Git revision `ca96624a56bd078437bca8184e78163e5039ad19`.
- [GeoNames](https://www.geonames.org/),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): city coordinates
  from `cities500.zip` and Bremen districts from `DE.zip` (2026-10-04).
- [NYC Open Data Borough Boundaries 26b](https://data.cityofnewyork.us/d/gthc-hcne):
  Manhattan and neighbouring borough geometries, under NYC Open Data terms.

These data have been cropped, merged, warped to the schematic game boards,
buffered and simplified. The browser receives SVG paths only, in a separately
loaded chunk for the current map;
it downloads no GIS library or external geographic data. If the optional chunk
fails, the playable board retains its original green surface. Include all
generated geography chunks
alongside locale chunks when eventually publishing (see
`docs/viewer-publishing.md`). Credits also accompany the SVG layer
and the local preview. No board-game artwork was traced or copied.

## Regenerating the assets

Python, NumPy and Shapely >= 2 are **asset generation dependencies only**:

```sh
python3 viewer/scripts/geography/build-outlines.py
```

The script writes `viewer/src/geography/assets/*.json`, `names.json`,
`loaders.ts` and `fit-report.json`.
Thin-plate splines fit geographic city anchors to the unchanged board positions.
Country unions preserve outer coastlines without adding internal political or
game-region divisions. Bremen, Baden-Württemberg and Quebec use provincial
boundaries. Lakes are retained where the source geometry and simplification
allow them. Land is slightly expanded around coastal cities, then simplified to
about 1.7 board pixels. Integer raw coordinates add at most 0.875 board pixels
of rounding error. Only the current map is downloaded: about 1–45 KB gzip
depending on the map
(Australia 16 KB, USA 34 KB). The initial viewer entry remains below its existing
byte limits. Neighbouring geographic data extends well beyond the city network;
country/province shapes are not cropped at the old network rectangle. The
export window includes the entire authored board for every possible rotation
pivot within the selected-city envelope, with an additional margin for the much
taller portrait layout.

Special schematic fits:

- Britain and Ireland are fitted independently. A western Scotland clearance
  envelope preserves a sea gap despite the compressed board layout.
- Manhattan's anonymous M1–M83 spaces cannot be geocoded. Its real coastline is
  aligned with the island's long axis and fitted to the grid envelope. The
  northern edge continues beyond the viewport; it is not an invented coast.
- Duplicate Paris/London/Melbourne spaces and expanded Montreal suburbs make
  exact geographic correspondence impossible. This is a gameplay backdrop,
  not an accurate geographic projection.
- Foreign-country spaces on South Africa and transregional cities on
  Baden-Württemberg intentionally fall outside the lighter active area.

`fit-report.json` records anchor errors, polygon repairs and city centres outside
active land. Outside entries include legitimate neighbouring territories and a
few generalized coastal edge cases; they do not alter gameplay.

## Verification

The viewer unit suite covers every authored map in both editions, real region
subsets with three and four players, and fallback for unknown/random layouts.
The standard viewer package build enforces the existing entry-point and gzip
size limits. All 24 asset fits have been visually reviewed. Native desktop and
portrait comparisons check that background on/off leaves the network bounds,
slot transforms, rendered city positions and root viewBox unchanged. The 96
comparisons (24 maps × 2 region modes × 2 viewport sizes) are recorded in
`viewport-checks.json`; all passed for the initial clipped preview. The continuous
background is still outside all measured slots; follow-up native checks cover
cold loading, desktop/portrait framing, rotated maps and Australia’s mine-panel
clearance. Results for 24 follow-up comparisons are in `extended-checks.json`.
The viewer unit suite has 39 passing tests.

Australia's desktop uranium mine market begins at y=112, below the income track
and legend; its portrait row still uses the existing stacked layout. This is a
control-spacing fix and does not move or resize the playable network.
