# Power Grid achievements

**Unpublished review candidate: engine 2.0.33, manifest revision 2, 36 achievements.** Adds 20 map victories (24 total) and raises Fully Supplied from a 10-city to a 15-city minimum, preserving its complete-network condition. The separate powered-city tiers remain 15 and 18. No viewer, artwork, map-cap, scoring, or backfill changes. Existing awards are not recalculated or revoked by this change.

The live 2.0.32 / revision-1 release remains documented in `docs/releases/achievements-2.0.32.json`. Do not publish this candidate until coordinator review.

## Contract

`engine/wrapper.ts` exports the optional `achievementDefinitions()` and `achievements(data)` hooks. Both use the published `@boardgamers/protocol@0.11.0` `/engine` types. The candidate manifest has revision 2. IDs are stable game-local identifiers: do not rename or reuse them after publication. Future definition changes require a manifest revision bump. Icons are omitted, allowing platform fallback icons; no asset upload is needed.

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
| `fully-supplied`    | Fully Supplied    | Able to power every owned city, with at least 15 owned.                      |
| `network-seventeen` | Network Seventeen | Own at least 17 cities.                                                      |
| `network-twenty`    | Network Twenty    | Own at least 20 cities.                                                      |
| `cash-reserve`      | Cash Reserve      | At least 100 Elektro.                                                        |
| `deep-reserves`     | Deep Reserves     | At least 200 Elektro.                                                        |
| `wind-farm`         | Wind Farm         | Owned Wind plants total at least 8 printed capacity.                         |
| `atomic-power`      | Atomic Power      | Owned Uranium plants total at least 8 printed capacity, excluding Australia. |

`PowerPlantType.Nuclear` means fuel-free fusion in this engine and does not count as wind or uranium-fuelled capacity. On Australia, Uranium plants are mines, not generators. Conditions use types/output rather than card numbers so alternate and shuffled decks work too. Map feats use the resolved `data.map.name`, including games created with Random map selection.

### Complete map-win catalog

Each entry is **Win on the named map**, including shared first place, never mere participation. The 24-name set matches both runtime `maps` and `mapsRecharged`, including expansion maps. Existing Germany, USA, France and Japan IDs and descriptions are unchanged.

| Canonical map name | Stable achievement ID        |
| ------------------ | ---------------------------- |
| USA                | `usa-champion`               |
| Germany            | `germany-champion`           |
| Brazil             | `brazil-champion`            |
| Spain & Portugal   | `spain-portugal-champion`    |
| France             | `france-champion`            |
| India              | `india-champion`             |
| Italy              | `italy-champion`             |
| Quebec             | `quebec-champion`            |
| Middle East        | `middle-east-champion`       |
| China              | `china-champion`             |
| Benelux            | `benelux-champion`           |
| Russia             | `russia-champion`            |
| Central Europe     | `central-europe-champion`    |
| Baden-Württemberg  | `baden-wurttemberg-champion` |
| Northern Europe    | `northern-europe-champion`   |
| Korea              | `korea-champion`             |
| Europe             | `europe-champion`            |
| North America      | `north-america-champion`     |
| South Africa       | `south-africa-champion`      |
| UK & Ireland       | `uk-ireland-champion`        |
| Australia          | `australia-champion`         |
| Bremen             | `bremen-champion`            |
| Manhattan          | `manhattan-champion`         |
| Japan              | `japan-champion`             |

Names are matched exactly against resolved `data.map.name`; `options.map` is not consulted. Random selection therefore earns the resolved map badge. Original and Recharged share an ID, as do deck/region variants on the same named map. USA is not an alias for North America. Internal module names such as `america`/`indian`, translations, accent-stripped names, and unsupported names are not accepted map aliases. Explicit ASCII IDs omit ampersands and transliterate ü to u, without runtime slug generation.

### Powered-city target rationale

Most maps end when a player builds 21/17/17/15/14 cities at 2/3/4/5/6 players, not when anyone powers that many. South Africa and Manhattan use 18 at two players. Bremen uses 13/13/13/12/11; its two-/three-player map has only 15 cities. UK & Ireland caps the two-player ending target to available map cities. Stalled games can end below these triggers. Legal building stops at 21 owned cities (`buildOptions`), despite the legacy `housesLeft: 22` initialization.

Thus the 15/18 powered ladder remains meaningful without a near-ceiling 20 target. Fully Supplied at 15 is stricter than Power Fifteen: all owned cities must be powerable. Some small maps cannot award the upper tier; the game/map limits remain untouched. Every powered predicate uses official fuel-constrained, network-capped final `citiesPowered`, not plant capacity.

## Server eligibility boundary

Power Grid state contains neither platform account identities nor cancellation metadata. The existing BGS achievement capture/adjudication path must remain enabled: it captures first natural completion only, rejects cancelled/claimed-win/edited-solo games, and excludes platform bot/dropped/quit seats before persisting human awards. In particular, BGS does **not** propagate `isBot` into Power Grid's `isAI`; `isAI === false` alone is not proof of a human account. Do not call these hooks directly to persist user awards outside that server path. Host-side evidence and award deduplication remain authoritative.

Analysis constructors and moves mark their copies with `achievementAnalysis: true`; full wrapper replay preserves this exclusion. Older analyses may not have the marker, so the host's analysis isolation is still required. Ordinary historical replay is a pure engine operation, not permission to backfill achievements.

## Revision-2 review verification

-   150 achievement tests pass, including all 24 maps in both variants at two and six seats, winner/loser checks, runtime catalog parity, resolved-map handling, unsupported names, thresholds, eligibility, ties, and real replay fixtures.
-   Full suite: **725 passing** with `pnpm --filter powergrid-engine exec mocha -r ts-node/register 'src/*.spec.ts' --timeout 10000`. An archived unchanged `eb08aaf` baseline passes **625** with the same timeout. Both baseline and candidate hit existing 2-second replay timeouts under the default limit; the override is command-line only, with no skipped tests or assertion changes. An initial candidate run also hit the historically recorded China shuffled-deck analysis assertion; it did not recur in the comparison runs or targeted baseline test.
-   Engine build and published protocol schema validation pass. The compiled manifest is compared with the recorded revision-1 catalog: exactly 20 additions, with only Fully Supplied's approved description change among existing IDs.
-   102 viewer unit tests pass. Engine lint passes with 0 errors and 41 warnings. Frozen installation, formatting, and whitespace checks pass.
-   Scoped read-only review found no concrete issues; final coordinator approval is still required before publication.

## Previous release verification (2.0.32)

The following results describe the shipped revision-1 release, not approval of revision 2.

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
-   Review all 36 IDs/descriptions, thresholds, tie semantics, and human-versus-bot policy with the coordinator.
-   Validate the compiled hooks against protocol manifest/result schemas and the actual BGS install/adjudication path before release, including cancellation, bot/account filtering, duplicate completion, and edited-solo exclusions. Unit tests cannot substitute for server-owned eligibility checks.
-   After approval, allocate an engine release version, fetch/integrate the latest canonical release, rerun relevant checks, and publish through the existing engine release workflow. Verify the installed artifact contains both hooks and the expected manifest revision. No artwork is required.
-   Only when authorized to publish: follow AGENTS.md's corresponding source/lockfile/version commit, canonical release-branch push, public mirror update, and remote-delivery verification requirements. The approved 2.0.32 delivery follows that workflow; consult its release receipt for the installed artifact and verification results.
