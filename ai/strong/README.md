# Strong-policy research (active)

The target is substantially stronger play, not merely beating the engine's default bot. No strength claim is made from the first prototype. Training runs on HF Jobs; CPU inference and correctness checks run locally and on the 8840U.

## Critical diagnosis

The first heuristic incorrectly read `BuyResource.data.price`, which the engine does not provide. The resulting NaN comparison suppressed fuel buying. It also used the beginning of a price schedule instead of the slot indexed by remaining market stock. Both are fixed and covered by a test against the engine's actual cash deduction. The corrected heuristic wins 85.1% against the default bot over 960 games. Thus the default bot is only a sanity check.

`../core-v2.cjs` preserves the old feature semantics solely for compatibility with old exported research artifacts. New strong models use the corrected core and this directory's features. Do not evaluate new models with old feature encoders.

## Model information and strategy

Schema 3 has 738 state features and 96 features per candidate action. All opponents' money is visible by user instruction. Hidden deck order, random seed, sealed bid amounts and queued plans are excluded.

Feature revision `3.1-uranium39` corrects the effective uranium refill after plant 39 has been bought in Recharged Germany (also handled by the helper for Italy). The engine's persistent flag matters even after that plant is discarded. A test compares the feature's predicted refill with a real engine round transition. Older checkpoints use frozen revision `3.0`; the arena and worker select the matching encoder from ONNX metadata. The old encoder's output was verified byte-for-byte against the archived runtime over 427 positions. Unknown revisions and mismatched data fail explicitly. Revision 3.0 datasets and source bundles are retained for reproducibility, not silently reinterpreted.

The observation explicitly includes all players' cities, plants, fuel, money, current order and remaining actors; per-resource replenishment for every step; current prices and capped refill; and generation capacity with current fuel. Territory features describe each player's presence in map-defined regions/islands and their remaining legal building slots. Building actions include the projected next order with highest-plant tie breaking. Terminal winning is the optimization objective; there is no reward for indiscriminately adding cities.

`public-graph.cjs` exports map topology, owner vectors, slot rules, edges, islands and crossing costs for subsequent multi-map model work. UK/Ireland territory behavior is tested, but the current trained policy remains Germany/three players. Exporting generic map features does not establish playing strength on another map.

## Opponents and training

The economic opponent enumerates feasible plant/fuel combinations and considers purchase cost, income, generation capacity, resource replenishment and stockpiling. A rush variant and the corrected heuristic supply different styles. The residual policy starts with economic action scores and learns neural corrections, rather than initially relearning how to buy fuel from scratch.

PPO collects complete episodes against a mixture of fixed bots, self-play and frozen earlier neural policies. The four learners vary seed, learning rate, entropy and prior regularization. Each is configured for 300 updates × 128 completed games. Development evaluation uses 96 games per opponent every 20 updates. It selects checkpoints; it is not the final test.

A separate rollout-search opponent uses the engine's public-information scenario sampler and evaluates counterfactual actions across sampled unknown decks and sealed bids. Its choices are tested for invariance to the actual hidden deck and bids. The initial search benchmark is held separately from training.

The search reference scored 64.8% against the economic bot and 76.3% against the corrected heuristic, 240 games each with no truncations. Bootstrap 95% intervals, clustered by the 20 independent deals, were [57.9%, 71.7%] and [70.8%, 81.3%]. The B learner's update-20 checkpoint scored 42.2% against the economic bot on 480 fresh paired games (40 deals; interval [38.1%, 46.3%]). These are development/screening results, not a final strength claim; the comparison also uses different deals.

Four HF CPU jobs generated a separate search-teacher dataset: 512 games, 25,268 strategic positions, 6,769 disagreements with the economic teacher, zero truncated games. `distill.py` trains on HF GPUs, splitting whole games for validation and selecting checkpoints using actual arena performance. Its seeds do not overlap the reference benchmark, screening, or reserved final test.

The first distillation run deteriorated after epoch 5. Its epoch-30 model scored 8.6% against the economic bot on 480 screening games. Restricting its learned corrections to auction/build decisions raised that to 22.3% on exactly the same deals, still worse than the economic prior. This isolates harmful changes in unsupervised phases as one contributor, not a complete explanation. The next dataset covers every phase and uses 12 search samples instead of four. Hard labels and distributions over counterfactual action values are separate experiments; no improvement is assumed in advance.

The high-exploration league runs C and D were stopped after sustained regression around updates 60–80, retaining their best checkpoints. B completed all 300 updates; A continues. The neural B20 checkpoint scored 23.8% against two search opponents over 240 paired screening games (20 deals; 95% interval [17.1%, 30.4%]). Thus it has not passed the strength gate.

B160 subsequently scored 46.0% against the economic bot and 40.4% against two B20 neural opponents, each over 480 paired screening games (40 independent deals) with no truncations. B20 with 16-sample search scored 47.9% against two four-sample search opponents on 96 screening games (eight deals; interval [36.5%, 59.4%]), but its original/open subset was only 25%; broader evaluation is needed. These runs use their archived revision-3.0 runtime. B160 scored 47.9% with 16 samples and 61.5% with 48 samples against the four-sample reference, each over 96 games/eight deals. The 48-sample interval is [53.6%, 71.4%]; all four rule subsets exceeded 54%. This remains a small development test against a limited reference.

The corrected revision-3.1 dataset (`search-teacher-v3`) contains 247,104 decisions from 2,048 complete games, with 33,130 search/economic disagreements and no truncations. It includes all phases and uses 12 search samples per strategic decision. Hard-label and uncertainty-preserving distillation completed separately on HF Jobs. Their best checkpoints scored 37.9% and 42.5%, respectively, against the corrected economic opponent over 480 paired screening games each. The corrected soft-label checkpoint is the starting point for two new PPO refinements, with an anchor to its initial policy; one includes search opponents and restricts learned corrections to strategic phases. The new dataset replaces the intermediate revision-3.0 all-phase dataset for corrected-model training.

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

## Current deeper evaluation

Optional geographic proposals broaden build shortlists using connection costs and nearby available expansion sites, while preserving the classic reference for reproducibility. The independent `search_geo` opponent uses 16 sampled worlds and six proposals. Three configurations (B160/48 samples, corrected soft/48, corrected soft/16) each have four HF CPU shards of 48 games against it, sharing deals across configurations. These are development tests; reserved final seeds remain unused. Source v11 is pinned in `experiments.json`.

The corrected soft model passed PyTorch/ONNX parity across all 427 fixture positions: all actions identical, maximum logit error 3.82e-5 and value error 2.15e-6. On the 8840U, all requests were legal, with 1.87 ms median and 3.45 ms p95 full-worker response. With 48-sample geographic search, a smaller 43-position sample had a 2.02-second p95 and all legal moves. These timings support feasibility, not playing strength.

A bounded cache of static plant/fuel combinations was tested and removed: feature/search output hashes stayed identical, but measured runtime increased. No cache is included in source v11.

The later A260 checkpoint scored 67.5% against two economic opponents on the same 480 paired screening games (40 deals; 95% interval [62.3%, 72.5%]), compared with B160’s 46.0%. Its four rule subsets scored 57.5%, 65.8%, 71.7%, and 75.0%. The corrected refinement checkpoint at update 30 scored 54.7%. Both exports matched checkpoint actions on all 427 fixtures. A260 is now tested against frozen B160 and the deeper geographic search reference, both raw and with 48-sample guided search. These remain development tests; final seeds are reserved.

An explicit, limited 3.0 → 3.1 uranium-feature transfer experiment starts from pinned A260 weights. Ordinary checkpoint loading still rejects mismatched input revisions. The experiment evaluates its transferred starting policy before any gradient update, anchors refinement to that policy, records the original feature revision, and trains only on an HF GPU job. It does not relabel the old ONNX model or claim unchanged behavior. The complete 427-position corrected-soft/search-48 benchmark on the 8840U returned only legal moves with a 2.50-second p95. Raw A260 serving also passed all 427 positions at 3.74 ms p95.
