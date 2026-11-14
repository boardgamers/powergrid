# Power Grid achievement artwork

Issue: https://codeberg.org/boardgamers/boardgamers/issues/595

The 36 compositions are original geometric drawings in
`scripts/generate-achievement-art.py`, licensed under the repository's MIT
license. No publisher illustrations, photographs, logos or commercial board
artwork were copied. SVG exports are editable vector originals. PNGs are 256px
transparent circular badges. Numerals supplement structure, not replace it.

## Geographic inputs (24 badges)

Each map badge uses **all land paths** from its named
`viewer/src/geography/assets/*.json`, uniformly fitted without merging islands.
Context/foreign land is intentionally excluded. Four representative city anchors
are chosen deterministically from actual geography coordinates; joining strokes
are illustrative electrical connections, not claims about a playable route.
Source filenames and SHA-256 are individually recorded in `manifest.json`.

These existing game-map geographic datasets are derived from:

-   Natural Earth, public domain, https://www.naturalearthdata.com/about/terms-of-use/
    (country/province boundaries; upstream revision
    `ca96624a56bd078437bca8184e78163e5039ad19`).
-   GeoNames, https://www.geonames.org/, CC BY 4.0,
    https://creativecommons.org/licenses/by/4.0/ (city anchors and Bremen districts).
-   NYC Open Data Borough Boundaries 26b,
    https://data.cityofnewyork.us/d/gthc-hcne (Manhattan), NYC Open Data terms.

Full upstream source URLs, hashes and transformations remain in
`viewer/scripts/geography/source.json` and its README. Existing geographic
inputs were cropped, warped and simplified to authored board coordinates;
these badges additionally scale them uniformly. Geographic shapes are schematic
map footprints, not authoritative political boundaries. Attribution accompanies
all distributed sources and asset exports in this document.

## Reproduction and review

Use Python 3.12 with CairoSVG 2.9.1 and Pillow 13.0.0, system Cairo and DejaVu Sans:

```sh
python scripts/generate-achievement-art.py
python scripts/check-achievement-art.py
```

`manifest.json` lists exact PNG hashes and stable asset keys. `contact-32.png`,
`contact-48.png` and `contact-64.png` composite the actual exported rasters at
native display sizes on both light and dark backgrounds. These are review
artifacts, not enlarged SVG mockups. No service or database is needed.

Capacity feats show a generating plant feeding lit houses; network feats use
unlit owned houses and no generator. The full table contains exactly six house
pieces; head-to-head exactly two. Money uses original Elektro lightning-note
geometry, not reproductions of printed currency. Wind and uranium depict
plant output, not fuel inventories or Australian uranium mines. Numeric values
are thresholds; illustrative neighborhoods do not assert exact city counts.
