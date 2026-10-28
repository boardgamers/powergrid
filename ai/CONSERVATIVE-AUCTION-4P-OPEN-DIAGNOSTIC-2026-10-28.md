# Four-player original/open: complete historical regression diagnostic

This is a **post-hoc description of existing games**, not a new strength test
or a reason to retune the frozen confirmation policy. It examines every pair
in the adverse `search_geo/4p`, original/open cell of the completed historical
10,080-game study: 32 games per arm, all seats on eight independent deals.
No games, inference, gradient updates or HF jobs were generated.

## What the negative result consists of

The filtered model won 17/32; population auction search won 15/32. Across the
same deal/seat pairs, search lost nine previously won games and gained seven
previously lost games. Eight pairs were wins for both; eight were losses for
both. There were no tied wins in this cell.

The net credit differences by independent deal are
`0, −1, 0, +1, −1, −1, −1, +1`, out of four seat repetitions per deal. Thus the
net deficit of two wins is spread across four negative deals, two positive
deals and two unchanged deals. No single deal accounts for the whole deficit.
The existing paired interval remains **−6.25 percentage points [−18.75, +9.38]**.
This evidence cannot distinguish a repeatable regression from sampling noise.

All 32 paired trajectories first diverged at a legal auction-search override
on **the same public input**, with the filtered model's move matching search's
baseline proposal. No preceding input or move mismatch was found. Later game
states differ as expected; that does not identify which later choice caused a
win or loss.

## Spending does not support a simple overbidding fix

The following are descriptive search-minus-filter differences. They condition
on the observed outcome, so they are not causal estimates or independent tests.
Spending comes from the last saved learner observation: in all 64 games this
was a Pass in the terminal round, with the same city count as the terminal.
Final city/powered counts come directly from the terminal records.

| Paired outcome | Pairs | Mean plant-spending difference | Median plant-spending difference | Mean final city difference | Mean final powered difference |
|---|---:|---:|---:|---:|---:|
| Search loses a baseline win | 9 | +15.44 | +2 | −1.33 | −0.56 |
| Search gains a baseline loss | 7 | −11.29 | +33 | +0.86 | +1.14 |
| Same win/loss outcome | 16 | +7.13 | +11 | −0.50 | +0.31 |

The means alone are misleading: one regressed pair adds 114 in plant spending,
while one improved pair saves 192. Three of the nine regressed pairs spend
**less** on plants; three of the seven improved pairs also spend less. The
median spending direction does not reproduce the mean-based pattern. Do not
infer that reducing auction bids will repair this cell.

Among the nine regressed pairs, two finish with **more** powered cities than
their baseline counterpart, three with the same number, and four with fewer.
The opponents' outcomes change too. Six losses are decided by powered cities
and three by the money tiebreaker within the search trajectory; these facts do
not isolate plant efficiency, fuel planning or city timing as the sole cause.

## First divergence in every regressed pair

Deal and seat numbers are zero-based. These are first changed moves, not
counterfactual proof that the move was wrong. Plant numbers are identifiers;
nomination does not imply the eventual purchase price.

| Deal / seat | Round | Model + filter | Population search |
|---|---:|---|---|
| 0 / 0 | 1 | Nominate plant 5 | Nominate plant 4 |
| 1 / 1 | 1 | Bid 8 | Bid 7 |
| 1 / 2 | 1 | Pass | Bid 30 |
| 2 / 2 | 2 | Pass | Nominate plant 10 |
| 4 / 1 | 1 | Bid 6 | Bid 7 |
| 4 / 3 | 1 | Pass | Bid 12 |
| 5 / 3 | 1 | Pass | Bid 10 |
| 6 / 1 | 1 | Bid 7 | Bid 28 |
| 6 / 2 | 1 | Pass | Bid 10 |

The earliest difference is usually in round one, but changes include lower
bids, higher bids, entering an auction and a different nomination. Each full
trajectory contains further search overrides. A controlled diagnostic of an
individual action would require separate counterfactual evidence; this saved
receipt analysis does not provide it.

## Research decision and recovery

Keep the unchanged population-search policy and its paired filtered control
for the already frozen current-engine confirmation: 32 fresh independent deals
per player count, 26,880 games across all opponents/rules/counts. Retain the
four-player original/open cell and every adverse view. Do not choose new bid
thresholds, opponent mixtures or count/rule routing from these eight deals.
If the fresh study reproduces a weakness, this complete case list provides
diagnostic inputs for a separately designed follow-up; it is not training data
for the policy under confirmation.

The new analyzer is `strong/diagnose-conservative-auction-4p-open-v1.py`.
Its result is `strong/conservative-auction-4p-open-diagnostic-v1.json`, retaining
all 32 pairs, outcomes, final states, first divergences, spending differences,
80 checked input hashes and references to 16 immutable raw HF archives.
It reconciles win credits and the exact mean difference with the pinned complete
comparison, then rechecks every input after analysis. The original process
session 98030 exited with code 0; do not rerun it without a changed question.

The source comparison SHA-256 is
`2d2e469a073e3cd71a919da6a137042cfb5fd2ea14d6fb0491997d06eee77e37`;
its complete recovery archive is indexed by
`strong/conservative-auction-comparison-evidence-v2.json`. This diagnostic does
not modify that comparison or any model/runtime/confirmation pin. The research
goal remains active; no candidate qualified and no reserved final seeds used.

Verified recovery archive: private model repository
`coyotte508/powergrid-ai-germany-v1`, revision
`eaef9f7377f3c334137af1e7a90cf74a9cc181c4`, path
`archives/conservative-auction-4p-open-diagnostic-evidence-v1.tgz`, downloaded
SHA-256 `3473260239e8da8e4c12cc6d0d9d90fc892337273f451fcfdab7b92f83ca4f26`.
`strong/conservative-auction-4p-open-diagnostic-evidence-v1.json` records the
bindings. The archive preserves the full diagnostic, analyzer, run log and
pre-upload document, and references the original raw evidence rather than
repeating any games.
