# Power Grid AI — research resumed, 27 October 2026

The human explicitly requested “do ai research”. This supersedes the research
pause, but does not alter the original failed pilot or qualify a model. The broad
goal is active. Production Power Grid is separate and untouched.

## Where the research stands

`frozen-1` is the best verified development reference. Germany four-player win
share against geographic search improved from **30.859% to 51.563%**; Recharged
sealed improved from **15.625% to 39.063%**. These are development measurements,
not reserved final tests. Coverage includes 2–6 players, original/Recharged and
open/sealed auctions; other maps are not qualified. Public player money and the
other players' economic state are available to the policies.

The actual AMD 8840U matched 10,212 model requests: median 4.3–5.9 ms, p95
7.0–8.8 ms. That is model-only inference, not a whole hybrid-search decision.
Broader auction/resource search additions regressed in important settings.
The learned-opponent training recipe did not establish better overall fidelity;
do not spend more training on the same recipe without a new hypothesis.

Next research direction remains the frozen conservative auction comparison:
only replace the model move when the pooled margin strictly exceeds 1/8 and
each included opponent population has a nonnegative margin. The 10,080-game
development comparison is still unadmitted and unlaunched. Full-game runtime
validation of the corrected artifact comes first. No reserved final seeds used,
new candidate qualified or AI deployed.

## Recovered failure and narrow fix

Original job `6addea04046eb82b1ece4fb1` failed at episode 5, request `5:21`.
All 1,502 original source manifest entries were verified. Replaying the original
episode using the 20 recorded learner moves and deterministic original opponent
search matched all 20 saved public states and ordered legal menus, excluding
only wall-clock bookkeeping. The next public request was reconstructed; it was
not itself saved in the original failure archive.

The original frozen policy reproduced the assertion in
`opponent_surrogate_training_v1.inputs`. In round 2, Recharged sealed, prior
bidder 2 initiated plant 26 with exactly 26 money. Its only legal action was
`Bid 26`. The schema correctly marked it non-strategic with no shortlisted
action, but the opponent runtime sent it to a strategic-choice model. Another
prior actor could only pass.

Two runtime files were corrected in a fresh artifact:

- `opponent_surrogate_policy_v1.py`: validate forced observations and choose their
  sole action directly; infer only the other rows, preserving batch order.
- `surrogate-opponent-continuations-v1.cjs`: accept the unique legal prior bid or
  pass without requiring a strategic shortlist; all genuine choices still need
  to be legal and shortlisted.

The encoder, training validator, neural weights, eight worlds per population,
threshold, population mixture and outside-auction behavior are unchanged. The
original artifact and reports are immutable. The corrected runtime is a new
identity, not a relabelled passing original.

## Verification

- **Five Python tests:** exact recorded forced bid, forced pass/no-moves routing,
  malformed inputs, strict training validation, and **382 saved strategic
  predictions identical to the original four-member model**, interleaved with
  383 forced actions.
- **Six Node tests:** recovered forced bid/pass accepted; invalid replacements
  and nonshortlisted genuine choices rejected; **80 historical population
  contexts unchanged**, 60 strategic contexts preserve public-only inputs,
  worker partition invariance, oracle equivalence and transport failure handling.
  The 480 deliberate short-horizon caps in these engineering tests are expected
  test cases, not the recovered request's continuations.
- The corrected standalone service completes request `5:21`. The independent
  verifier is byte-identical to the original, loaded beside the new pinned worker
  so its integrity check uses the new worker hash. It recomputed all terminal
  credits, paired worlds, exact rational margins and selection: **96
  continuations, zero outer/nested caps; 11,184 neural and 6,252 surrogate
  decisions**. It retains the model's `Pass`: alternatives had pooled +1/16,
  below the strict +1/8 threshold. These are simulated credits, not calibrated
  probabilities or evidence of playing-strength improvement.
- Observed 26.01 seconds for this one local cold request while Node tests also
  ran. This is neither resource admission nor an 8840U latency benchmark.
- **Zero new HF jobs, gradients or fresh strength games** in this recovery.
  Prefix replay and this diagnostic request do execute engineering continuations.

Initial test scaffolding assumed an unrelated player was a prior bidder; it was
corrected to use the actual prior-pass actor for the nonshortlist rejection
test. Initial audit loading from the old tree correctly rejected the new worker
hash; loading the byte-identical independent verifier from the new artifact
passed. All failed attempt logs are retained with the evidence.

## Identities and recovery

| Item | SHA256 |
| --- | --- |
| Original source tarball | `99227f1fc4bd8976e168db88f2c330eeff9947d320526d83dffaeff59b492328` |
| Original runtime manifest | `dcb23342088ae91379374827b45c0845d1b9494b31682fca55e3ac047d1e2f55` |
| Corrected runtime manifest | `a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619` |
| Corrected dual policy descriptor | `78dbcdff1a61bf3affb61d800f8a28707ef9c32fab9919ef751adcde8f8e0e39` |
| Recovered request | `03234e913cc88e8061b8d486c76c8d18d20b9d960740d51111dace6a9dacbf75` |
| Corrected raw response | `b0b703ed3be190d8208af52bc3618af092f41971023c8ef233ffd0cdb8642e46` |

The machine-readable result is
`strong/conservative-auction-forced-prior-results-v1.json`. Its companion archive
descriptor is `strong/conservative-auction-forced-prior-evidence-v1.json`, created
only after the private HF archive is uploaded and downloaded/hash-verified.
It records the immutable archive revision/hash. Evidence references the original
source and all four raw job archives instead of duplicating or rerunning them.

The new artifact is `runs/conservative-auction-forced-prior-v1/artifact`;
`derivation.json` records the two code deltas and updated descriptor pins.
Rebuild only in a fresh directory from the original pinned source and archived
patches; every manifest hash must match the new manifest. Do not overwrite a
prepared runtime or repeat a replay/upload with an unresolved intent.

Tools (all use `ai/.venv/bin/python -B`):

- `strong/replay-conservative-auction-failure-v1.py`: recover the original prefix.
- `strong/diagnose-conservative-auction-request-v1.py`: reproduce original error.
- `strong/verify-conservative-auction-forced-prior-v1.py prepare|replay|audit`:
  derive and validate the new artifact in separate interpreters.
- `strong/archive-conservative-auction-forced-prior-v1.py --archive`: verified
  evidence archival only; no job submission.

Original jobs remain **3 completed / 1 failed**, **40 fully audited games** and
**23 completed receipts from the failed shard**. The original 64-game run remains
incomplete. Original handles, costs and archives remain in
[the 25 October handoff](HANDOFF-2026-10-25-PAUSED.md) and
`strong/conservative-auction-runtime-results-v1.json`.

Former development coordinator PID 1061599 and collector PID 1146868 remain
stopped; preserve the development STOP marker. Do not restart old owners.
Continue with a separate source identity, launch guard and measured HF runtime
pilot for the corrected code, followed by independent full-game/resource auditing.
Do not use this single-request success to bypass the development admission gate.
