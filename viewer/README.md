# powergrid-viewer

## Project setup

```
yarn install
```

### Compiles and hot-reloads for development

```
yarn serve
```

### Compiles and minifies for production

```
yarn build
```

### Run your unit tests

```
yarn test:unit
```

### Lints and fixes files

```
yarn lint
```

### Customize configuration

See [Configuration Reference](https://cli.vuejs.org/config/).

## Playable tutorials

Seven independent chapters cover auctions, fuel, connections, income, plant replacement, Steps 2/3 and final scoring. They use Germany with classic rules, deterministic positions and scripted opponents. Actions go through the real engine; only the learner's filtered state reaches the board.

From the repository root:

```sh
pnpm --dir engine build
pnpm --dir viewer test:tutorial
NODE_OPTIONS=--openssl-legacy-provider pnpm --dir viewer package
pnpm --dir viewer test:tutorial:browser
pnpm --dir viewer preview:tutorial
```

Open <http://127.0.0.1:5199/?chapter=auctions>. Other chapter IDs are `resources`, `network`, `income`, `upgrades`, `steps` and `final-round`.

The ordinary viewer bundle exposes both `powergrid.launch` and `powergrid.launchTutorial`. Upload the entry JS, CSS and all `.umd.min.locale-*.js` chunks and configure the tutorial chapters on the same BGS game version. `pnpm --dir viewer tutorial:manifest` prints the chapter metadata. No second bundle or engine release is required.

Lessons live in `src/tutorial/lessons.ts`. Keep their IDs stable and increase a chapter's version when changing its setup or accepted actions would invalidate saved progress. Test normal board clicks, refresh, rewind and completion on desktop and mobile before release.

See the [desktop and mobile screenshots](docs/tutorials/README.md) for examples of the tutorial UI.

## Undo against bots

When the only human of a game plays against bots, BGS can take back their last saved move (protocol 0.10.0 `undo:available` / `undo`). The board's Undo button then becomes "Undo my move" once the turn in progress has nothing left to undo locally. It stays hidden during replays, analyses and round planning, for spectators, and while a move is on its way. BGS answers with the earlier state, and the viewer drops the turn buffer, open dialogs and the bid being dialled. The development sandbox (`npm run serve`) offers the same undo against its bots.

## Shared accessibility preference

The viewer accepts BGS's `colorBlind` boolean preference (default `false`). The eye button on the board changes it through `update:preference`, so BGS saves the setting across games. It also works locally in tutorials.

When enabled, houses on the map, turn-order track and city-count track carry their owner's seat number. Player panels use the same number, regardless of turn order or selected color. City rims use contrasting dash and dot patterns to distinguish map regions without extra labels. Each region keeps its pattern after region selection. Resources already use different shapes.

### Local phase auto-pass preview (no BGS connection)

From the repository root, build the engine and viewer, then start the preview:

```sh
pnpm --dir engine build
NODE_OPTIONS=--openssl-legacy-provider pnpm --dir viewer exec vue-cli-service build --target lib --name powergrid-viewer src/wrapper.ts
node viewer/scripts/auction-preview.mjs
```

Open <http://127.0.0.1:5216/?mode=fuel-hidden> (or `?mode=city-hidden`).
The scenario selector also offers public-money versions and an empty oil market.
Toggle the checkbox in **your** player card, then click Ada's action in the top
bar. Ada takes the last affordable oil/city and finishes via the real engine
wrapper. Hidden money without opt-in retains your turn; opt-in or public money
skips it. An empty oil market skips even with hidden money and opt-in disabled,
because the impossibility is public. Reset before comparing scenarios.
Preferences persist through the wrapper's private player-settings API; no
client-side auto-pass simulation is used. Preview state is held in memory only.

Run the eight browser scenarios after building:

```sh
node viewer/scripts/phase-auto-pass-smoke.mjs
node viewer/scripts/auto-pass-label-smoke.mjs
```

The label smoke checks all 17 languages at 390px and 1400px, switching phases
and locales live and checking left alignment, checkbox clearance and row bounds.
To verify a published viewer, set `POWERGRID_VIEWER_URL` to its public
`powergrid-viewer.umd.min.js` URL when running either smoke. Only viewer assets
are fetched from the CDN; game state, moves and settings remain local in memory.
