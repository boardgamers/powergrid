# Auction discount is absent from the neural inputs

The frozen schema-4.3 encoder produces **identical complete encodings for ten
paired public states** where the Recharged discount changes the cheapest plant's
opening bid from one Elektro to its printed number, between 3 and 11. Each pair
has the same legal menu. State vectors, action matrices, priors, shortlist bits
and teacher indexes are identical. Twenty encoder calls, no model inference,
search, fresh games, gradient updates or HF jobs were needed to establish this.

This is a concrete information gap to address in a future training experiment.
It does not establish that nominating the plant is better, that these paired
histories arise naturally, or that this gap explains the weak Recharged results.
The ongoing auction comparison remains valid for its unchanged frozen policy.

## Predetermined fixtures

The ten original controls from the existing
[current-engine policy check](CURRENT-ENGINE-POLICY-2026-10-28.md) supply the
roots: 2–6 players, open and sealed Recharged auctions, first eligible nomination
after round one in fixed recorded economic episodes 1 and 3. The actor can pay
the printed plant number in every control.

For each root, change only `plantDiscountActive` from true to false and recompute
the actor's menu using the pinned current engine. All cash, plants, cities,
history and other fields stay unchanged. The flag-off member is explicitly a
counterfactual; its history is not rewritten to pretend it was observed.

| Players | Auction | Cash | Cheapest plant | Opening bid, discount on/off | Full encoding identical |
| --- | --- | ---: | ---: | --- | --- |
| 2 | Sealed | 44 | 3 | 1 / 3 | Yes |
| 2 | Open | 43 | 3 | 1 / 3 | Yes |
| 3 | Sealed | 41 | 4 | 1 / 4 | Yes |
| 3 | Open | 49 | 4 | 1 / 4 | Yes |
| 4 | Sealed | 35 | 7 | 1 / 7 | Yes |
| 4 | Open | 36 | 7 | 1 / 7 | Yes |
| 5 | Sealed | 37 | 11 | 1 / 11 | Yes |
| 5 | Open | 54 | 7 | 1 / 7 | Yes |
| 6 | Sealed | 39 | 9 | 1 / 9 | Yes |
| 6 | Open | 39 | 9 | 1 / 9 | Yes |

## Mechanism and interpretation

`features-v4.cjs` has no explicit `plantDiscountActive` input. The subsequent
4.1/4.2/4.3 extensions add fifth plants and correction/shortlist cues, but do not
add the discount. The economic nomination prior compares plant value against
the printed number. It is unchanged across these pairs, including the raw
unclipped scores.

`core.cjs` encodes a nomination's immediate action cost as zero. That is not
itself a wrong debit: nominating starts an auction and does not necessarily buy
the plant immediately. The missing information is the conditional opening price
and discount state, rather than a need to relabel every nomination as a purchase.
The printed plant number should remain available as a separate identity/value
feature. The engine's `minimumPlantBid` function is the price reference here.

A deterministic feed-forward neural model cannot directly condition its output
on a changed flag when its entire encoded input is identical. It can learn
correlations with other state fields, and hybrid search can still inspect the
full state and simulate different consequences. This diagnostic concerns the
neural representation; it is not a claim that every component of the hybrid
policy is blind to discounts.

## Next experiment, after the current comparison

Consider a separately versioned, append-only feature extension with the public
discount flag and each nomination's actual opening price/discount amount. Keep
the existing feature meanings and printed plant number. A warm-start conversion
should initially preserve the old model's outputs before training the new inputs.
Use a separately pinned intended engine so the newly affordable nomination is
actually represented in legal-action generation and labels.

Measure against the frozen reference on the same full development schedule,
with particular attention to Recharged open/sealed and original-rule regressions.
Do not silently change the encoder, teacher or priors in any running study.
Check naturally observed coverage and action regret before attributing existing
losses to this feature. No new feature artifact, training job, strength study,
candidate qualification or final-seed use is introduced by this diagnosis.

## Evidence

`strong/check-auction-discount-encoding-v1.cjs` verifies the frozen runtime
manifest, current compiled engine and existing fixture hashes before encoding.
`runs/auction-discount-encoding-v1/` contains the fixed design, both full encodings
for every pair, and the assessment. The first execution completed successfully.
`strong/auction-discount-encoding-results-v1.json` binds these files.

The private archive indexed by
`strong/auction-discount-encoding-evidence-v1.json` preserves the diagnostic and
full paired vectors and references the existing immutable source/fixture archives.
It verifies equality and the changed opening bids without rerunning inference.
