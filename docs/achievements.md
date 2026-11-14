# Power Grid achievements

Approved for engine **2.0.32** after independent review of `c8aae016`. No viewer or artwork changes are required. Publication verification is recorded in `docs/releases/achievements-2.0.32.json`.

## Contract

`engine/wrapper.ts` exports the optional `achievementDefinitions()` and `achievements(data)` hooks. Both use the published `@boardgamers/protocol@0.11.0` `/engine` types. The manifest has revision 1. IDs are stable game-local identifiers: do not rename or reuse them after publication. Future definition changes require a manifest revision bump. Icons are omitted, allowing platform fallback icons; no asset upload is needed.

The input is the deserialized, authoritative saved `GameState`, not a viewer payload or client-supplied achievement claim. Evaluation is pure, repeatable, and does not store counters or mutate state. Results use player-array indexes as seats. The hook returns nothing for unfinished, tentative, analysis/simulation, or fewer-than-two-player states. Power Grid has no standalone solo rules; a human against bots competes normally and receives an explicit win/loss outcome.

Final `citiesPowered` is the engine's official fuel-constrained, network-capped score, calculated after Building. There is no final plant-use round. Portfolio feats measure owned printed capacity, not generated electricity. Money is the final balance, including any map-specific end payouts.

Winning follows the existing three tie breakers: powered cities, money, built cities. Exact tied leaders are co-winners (`outcome: "win"`); all other eligible seats have `outcome: "loss"`. Bots and dropped players remain in the standings, but engine-known AI and dropped seats receive no results. Non-winning feats are independent of victory.

## Manifest

| ID                  | Name              | Condition at completion                                                      |
| ------------------- | ----------------- | ---------------------------------------------------------------------------- |
| `grid-champion`     | Grid Champion     | Win (including shared first place).                                          |
| `head-to-head`      | Head to Head      | Win with two seats.                                                          |
| `full-table`        | Full Table        | Win with six seats.                                                          |
| `germany-champion`  | Germany Champion  | Win on Germany.                                                              |
| `usa-champion`      | USA Champion      | Win on USA.                                                                  |
| `france-champion`   | France Champion   | Win on France.                                                               |
| `japan-champion`    | Japan Champion    | Win on Japan.                                                                |
| `power-fifteen`     | Power Fifteen     | Able to power at least 15 owned cities.                                      |
| `power-eighteen`    | Power Eighteen    | Able to power at least 18 owned cities.                                      |
| `fully-supplied`    | Fully Supplied    | Able to power every owned city, with at least 10 owned.                      |
| `network-seventeen` | Network Seventeen | Own at least 17 cities.                                                      |
| `network-twenty`    | Network Twenty    | Own at least 20 cities.                                                      |
| `cash-reserve`      | Cash Reserve      | At least 100 Elektro.                                                        |
| `deep-reserves`     | Deep Reserves     | At least 200 Elektro.                                                        |
| `wind-farm`         | Wind Farm         | Owned Wind plants total at least 8 printed capacity.                         |
| `atomic-power`      | Atomic Power      | Owned Uranium plants total at least 8 printed capacity, excluding Australia. |

`PowerPlantType.Nuclear` means fuel-free fusion in this engine and does not count as wind or uranium-fuelled capacity. On Australia, Uranium plants are mines, not generators. Conditions use types/output rather than card numbers so alternate and shuffled decks work too. Map feats use the resolved `data.map.name`, including games created with Random map selection.

## Server eligibility boundary

Power Grid state contains neither platform account identities nor cancellation metadata. The existing BGS achievement capture/adjudication path must remain enabled: it captures first natural completion only, rejects cancelled/claimed-win/edited-solo games, and excludes platform bot/dropped/quit seats before persisting human awards. In particular, BGS does **not** propagate `isBot` into Power Grid's `isAI`; `isAI === false` alone is not proof of a human account. Do not call these hooks directly to persist user awards outside that server path. Host-side evidence and award deduplication remain authoritative.

Analysis constructors and moves mark their copies with `achievementAnalysis: true`; full wrapper replay preserves this exclusion. Older analyses may not have the marker, so the host's analysis isolation is still required. Ordinary historical replay is a pure engine operation, not permission to backfill achievements.

## Review verification

-   Full engine suite: **625 passing**, including **50 achievement tests**.
-   Engine build and published protocol 0.11.0 manifest/result schema validation: passed.
-   Engine lint: passed with existing warning-level findings, no errors.
-   Viewer unit suite: **102 passing**.
-   Viewer production package and bundle-size check: passed (`NODE_OPTIONS=--openssl-legacy-provider pnpm --filter powergrid-viewer package`).
-   Frozen pnpm installation, changed-file formatting, and whitespace checks: passed.
-   A read-only review confirmed the win rules and that the capacity/network thresholds are reachable with actual plants and house limits.

An earlier full engine run concurrent with builds hit two 2-second replay-test timeouts; the final full run passed with the normal timeout. Viewer tests were also rerun successfully after an overlapping engine clean/build temporarily removed their imports. No gameplay assertions were relaxed.

## Validation and release prerequisites

-   Run `pnpm install --frozen-lockfile`, `pnpm --filter powergrid-engine test`, and `pnpm --filter powergrid-engine test:achievements` (builds and validates the compiled hooks with the published protocol's runtime schemas).
-   Engine TypeScript is pinned to the 4.9 minor line to resolve the protocol's CommonJS `.d.cts` declarations while retaining compatibility with the existing ESLint parser and Node type declarations. The legacy npm lockfile is already stale; pnpm and `engine/pnpm-lock.yaml` are authoritative.
-   Review all 16 IDs/descriptions, thresholds, tie semantics, and human-versus-bot policy with the coordinator.
-   Validate the compiled hooks against protocol manifest/result schemas and the actual BGS install/adjudication path before release, including cancellation, bot/account filtering, duplicate completion, and edited-solo exclusions. Unit tests cannot substitute for server-owned eligibility checks.
-   After approval, allocate an engine release version, fetch/integrate the latest canonical release, rerun relevant checks, and publish through the existing engine release workflow. Verify the installed artifact contains both hooks and the expected manifest revision. No artwork is required.
-   Only when authorized to publish: follow AGENTS.md's corresponding source/lockfile/version commit, canonical release-branch push, public mirror update, and remote-delivery verification requirements. The approved 2.0.32 delivery follows that workflow; consult its release receipt for the installed artifact and verification results.
