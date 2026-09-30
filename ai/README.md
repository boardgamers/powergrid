# Powergrid AI — first executable baseline

This is an experimental training/serving pipeline, **not a replacement for the current production bot**. The trained self-play model beats the new simple heuristic but loses heavily to the engine's existing bot. No BGS bot routing has been changed.

## Scope and information

Germany, three players, normal region setup, original and Recharged rules, open and sealed (`fastBid`) auctions. Money is visible for every player. Other maps, player counts and randomized maps need another feature schema and training distribution. Optional region/color drafts are not represented adequately and must not be used with this model.

The existing compiled JavaScript engine is the authoritative simulator. No game rules were modified. The engine revision is `365fc519903fa2b4e8c593eed6cc5f5f77b5332a`. Schema v2 contains 541 state numbers and 74 numbers per candidate action. Its 44-city vocabulary covers both original and Recharged Germany, including Stralsund/Mainz and Torgelow/Wiesbaden. Schema v1 omitted the two replacement cities and is superseded; do not mix v1 weights with current features. The policy scores a variable list of legal candidates. Large bid lists are approximated by the lowest eight bids, multiples of ten, and the maximum; this is not exhaustive bidding.

Feature extraction excludes seed, deck order, logs, queued plans, and sealed bid amounts, including already submitted opposing bids. Sealed auctions retain the engine's actual resolution rules, rather than being treated as faster ascending auctions. Player order, plant markets, resource markets, cities, all players' money and holdings remain visible. The server passes trusted engine state; the model itself sees only the allowlisted features.

## Corrected schema v2 results

The final HF job completed in 155 seconds. It uses the 44-city vocabulary, 600 synthetic games, 32 supported human games, 12 imitation epochs and 16 self-play updates (482 completed episodes). Four JS workers serve 64 environments; optimizer batch is 1,024. Source: dataset commit `65ecfa063c272bd72a805d45f4ba55dc84a28f42`, archive `source-v4.tgz`. Job: https://huggingface.co/jobs/coyotte508/6abd0cba404719ba3761324e.

Each comparison has 480 games and zero truncations:

| Candidate    | Opponents           | Win share |
| ------------ | ------------------- | --------: |
| Imitation v2 | New heuristic       |    13.75% |
| Self-play v2 | New heuristic       |    90.00% |
| Imitation v2 | Existing engine bot |     0.00% |
| Self-play v2 | Existing engine bot |     0.00% |

This is a failed playing-strength gate, despite a working training pipeline. Do not deploy it as the production bot. The larger optimizer batch improved component throughput but reduced gradient updates per epoch; these runs also change schema and rollout configuration, so they are not a controlled batch-size quality comparison.

On the 8840U, the corrected self-play model reproduces all 480 laptop game outcomes. Pure inference p95 is 0.130 ms. Full worker p50/p95 is 0.773/1.202 ms across 48 representative positions; startup plus first request is 152 ms. All returned actions are legal. Both exports agree with PyTorch on 128 checked decisions each, with maximum absolute error below 0.000007.

The throughput microbenchmark measured 2,766 decisions/s with one worker/24 environments, 6,289 with four workers/256 environments, and 6,177 with eight. Optimizer sample throughput rose from 18,874 to 28,590/s when increasing batch 256 to 1,024. This does not translate directly into full training speed or playing strength.

## Initial evidence (schema v1; corrected-model results accompany the package)

-   Read-only BGS audit: 4,007 records, 3,978 marked ended. Export restricted to non-unlisted, ended Germany games with three players.
-   66 candidate historical games; 33 replay exactly against the current engine, including 7 sealed games. Reject 14 dropped/quit/bot games, 15 records that do not reach engine termination, and 4 incompatible replays. The initial run used 11,675 decision examples. Corrected-schema training excludes one color-draft game outside its supported setup: 32 games and 11,366 historical decision examples remain. These records are private and excluded from Git and serving bundles.
-   Initial HF job: 600 synthetic games plus verified human examples, 12 imitation epochs, 16 PPO updates, all three seats share the model. Split imitation validation by whole game. HF job completed in 147 seconds excluding queue. CPU training is not run on the 8840U.
-   Evaluation: 40 unseen seeds × 3 rotated seats × 4 rule combinations = 480 games per comparison. Model gets one seat, the selected opponent fills the other two. Zero truncated evaluation games.

| Candidate       | Opponents           | Win share |
| --------------- | ------------------- | --------: |
| Imitation model | New heuristic       |    59.27% |
| Self-play model | New heuristic       |    81.77% |
| Self-play model | Existing engine bot |     2.08% |

These are observed win shares, splitting ties. Seats sharing a seed are correlated. The simple heuristic is a weak opponent; its score is not evidence of human-level play. Use the existing bot as a gate and a training teacher in the next experiment. Freeze separate final-test seeds before selecting many checkpoints.

8840U: all 480 model-vs-heuristic games completed with identical outcomes to the laptop. Pure ONNX inference p50 0.082 ms / p95 0.165 ms. Persistent JSONL worker on 48 representative positions: p50 0.725 ms / p95 1.144 ms; first request including worker startup 182 ms. All returned actions passed the engine. These are one-run measurements, not concurrency/load guarantees.

The value head is an **uncalibrated self-play win estimate**, not a forecast of a player's final score or objective position strength. Imitation held-out value MSE is approximately 0.244. Do not expose a player-analysis graph from it yet: add round-stratified calibration, stronger reference opponents, and a separate final-score target if that is the desired analysis.

## Run and reproduce

Install the engine dependencies and build `engine/tsconfig.json` using the repository's package manager. Use Python 3.11+, Node 24, and `numpy`, `onnxruntime` for serving. Cloud training additionally needs PyTorch, `onnx`, and `huggingface_hub`; launch scripts use the PyTorch 2.6.0 CUDA 12.4 image.

```sh
node --test ai/test.cjs
hf download coyotte508/powergrid-ai-germany-v1 --include 'runs/baseline-v2/*' --local-dir ai/runs/download
python ai/evaluate.py ai/runs/download/runs/baseline-v2/selfplay.onnx --seeds 40 --output evaluation.json
python ai/evaluate.py ai/runs/download/runs/baseline-v2/selfplay.onnx --seeds 40 --opponent legacy --output evaluation-legacy.json
python ai/serving-smoke.py ai/runs/download/runs/baseline-v2/selfplay.onnx
```

Private HF repositories require the owner's token in the CLI credential store. `launch-v2.sh` trains the corrected schema using `source-v4.tgz`; `launch.sh` reproduces the initial frozen `source-v1.tgz` job; `launch-smoke.sh` checks the updated concurrent trainer with `source-v2.tgz`. `launch-profile.sh` measures batching/worker throughput. Source archives contain only the compiled engine, its production dependencies, AI scripts and the deidentified verified training records. Use the recorded dataset commit plus archive hash for exact provenance; uploaded archives are not automatically rebuilt when local files change.

Trainer controls: `GAMES`, `BC_EPOCHS`, `RL_UPDATES`, `ENVS`, `WORKERS`, `BATCH_SIZE`, `ROLLOUT_SAMPLES`, `OUT`, `RUN_NAME`, `HF_MODEL_REPO`. Start with four workers and 256 environments, then tune the optimizer batch from measurements. Increasing batch changes optimization dynamics; compare strength as well as throughput. The small model does not need to fill GPU VRAM. Python JSON conversion and feature packing still take appreciable time; a packed binary/shared-memory interface is the next throughput improvement if needed.

## Platform worker contract

Keep one worker alive per CPU execution slot:

```sh
python ai/infer.py selfplay.onnx
```

Input is one JSON object per line: `{ "requestId": "unique-job-id", "revision": 123, "player": 0, "state": <authoritative raw engine state> }`.

Output echoes the request ID/revision and returns `move`, `winProbabilities`, `valueStatus`, `playerOrder`, `model`, `modelSha256`, and `elapsedMs`, or an `error`. Probabilities are ordered `[acting seat, next seat clockwise, third seat]`.

Each request chooses one **atomic** engine action. Before committing it, the platform must reload/check the game revision and acting player, validate the action with its pinned engine, and commit through its normal move path with a server timestamp. Revision is an echoed correlation value here, not a concurrency lock. Retry stale jobs from fresh state; deduplicate by request ID; use the existing bot on timeout/error or unsupported options. Multiple atomic actions can be needed to finish a player's turn. The process provides no HTTP endpoint or authentication; invoke it through the platform's existing job machinery.

## Next strength experiment

1. Generate demonstrations from the existing engine bot and improve the heuristic's build/auction economics. Preserve information boundaries for all teachers.
2. Train against a mixture of existing bots, frozen older policies and self-play; use larger rollout batches and enough completed games rather than simply more GPU memory.
3. Evaluate across rule combinations and held-out seeds with paired uncertainty estimates; require improvement over the existing bot before routing production moves.
4. Expand to other maps/player counts using graph/city features and variable player encodings. Retrain; do not silently apply the Germany model.
5. Train/calibrate analysis targets separately. Public-money assumptions must remain explicit in any analysis UI.
