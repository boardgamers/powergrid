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
