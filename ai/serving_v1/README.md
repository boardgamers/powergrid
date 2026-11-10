# Fixed-replica Node serving prototype v1

**Node-only inference. Python is used only for offline export and reference checks.**
This is an opt-in, headless development prototype—not an installed BGS engine,
public bot, browser playtest, or replacement for either existing `moveAI`.

Both audited replicas remain explicitly selectable. Neither was selected as a
winner. No weights were manually edited, fitted, quantized, or promoted. The
original checkpoints and completed stress-study evidence are unchanged.

## Local validation

[results-v1.json](results-v1.json) records the actual checks, artifact/source hashes,
review corrections, and limitations:

-   **160/160 exact selected-index matches**: 80 fresh public tensor positions for
    each replica, comparing frozen PyTorch, direct Node ONNX, and the Node worker.
    These cover four maps, 2–6 players, both rulesets and both auction modes. There
    are 48 normally learned positions and 32 additional fixed-phase tensor checks;
    the actual adapter does **not** call the neural model in those fixed phases.
-   Maximum absolute logit differences: **0.00000930 / 0.00001025**. The check uses
    `abs <= 2e-5 + 1e-6 * abs(reference)` and additionally requires exact argmax.
    This is not universal bitwise equality or a guarantee for every unseen near-tie.
-   **192 committed full-turn checks** (96 per replica), replay/JSON round-trips and
    duplicate-commit checks; **zero fallbacks** in the successful model smoke run.
-   **51 Node tests**, **45 Python export/reference tests**, and **366 unchanged
    engine tests** passed. The Python suite also ran without Torch/ONNX: 27 passed,
    18 dependency/private-model tests skipped. Those skips are not parity evidence.
-   Final local worker round-trip p95 was approximately **3.66 / 3.11 ms**; full-turn
    p95 **10.54 / 11.13 ms**. Worker/session startup was **89.9 / 46.9 ms**. The
    benchmark process peaked around **248 MiB RSS**, including fixtures, a direct
    ONNX session, a worker and previous allocations. Earlier development timings
    were slower and are retained in the result record. These are **not target-host
    benchmarks**: the host was unconstrained, caches were warm, and the second role
    reused the process. They do not establish concurrency or 512 MiB compliance.

These are engineering observations, not additional games in the frozen strength
study, new independent win observations, human-strength evidence, or tuning data.
The fixture generator stops at targeted positions and does not compute winners.

## Runtime architecture

-   `onnx.cjs` authenticates an explicitly supplied export-manifest SHA and the
    selected model's size/SHA **before** native parsing, then loads those same bytes.
    ORT Node **1.31.1**, CPU execution, float32, sequential execution and one
    intra-/inter-op thread are pinned. Models are **621,002 bytes each**.
-   `onnx_worker.cjs` receives **public tensors only** in a Node worker thread.
    No Python interpreter, subprocess, HTTP service, network access, raw game state,
    deck, game seed, hidden log or atomic-action payload is needed for inference.
-   `ReplicaBot` preserves the frozen composition: full-menu expert-v2 inputs and
    greedy first argmax in multi-action Auction/Building; geographic teacher-v2 for
    Resources/Bureaucracy; direct forced moves. It never sorts, prunes or reconstructs
    the action menu. Legal payloads remain on the authoritative Node side.
-   Planning runs on a detached state, ends at the **first actual turn boundary**,
    and applies the full buffer using unchanged `wrapper.move` on another clone.
    Private plan identity, game/revision/seat, full normalized state and menu binding
    prevent stale or caller-fabricated plans from being applied.
-   On unsupported scope, inference failure, malformed output or deadline expiry,
    the entire speculative plan is discarded. A fresh, bounded turn uses the
    unchanged **production atomic heuristic**. Diagnostics identify fallback;
    teacher-v2 fixed phases are not mislabeled as fallback. Failure to finish the
    fallback turn throws; this adapter never force-commits. Wrapper application
    stamps one authoritative time for the buffer, rather than the default bot's
    separate timestamps for each randomly chosen atomic move.
-   `MemoryHost` demonstrates post-await CAS, duplicate coalescing, retained receipts
    and monotonically advancing revisions—including undo/replacement. Visible log
    length is never a revision: sealed bids can commit without changing it.
    **This is single-process memory, not durable or production exactly-once storage.**
    Restart examples require retaining both state and revision. Old receipts are
    historical acknowledgments, not snapshots of the latest game state.

Default bounds: 8 outstanding callers/plans, 64 cached decisions/plans/receipts,
64 local games, 4 MiB request, 8 MiB JSON state, 4 MiB model, 128 atomics/turn,
1 s inference, 3 s learned planning plus a separate 1 s fallback budget, and 10 s
worker startup. Limits are entry/shape bounds, not a measured aggregate memory
budget. Synchronous feature/engine work is cooperatively checked, not preempted.
Worker termination is lifecycle isolation, **not a hostile-code sandbox or a
hard native cancellation guarantee**. A poisoned worker is not silently restarted.
`OnnxPolicy.evaluate()` is a direct parity API; use `OnnxTransport` for bounded
request queuing and deadlines.

Learned scope is deliberately narrow: Germany, USA, France, UK & Ireland;
2–6 players; Original/Recharged; open/sealed; visible money and the pinned standard
automatic setup. Hidden money, alternate decks, custom drafts/maps and rule-option
overrides use observable heuristic fallback instead of claiming learned support.

## Install and reproduce locally

Use the authenticated engine **2.0.22** compiled tree and pinned research sources
already present in this worktree. `manifest.json` checks all 42 compiled JS files
and the relevant frozen feature/model sources. Missing or changed files fail
closed. Do not rebuild over or alter retained study artifacts to bypass a guard.
This development layout verifies Python **source bytes** for provenance but does
not execute Python during serving; a minimal production bundle is separate work.

```sh
# Isolated package: do not change the root/engine locks or run CUDA installers.
pnpm --dir ai/serving_v1 install --ignore-workspace --ignore-scripts --frozen-lockfile
node --test ai/serving_v1/test_*.cjs
```

Real-model Node tests skip if no local exports exist. Set `PG_ONNX_TEST_MODELS` to
a freshly exported directory to exercise them; the default is
`ai/runs/serving-prototype-v1/onnx-final`.

Offline export needs the existing pinned CPU Python environment. **Do not install
new packages into `ai/.venv` or `ai/.venv-reference`.** See
[requirements-export.txt](requirements-export.txt) for the isolated additions.
No model download is performed; both private checkpoint paths must be explicit.

```sh
DEPS=$(mktemp -d /tmp/pg-onnx-export-deps.XXXXXX)
uv pip install --python ai/.venv/bin/python --target "$DEPS" \
  --no-deps --no-cache -r ai/serving_v1/requirements-export.txt
RUN=$(mktemp -d "$PWD/ai/runs/serving-prototype-local.XXXXXX")
R1=ai/runs/multimap-expert-replicas-20261109-v1-continuation-r1/audit/restored/expert/best.pt
R2=ai/runs/multimap-expert-replicas-20261109-v1-continuation-r2/audit/restored/expert/best.pt
node ai/serving_v1/fixtures.cjs > "$RUN/fixtures.json"
PYTHONPATH="$DEPS" ai/.venv/bin/python -B -m ai.serving_v1.export_onnx \
  --replica1-checkpoint "$R1" --replica2-checkpoint "$R2" \
  --output "$RUN/onnx" --reference-fixtures "$RUN/fixtures.json" \
  --reference-output "$RUN/reference.json"
SHA=$(sha256sum "$RUN/onnx/export-manifest.json" | cut -d' ' -f1)
node ai/serving_v1/check.cjs --models "$RUN/onnx" --manifest-sha "$SHA" \
  --fixtures "$RUN/fixtures.json" --reference "$RUN/reference.json" \
  --output "$RUN/check.json"
PG_ONNX_TEST_MODELS="$RUN/onnx" node --test ai/serving_v1/test_*.cjs
PYTHONPATH="$DEPS" ai/.venv/bin/python -B -m unittest \
  ai.serving_v1.test_worker ai.serving_v1.test_export -v
```

Export/output paths must be new; existing artifacts are never overwritten. Python
reference output binds the exact raw fixture bytes, and the Node harness compares
those observations to independently regenerated fixtures. Each export retains the
loaded model's original fingerprint and rejects weight/scalar/mode mutations
before/after export and reference inference. This protects accidental mutation,
not hostile Python code deliberately replacing private fields.

For the checked local final bundle, the **trusted export-manifest SHA** is:

```text
8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543
```

An application must pin the reviewed bundle SHA in trusted configuration. Merely
hashing an arbitrary uploaded manifest does not authenticate a model. The original
checkpoints and ONNX exports remain outside Git; this change does **not** publish
private weights. Source/tests/locks/results are committed, and the exports are
reproducible locally from the retained private checkpoints.

### Host API sketch

```js
const { OnnxTransport } = require('./onnx.cjs');
const { ReplicaBot, MemoryHost } = require('./adapter.cjs');
// Explicit trusted configuration: replica must be 'replica1' OR 'replica2'.
const transport = new OnnxTransport({ replica, modelDirectory, exportManifestSha256 });
await transport.ready;
try {
    const bot = new ReplicaBot({ replica, transport });
    const host = new MemoryHost();
    host.add(gameId, committedState, revision);
    const receipt = await host.play(bot, { gameId, revision, player });
    const next = host.snapshot(gameId);
    // receipt.diagnostics reports fallback; next is the authoritative local state.
} finally {
    transport.close();
}
```

## Remaining before a controlled BGS playtest

1. Package the pinned Node-only runtime, model assets and appropriate serving
   manifest into an isolated private engine artifact/version. This worktree-based
   prototype is not that package. Validate CPU/native dependencies in the actual
   Node 24 bookworm-slim image; do not rely on development host availability.
2. Test within BGS's actual network-isolated, read-only **512 MiB / 1 CPU / 64 PID**
   host, including cold import, worst menus, concurrent games, worker teardown,
   idle restarts and its 10 s call / 30 s startup limits.
3. Integrate the platform's `moveAI(G, seat) -> committed state` contract. It does
   not supply this local host's game ID/revision. Check actual locking, persistence,
   failure rescheduling and undo; do not transfer local CAS claims to BGS by analogy.
4. Add explicit private playtest access and supervised human sessions. Keep both
   replicas' identities separate and public/default bot behavior unchanged until
   a separately approved rollout with monitoring and rollback.

The strength evidence plus local Node serving checks justify these next engineering
steps. They do **not** make the bot BGS-playtest-ready or release-ready yet.
