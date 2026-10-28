# Current-engine auction search — 28 October 2026

The historical auction study remains complete and unchanged. Its cheaper
population-search recipe is being moved to engine commit
`3adad0cc0d1d31352aa7a9059bd15efa79647269` (2.0.19) in an isolated research
artifact. Weights, features, shortlist, eight-world budget, opponent population,
strict-loss filter and selection threshold are unchanged. No production files
were edited or deployed, and final qualification seeds remain unused.

## Current engine and ordinary positions

The first isolated copy changes 11 compiled engine JavaScript files, adds three
engine files, and drops 39 stale declaration files. The public transport gains
an explicit scope check; 1,451 original runtime files remain byte-identical.
The engine compilation used TypeScript 4.3.5 with ES2018/CommonJS output; this
build is not claimed to have passed TypeScript type checking.

The scope check runs before model construction/inference: Germany, 2–6 players,
public money, original/Recharged, open/sealed, automatic setup, standard deck,
current Recharged setup, and no optional end-of-Step-3 discount removal. Unknown
options, hidden balances and unsupported drafting/deck options fail explicitly.
Four tests cover 100 accepted saved CPU requests, 12 rejected requests, a valid
zero balance and a factory-order positive control. This is a research scope
boundary, not a deployed platform router.

The completed first fixture run checked **2,693 filtered-model requests** and
**140 population-search requests**:

- 2,553 original serving fixtures, 100 separately normalized archived CPU cases,
  30 current-engine controls/counterfactuals, and 10 naturally recorded low-cash
  nomination cases. Existing train/validation provenance remains unchanged.
- 2,673 public preparations match the historical engine exactly. The remaining
  20 menus gain precisely the newly affordable discounted nomination: ten
  one-Elektro counterfactuals and ten natural cases. There are no unexplained
  menu differences.
- All 100 archived filtered-model CPU controls reproduce their full semantic
  decisions exactly. The current engine changes one historical search choice
  (`4p-recharged-sealed-choose`), so historical strength is not automatically
  transferred to this engine.
- All 140 information-boundary tests preserve observations and sampled worlds
  after altering hidden deck, seed, bid, log, automation and last-move data.
- Search completed 2,160 uncapped continuations and 390,557 neural decisions;
  it changed 23 model choices. Elapsed local wall time was 540.87 seconds.

These are saved-position engineering checks, not fresh whole-game win evidence
or timing on the AMD 8840U.

## Actual sealed-auction input failure

The old belief adapter assumed submitted sealed bids formed a prefix of player
order and the requested actor was the first pending player. Actual simultaneous
submissions and automatic unaffordable passes can violate both assumptions.
The error was in the research adapter, not an engine rule.

Ten archived round-after-first nomination roots cover 2–6 players and both rule
variants. The actual wrapper commits nomination plus bid. For each root the
diagnostic either requests a later pending player or sets a later opponent's
cash to zero and lets the wrapper automatically pass them. This produced
**16 reproducible adapter failures among 20 cases**: all 3–6-player cases fail;
the four two-player controls remain compatible. Cash edits are explicit
counterfactuals; this does not estimate the frequency in natural games.

Two earlier diagnostic harness mistakes are preserved. The first expected
automation before committing the bid; the second used zero initial cash during
mandatory first-round purchasing and assumed the auction must immediately end.
Neither is counted as an engine defect or a successful compatibility test.

## Public pending-player repair

A second separate runtime changes only `sealed-policy-beliefs.cjs` relative to
the first. It derives submitted actors from eligible players minus the public
pending-player set. Their reconstructed prior prompts use deterministic player
order; the adapter does not claim to recover actual submission chronology and
never reads hidden bids. An already-submitted requested actor is rejected.

For canonical prefix inputs this construction equals the previous construction.
All **2,693 public preparations match exactly** between the two copies. All 20
wrapper inputs now prepare correctly, including the 16 previously failing
cases. The automatic-pass prior offers only Pass. Hidden-data edits and pending
list permutations preserve the prepared inputs.

The complete second run passed: **20 filtered-model requests and 160 search
requests**, comprising the 140 canonical controls plus all 20 wrapper cases.
All canonical full decisions, sampled worlds and continuation credits match
exactly; only elapsed time is excluded. Every wrapper response is legal and
matches the complete runtime/model identity and request/revision/player order.

Search completed **2,960 uncapped continuations / 512,203 neural decisions**,
with 88 searched decisions and 24 overrides. The 20 wrapper cases account for
800 continuations beyond the canonical controls. Total local time was 563.94
seconds. The original execution session exited 0. These checks generated no
new whole-game strength observations, HF jobs, gradient updates or final seeds.

The fixed-position migration is verified. Whole-game HF runtime admission and
fresh strength confirmation remain separate requirements.

## Frozen identities and recovery

| Item | SHA-256 |
| --- | --- |
| Model | `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530` |
| Historical runtime | `a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619` |
| Current engine, first copy | `8ad645eb91e9f56278e5c820b92fae47aca45ebcb610fa75eb6713e93884fc3f` |
| Current engine, pending-set repair | `fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df` |
| Actual-wrapper cases | `1d303732b7c5430e01015608a2451cad27edbd2553f73d2b83c4d13c56c154e0` |

Raw runs are under `runs/current-engine-auction-v1/`,
`runs/current-engine-auction-v2/` and
`runs/current-engine-auction-wrapper-diagnostic-v{1,2,3}/`. Each original intent,
receipt and failure remains preserved. The separate evidence archiver re-audits
the saved responses without inference, and records exact file deltas from the
immutable historical source bundle. The verified descriptor is
`strong/current-engine-auction-evidence-v2.json`: private model revision
`ca003e34a2b80b86f95aa8b7affc031b8bde2683`, archive
`archives/current-engine-auction-evidence-v2.tgz`, SHA-256
`12309cf9c1ac339601ccf8e5e6c78916e57fabce04626efb49a3ca19f4c67e0d`.
All 80 archived files and the downloaded archive hash verified. Do not repeat
this completed archive.

## Next strength decision

Carry the unchanged cheaper auction recipe forward. The frozen next
confirmation uses 32 fresh deals per count, every seat and all four rule
combinations, against all 27 opponent/count cells. Two arms make 26,880 games.
The primary contrast is the equally weighted search-opponent gain over the
same filtered model; all adverse count/rule cells remain visible. No dual arm,
new discount-feature training or retrospective routing is added.

First complete current-engine whole-game HF pilots for both arms at 2 and 6
players: four jobs, 64 runtime-only games. Use their measured complete costs for
the larger grid. No final candidate is selected by this document. Fresh strength
confirmation, the unchanged reserved qualification gate, selected-policy serving
checks, actual 8840U measurement and standalone package verification remain.


## Current execution and recovery

The protocol `strong/current-auction-confirmation-protocol-v1.json` is frozen
before any confirmation games. All four portable job contracts validate from
an unrelated working directory without executing games. Five launcher tests
verify duplicate prevention, preserved unknown outcomes, reserved/development
seed rejection, bounded pilot shards and exclusive submission locks.

The four original runtime pilots were submitted on 28 October at approximately
22:12 UTC. They use `cpu-upgrade`, four simultaneous games per job, four search
workers and one inference thread. Both two-player jobs have a two-hour limit;
both six-player jobs have a five-hour limit. The allocation uses 900 seconds of
setup plus twice the previous same-count population-pilot wall time within
75% of the limit; it is a planning allowance, not a performance guarantee.

| Policy / players | Original HF handle |
| --- | --- |
| Filter / 2 | `6ae2733541e90535df77d71e` |
| Filter / 6 | `6ae273363fb22a235dd4a65d` |
| Population auction search / 2 | `6ae2733641e90535df77d722` |
| Population auction search / 6 | `6ae273363fb22a235dd4a660` |

The independently hash-verified source is in the private **dataset** repository
`coyotte508/powergrid-ai-training-v1`, revision
`fbee9770f28fd5bf6b2042382876e58ebbaf775d`, archive
`strong-source-current-auction-runtime-v1.tgz`, SHA-256
`d0d7265536ad848c93883074a2513bae336421c0211895335a56da583ebb0a61`.
The unchanged Node release is downloaded from its already verified immutable
HF cache, avoiding the previous origin-download failures.

Collect only these original handles with:

```sh
ai/.venv/bin/python -u -B ai/strong/manage-current-auction-runtime-v1.py collect
```

The collector is bounded and never submits jobs. No background submitter or
collector has been started. Inspect actual HF status and original receipts
before any recovery; preserve failures and partial evidence. The source,
launch guards and statuses are under `runs/current-auction-runtime-hf-v1/`.
The launch/recovery archive descriptor is
`strong/current-auction-runtime-launch-evidence-v1.json`, verified at private
model revision `176f2f01da956b583cc5fc97a15bed7d753e8fbb`, archive
`archives/current-auction-runtime-launch-evidence-v1.tgz`, SHA-256
`45c9699cb31f7e770036d7045d29aa6db0ea7ef2824d9891c980c482438542f5`.
All four original handles were independently inspected as RUNNING for this
snapshot; no completion or strength result is implied.

Do not launch the 26,880-game grid until all four pilots and independent raw
receipts pass and measured costs determine its batch sizes and timeouts. Pilot
win rates are not strength results. No new training was started in this turn.
Research remains active, with no candidate qualified and no final seeds used.
