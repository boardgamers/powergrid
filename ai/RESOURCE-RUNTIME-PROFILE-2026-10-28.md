# Resource-search runtime profile

## What was measured

The independently audited whole-turn two-player HF pilot completed eight games,
919 policy requests and 11,352 uncapped continuations. Its 95 resource decisions
contain almost all the policy's measured time. These measurements are from the
original job `6ae20c133fb22a235dd41471`, with four concurrent games:

| Phase | Calls | Median | 95th percentile | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Auction | 291 | 15.46 ms | 25.55 ms | 38.62 ms |
| Resources | 95 | 18.80 s | 74.68 s | 113.47 s |
| Building | 256 | 14.34 ms | 24.83 ms | 51.01 ms |
| Bureaucracy | 277 | 12.46 ms | 18.19 ms | 41.61 ms |

Resource calls account for **99.50%** of summed policy time. Search itself is
2,472.95 s of the 2,474.66 s spent producing resource responses; the transaction
wrapper is a small part of that total. Summed per-request intervals overlap
across concurrent games: they are neither job wall time nor CPU attribution.
The full measured workflow was 858.53 s wall / 3,079.67 CPU-s, approximately
**3.59 CPU cores on average**. That interval excludes HF bootstrap and uploading.

## Component profiling with exact output parity

Four roots were fixed before profiling: the first resource request in episodes
0, 1, 2 and 3, covering each rule combination. This selection used no win
outcomes. The same pinned v3 policy was called locally with temporary timers
around ONNX execution, input batching, Node requests and the engine pool.
No engine source, weight, candidate, sample count, random seed or horizon changed.

All four complete public JSON responses match their original HF receipts after
removing elapsed-time fields, including the individual continuation receipts.
The successful replays total **96 uncapped continuations / 17,802 continuation
neural decisions**, and 28.85 seconds locally:

| Component | Share of profiled local wall time |
| --- | ---: |
| ONNX session execution | 54.83% |
| Rollout engine, serialization, communication and pool coordination | 38.23% |
| Neural batch preparation / postprocessing | 4.07% |
| Baseline preparation and other Node calls | 1.92% |
| Other Python work and process startup | 0.95% |

The ONNX timer is nested inside batch prediction; the table subtracts it from
batch overhead so time is not counted twice. Engine-pool time includes waiting
for JavaScript and transport/serialization, not exclusively JavaScript CPU.
These are **four early two-player positions on the local research host**, not
the AMD 8840U, a GPU comparison or a representative six-player latency estimate.
They show that both inference and engine/communication costs deserve attention;
they do not establish that a Rust rewrite or GPU migration is the best change.

## Compute implication and limits

The current pilots use four game workers. HF documents `cpu-upgrade` as eight
vCPUs / 32 GB RAM ([official Jobs configuration](https://huggingface.co/docs/hub/jobs-configuration)).
The completed job's 3.59-core workflow average is consistent with that worker
limit and a final-game tail. It is not a measurement of instantaneous CPU
utilization or proof of a particular speedup.

After all six original pilots finish, use their measured six-player peak memory
and worst game durations to size the next batch. Testing eight concurrent games
on that CPU flavor is a plausible first throughput experiment, with unchanged
policies and per-game settings. It is not admitted or launched here. A GPU test
would additionally need enough batched inference and accounting for the remaining
engine/transport cost; this profile alone cannot predict its benefit.
Do not change the current jobs, resubmit them or infer strength from their wins.

## Preserved profiling-harness failure

The first attempt compared a direct Python response with the original public
JSON response. Sampled-world dictionary IDs are integers in Python and strings
after JSON serialization, causing a false mismatch. The saved serialized
response was checked afterward and already matched exactly. No policy or model
defect was found. The corrected profiler compares the saved wire representation.

The first directory, `runs/resource-runtime-profile-v1/`, preserves the original
profiler, plan, input/output and failure explanation; its sibling `.log` preserves
the exception. No component metrics had been saved, so root zero was repeated
for measurement. The successful run is `runs/resource-runtime-profile-v2/`.
Including that initial attempt, profiling used **120 continuations / 22,265
continuation neural decisions**, not just the successful run's 96 / 17,802.
No new complete games, gradients, HF jobs or independent strength data were made.

## Evidence and next action

`strong/resource-runtime-profile-results-v1.json` contains the HF phase summary,
four local profiles, raw-output hashes and interpretation. Its successful
assessment SHA-256 is
`6f506ef84b1f178266db0074a56136563cf3220f4eb925a04f26cf8f96add0d8`.
`strong/resource-runtime-profile-evidence-v1.json` indexes the verified private
HF archive, including both attempts. The original pilot's immutable archive and
v3 source are referenced rather than duplicated. Do not repeat these completed
profiles without a changed implementation or a concrete new measurement need.

This is runtime evidence, not a new candidate or win-rate result. The auction
owner PID 1075760 remained live with all source pins matching at 15:57 UTC:
539 audited / 603 submitted / 648 selected jobs. Finish the unchanged full
auction comparison before choosing the next strategy study. Collect the exact
original resource handles; keep the final-test seeds unused. Research is active.

The **39-file profiling archive** was uploaded and downloaded successfully at
private model revision `a2874ce01ef24b454775d162372c392a8243ac73`,
`archives/resource-runtime-profile-evidence-v1.tgz`, SHA-256
`1a2f315819981bac8116bb83bcc248e1e8c29292686e4c3f8ad0188e25d1cd89`.
The corrected atomic two-player pilot has since also passed independent audit;
its exact collection receipt is saved in the experiment ledger. Two original
pilots / 16 games are verified; the other four were RUNNING at 15:57 UTC.
