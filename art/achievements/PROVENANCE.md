# Power Grid achievement artwork

Issue: https://codeberg.org/boardgamers/boardgamers/issues/595

The 36 compositions are original geometric drawings in
`scripts/generate-achievement-art.py`, licensed under the repository's MIT
license. No publisher illustrations, photographs, logos or commercial board
artwork were copied. SVG exports are editable vector originals. PNGs are 256px
transparent circular badges. Numerals supplement structure, not replace it.

## Geographic inputs (24 badges)

The 24 badges use the **unwarped geographic `active` geometry** in
`viewer/scripts/geography/source.json`, rather than the viewer's city-fitted
board paths. The latter can distort or join islands and include distant land
outside the gameplay viewport. Viewer sources and gameplay are unchanged.

`scripts/achievement-map-framing.py` explicitly defines each map's main-region
longitude/latitude window. Geometry is intersected with that window, projected
locally (longitude × cosine of mid-latitude, north up), and components smaller
than 0.3% of the largest selected polygon are omitted **before** fitting.
Remaining components share one uniform fit into a 90×78 box centred at (64,70).
No arbitrary outline is substituted; no island is moved or merged. Remote
components are deliberately omitted, not invisibly allowed to shrink the badge.
Coasts are topology-preserving simplified by 0.45 badge units (0.1125px at 32px).
Interior holes/lakes are filled; tiny islets and city/connection overlays are
omitted so the principal silhouette stays readable. The crown means map win.

The exact window, component count, principal span and simplification policy are
recorded per badge in `manifest.json`; it hashes the source and framing code.
The component count is after the documented window and small-islet filtering.

| Map | Main-region selection / deliberate omissions | Components |
| --- | --- | --- |
| germany | Germany mainland; omit subpixel coastal islets. | 2 |
| america | Contiguous USA; omit Alaska, Hawaii and overseas islands. | 1 |
| france | Metropolitan France including Corsica; omit overseas departments. | 2 |
| japan | Four main islands in true geographic positions; omit remote Ryukyu/Bonin chain. | 5 |
| brazil | Continental Brazil; omit subpixel offshore islands. | 2 |
| spainportugal | Iberian mainland and Balearics; omit Azores, Madeira and Canaries. | 2 |
| indian | Indian mainland; omit Andaman/Nicobar and Lakshadweep islets. | 1 |
| italy | Peninsula, Sicily and Sardinia; omit subpixel islets. | 3 |
| quebec | Whole Quebec mainland, not just the southern city corridor. | 3 |
| middleeast | Authored Middle East country union; omit distant/subpixel islands. | 1 |
| china | Mainland and Hainan from curated active geometry. | 2 |
| benelux | Belgium, Netherlands and Luxembourg union; omit subpixel islets. | 2 |
| russia | Russian mainland to Bering Strait; omit dateline fragments and Arctic archipelagos below size cutoff. | 4 |
| centraleurope | Complete authored Central Europe country union. | 1 |
| badenwurttemberg | Complete Baden-Wuerttemberg provincial outline. | 1 |
| northerneurope | Scandinavian/Baltic mainland and major Danish islands; omit Svalbard and remote Arctic islands. | 5 |
| korea | Korean peninsula and Jeju; omit subpixel islets. | 2 |
| europe | European mainland to 45E plus Britain/Ireland and major Mediterranean islands; omit overseas territories and remote Arctic islands. | 4 |
| northamerica | Continental North America including Alaska, Canada and Mexico; omit Hawaii and far Arctic islands. | 7 |
| southafrica | South African mainland; omit remote Prince Edward islands. | 1 |
| ukireland | Great Britain and Ireland, with larger coastal islands. | 6 |
| australia | Australian mainland and Tasmania; omit external Indian/Pacific Ocean territories. | 2 |
| bremen | Bremen city component; omit detached Bremerhaven to preserve city silhouette. | 1 |
| manhattan | Manhattan main island; omit tiny detached borough islets. | 5 |

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
the badges instead use the curated pre-warp geographic geometry. Geographic shapes are schematic
map footprints, not authoritative political boundaries. Attribution accompanies
all distributed sources and asset exports in this document.

## Reproduction and review

Use Python 3.12 with CairoSVG 2.9.1 and Pillow 13.0.0 and Shapely 2.1.2, system Cairo and DejaVu Sans:

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
