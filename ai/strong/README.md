# Strong-policy research (active)

The target is substantially stronger play, not merely beating the engine's default bot. No strength claim is made from the first prototype. Training runs on HF Jobs; CPU inference and correctness checks run locally and on the 8840U.

## Critical diagnosis

The first heuristic incorrectly read `BuyResource.data.price`, which the engine does not provide. The resulting NaN comparison suppressed fuel buying. It also used the beginning of a price schedule instead of the slot indexed by remaining market stock. Both are fixed and covered by a test against the engine's actual cash deduction. The corrected heuristic wins 85.1% against the default bot over 960 games. Thus the default bot is only a sanity check.

`../core-v2.cjs` preserves the old feature semantics solely for compatibility with old exported research artifacts. New strong models use the corrected core and this directory's features. Do not evaluate new models with old feature encoders.

## Model information and strategy

Schema 3 has 738 state features and 96 features per candidate action. All opponents' money is visible by user instruction. Hidden deck order, random seed, sealed bid amounts and queued plans are excluded.

The observation explicitly includes all players' cities, plants, fuel, money, current order and remaining actors; per-resource replenishment for every step; current prices and capped refill; and generation capacity with current fuel. Territory features describe each player's presence in map-defined regions/islands and their remaining legal building slots. Building actions include the projected next order with highest-plant tie breaking. Terminal winning is the optimization objective; there is no reward for indiscriminately adding cities.

`public-graph.cjs` exports map topology, owner vectors, slot rules, edges, islands and crossing costs for subsequent multi-map model work. UK/Ireland territory behavior is tested, but the current trained policy remains Germany/three players. Exporting generic map features does not establish playing strength on another map.

## Opponents and training

The economic opponent enumerates feasible plant/fuel combinations and considers purchase cost, income, generation capacity, resource replenishment and stockpiling. A rush variant and the corrected heuristic supply different styles. The residual policy starts with economic action scores and learns neural corrections, rather than initially relearning how to buy fuel from scratch.

PPO collects complete episodes against a mixture of fixed bots, self-play and frozen earlier neural policies. The four learners vary seed, learning rate, entropy and prior regularization. Each is configured for 300 updates × 128 completed games. Development evaluation uses 96 games per opponent every 20 updates. It selects checkpoints; it is not the final test.

A separate rollout-search opponent uses the engine's public-information scenario sampler and evaluates counterfactual actions across sampled unknown decks and sealed bids. Its choices are tested for invariance to the actual hidden deck and bids. The initial search benchmark is held separately from training.

The search reference scored 64.8% against the economic bot and 76.3% against the corrected heuristic, 240 games each with no truncations. Bootstrap 95% intervals, clustered by the 20 independent deals, were [57.9%, 71.7%] and [70.8%, 81.3%]. The B learner's update-20 checkpoint scored 42.2% against the economic bot on 480 fresh paired games (40 deals; interval [38.1%, 46.3%]). These are development/screening results, not a final strength claim; the comparison also uses different deals.

Four HF CPU jobs generated a separate search-teacher dataset: 512 games, 25,268 strategic positions, 6,769 disagreements with the economic teacher, zero truncated games. `distill.py` trains on HF GPUs, splitting whole games for validation and selecting checkpoints using actual arena performance. Its seeds do not overlap the reference benchmark, screening, or reserved final test.

The first distillation run deteriorated after epoch 5. Its epoch-30 model scored 8.6% against the economic bot on 480 screening games. Restricting its learned corrections to auction/build decisions raised that to 22.3% on exactly the same deals, still worse than the economic prior. This isolates harmful changes in unsupervised phases as one contributor, not a complete explanation. The next dataset covers every phase and uses 12 search samples instead of four. Hard labels and distributions over counterfactual action values are separate experiments; no improvement is assumed in advance.

The high-exploration league runs C and D were stopped after sustained regression around updates 60–80, retaining their best checkpoints. A and B continue. The neural B20 checkpoint scored 23.8% against two search opponents over 240 paired screening games (20 deals; 95% interval [17.1%, 30.4%]). Thus it has not passed the strength gate.

## Evidence required before declaring strength

-   Robust gains over the economic, corrected-heuristic, rush, and frozen neural opponents—not just the default bot.
-   Independent matches against the search reference, with confidence intervals and each rule combination reported separately.
-   Fresh final-test seeds, balanced seats, original/Recharged and open/sealed auctions, no silent dropping of failed or truncated games.
-   Tactical and information-boundary tests, ONNX parity, and measured full-worker latency on the 8840U.
-   Human/expert matches would still be needed to substantiate an expert-level claim. Other maps need training and validation, even though their topology can be encoded.

## Runtime

The initial whole-engine JavaScript simulation benchmark was already fast. Repeated economic and regional feature calculations were a larger bottleneck. Hoisting them out of candidate-action loops made the feature benchmark 2.2× faster while preserving the exact output hash across 1,786 positions. A Rust rewrite remains an option if later profiling warrants it.

`infer.py` serves schema 3 over persistent JSONL; it preserves the same revision-validation obligation as the baseline worker. `evaluate.py` runs independent CPU matches. The current policies are research artifacts, not routed into production bot moves.

The arena supports `--opponent search` and `--opponent-model frozen.onnx`. Every deal is repeated across three candidate seats and four rule combinations. Results retain the deal identifier; confidence intervals resample deals, not correlated seat repeats. A same-checkpoint-in-all-seats test yields exactly 1/3 for every rule combination, including with uneven worker batches.

`serving-fixtures.cjs` and `benchmark-serving.py` check full JSONL round trips, legal responses, request/revision preservation and latency across all phases. The update-20 B model's ONNX logits matched PyTorch within 4.1e-6 on 39 search positions, with all argmax actions identical. CPU serving is still a research installation and its value outputs are uncalibrated.

On the 8840U, all 427 fixture requests returned legal moves: warm round-trip median 1.78 ms, p95 3.80 ms, cold start 167 ms. Optional 16-sample public-belief search, guided by the model's proposed move, had a p95 of 704 ms on 43 sampled requests, all legal. The guided variant is under independent arena evaluation; runtime feasibility alone is not evidence of strength. The isolated research installation is `~/powergrid-ai-strong` and has no production routing.
