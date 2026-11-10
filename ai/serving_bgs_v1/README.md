# Private Node-only BGS integration v1

**Experimental engineering artifact, not a BGS release or a replacement for the default bot.**
No BGS version was uploaded, published, activated or changed. Private model/package
bytes and the copied platform host are excluded from Git. Neither replica was
selected as a winner, trained, manually edited, quantized or ensembled.

This directory extends the completed, immutable [`../serving_v1`](../serving_v1/README.md)
prototype to the actual platform-facing `moveAI(state, player)` contract. It does
**not** replace the synchronous atomic `engine.moveAI`, the original wrapper, or
dropped-player recovery. Both private artifacts preserve every original wrapper
export and replace only their own `moveAI`; `aiStatus` is private test observability.

## Readiness boundary

-   Offline npm-shaped installation with `--ignore-scripts`, target-Node numerical
    parity and the unchanged BGS host/protocol are tested independently for both roles.
-   These are integration tests, not new evidence of playing strength. The 16-case
    targeted matrix covers four maps, player counts 2–6, both variants and both bidding
    modes; it is **not** their complete Cartesian product.
-   **Exact production sandbox qualification remains blocked.** Neither this workspace
    nor the one remote admission job could create the required namespaces/delegated
    cgroups. Observed RSS, threads and latency do not establish enforced resource limits.
-   Actual BGS scheduler, database locking/persistence, duplicate scheduling, retry
    policy, production deployment and human playtesting have not been exercised.
-   Timers cannot preempt synchronous engine work/native execution. The external host
    kills all its pending calls on a timeout. No durable CAS/exactly-once claim is made.
-   Worker JS streams are discarded, but native writes to process fd 1/2 can bypass
    those listeners. `test_native_boundary.cjs` demonstrates this boundary with harmless
    markers. This is **not** a claim of native-output isolation; no tensors/game state
    are intentionally logged. The test client retains byte counts, not raw host stderr.

See [`results-v1.json`](results-v1.json) for final artifact identities, test counts,
measurements, adverse development evidence and preserved source/checkpoint hashes.

## Runtime and identities

The frozen research prototype pins Node **24.20.0**. Platform source inspected at
`boardgamers-mono@735f8e6804704572e8042b886cf2af3d9753d550` instead pins the security
release **24.22.1**. Its last runner/host update was
`ebb37db861675bf4d0ea33dad7c0ef3604edf713`.

Three identities are deliberately distinct:

1. Original research/export provenance:
   `8197fb7e35ed25a924d75e99eafcc140827b46ab441341bb14cd398c832b9f93`.
2. New `manifest.json`: 56 frozen JS/JSON engine/helper files, exact checkpoint
   metadata, original export identity and explicit runtime versions. Development
   loading permits only Node 24.20.0 and 24.22.1; packaged entry requires **24.22.1,
   Linux x64**. No Python/TypeScript/checkpoint files are needed in the artifact.
3. Generated `runtime-manifest.json`: exact dependency/native/model/runtime bytes,
   explicit role and private package identity. The generated ESM entry contains its
   literal SHA-256 and checks the exact tree **before importing** any game/native code.
   Unlisted dependency or extensionless-module shadows are rejected too.

`adapter.cjs`, `deadline.cjs` and `onnx_worker.cjs` are byte-identical ports of v1.
`onnx.cjs` changes only the export-provenance comparison, plus comments clarifying
that distinction and the native-output boundary. Model math/menus/transport are
unchanged. Old guards and old evidence were not weakened or rewritten.

The export manifest is pinned to
`8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543`.
Both unchanged float32 ONNX models are included in each artifact; its explicit role
selects one, never an ensemble. Runtime dependencies are `onnxruntime-node` and
`onnxruntime-common` **1.31.1**, `lodash` **4.17.21**, `seedrandom` **3.0.5** and
`delaunator` **4.0.1**. CPU inference uses one intra-/inter-op thread and sequential
execution. The Linux x64 native binding/shared library and licenses are materialized,
not pnpm links. Installer-only ORT dependencies are not shipped or executed; the
actual offline npm installation validates this pruned runtime payload.

One entry import creates one runtime singleton with one lazy/coalesced worker and
at most eight active calls. Every call clones its input and owns an opaque, random
plan binding/revision zero, unrelated to platform game IDs or database revisions.
Learned Auction/Building decisions and fixed teacher-v2 phases produce one full turn;
the unchanged wrapper applies it, retaining clocks, automation and legal boundaries.
Unsupported scope avoids ONNX. Startup/inference failures open a sticky fallback
circuit with no respawn loop and discard the whole speculative plan before heuristic
fallback. Core/package corruption fails closed. Thus a missing packaged model at
**import** is fatal integrity failure, whereas an authenticated runtime's operational
startup/inference failure can fall back. Fixed phases can still execute normally
while the model circuit is open.

## Reproduce privately

Prerequisites: retained authenticated ONNX export and reference fixtures, installed
engine/new-tooling dependencies, GNU tar, official Node 24.22.1 Linux x64 and its npm.
Tests also use actual Node 24.20.0 for rejection checks. No global Node switch is
necessary. Builder tests require root, UID 65534 or passwordless sudo for the narrow
filesystem/readability check; that check is not a container test.

```sh
# Only the isolated tooling dependencies; never engine prepublish/build workflows.
pnpm --dir ai/serving_bgs_v1 install --ignore-workspace --ignore-scripts

# Set absolute paths to an already installed, checksum-verified target Node/npm.
NODE22=/absolute/node-v24.22.1-linux-x64/bin/node
NPM22=/absolute/node-v24.22.1-linux-x64/lib/node_modules/npm/bin/npm-cli.js

"$NODE22" --test ai/serving_bgs_v1/test_*.cjs
python3 -B -m unittest discover -s ai/serving_bgs_v1 -p 'test_*.py'

# Explicit role and NEW destination required. Repeat separately for replica2.
node ai/serving_bgs_v1/build.cjs --replica replica1 \
  --models ai/runs/serving-prototype-v1/onnx-final --output /private/new-build-r1

# NEW isolated games directory, no lifecycle scripts, network fetches or user npm config.
cd /private/new-games
# An explicit project root prevents npm from walking up to an unrelated package.json.
printf '{"name":"private-engine-test","version":"0.0.0","private":true}\n' > package.json
# Create two distinct empty config files in this NEW directory (npm rejects one path used twice).
touch empty-user.npmrc empty-global.npmrc
"$NODE22" "$NPM22" install --offline --ignore-scripts --save-exact \
  --no-audit --no-fund --userconfig="$PWD/empty-user.npmrc" --globalconfig="$PWD/empty-global.npmrc" \
  --cache=/private/new-empty-cache \
  'pg-test-r1@file:/private/new-build-r1/powergrid-private-ai-replica1-0.0.0-test.1.tgz'
```

The builder normalizes file/directory modes, tar ownership and timestamps; tests
compare independent builds under different umasks. Keep outer staging directories
private even though mounted package contents must be readable by UID 65534.
`build.json` binds source, entry, manifest and tar; install into a clean tree and
retain/verify this tar identity. The entry is the trust root, not a signature against
an administrator who can replace the entry and its manifest together.

Stage the three **unchanged** upstream files outside Git: `host.ts`,
`host-protocol.ts`, `analysis-adapter.ts`. Their expected hashes are in
`conformance.cjs`; no platform source is vendored publicly here. The host dynamically
imports named ESM exports without default-object normalization, awaits Promise
results, JSON-round-trips them, and handles concurrent requests. The client launches
it with empty environment, cwd `/`, `--max-old-space-size=400`, 20-second readiness
and 10-second calls. It keeps stdin open until responses finish; EOF ends the host.

From this worktree, with all paths absolute and outputs new:

```sh
"$NODE22" ai/serving_bgs_v1/parity.cjs --package /private/new-games/node_modules/pg-test-r1 \
  --fixtures ai/runs/serving-prototype-v1/fixtures-final.json \
  --reference ai/runs/serving-prototype-v1/reference-final.json --output /private/parity-r1.json
"$NODE22" ai/serving_bgs_v1/conformance.cjs --node "$NODE22" --host /private/upstream-host \
  --package /private/new-games/node_modules/pg-test-r1 --output /private/conformance-r1.json
"$NODE22" ai/serving_bgs_v1/playthrough.cjs --node "$NODE22" --host /private/upstream-host \
  --package /private/new-games/node_modules/pg-test-r1 --output /private/playthrough-r1.json
```

Targeted conformance includes 96 full turns, 2/4/8 concurrency bursts, immutable
inputs, named export parity, JSON/toSave/replay, sealed logs, clocks, unsupported
hidden-money/Italy fallback, repeated independent proposals and fresh-host restart.
Diagnostics prove learned inference actually occurred rather than silently passing
through fallback. The separate bounded eight-game playthrough uses fresh engineering
seeds and records no winner comparison. Persistent replay compares all JSON including
clocks; original `wrapper.replay` intentionally clears transient `pendingMessages`,
whose `{messages, data}` drain is tested separately. These are not old study replays.

## Production gate still to run

Source-defined image:

```text
docker.io/library/node:24.22.1-bookworm-slim@sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae
```

A capable approved rootless Podman host must run that image with the source-defined
`--network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges`,
`--user=65534:65534 --memory=512m --memory-swap=512m --cpus=1 --pids-limit=64`,
read-only installed `node_modules` and three-file `/host` mounts, no forwarded app
secrets, and `node --max-old-space-size=400 /host/host.ts <installed-entry>`.
Verify actual controls/negative enforcement as well as native loading, cold/warm
turn deadlines, concurrency and restart. Do not substitute RSS watchdogs/CPU affinity
for cgroups or call an ordinary HF Job a sandbox pass.

One separately authorized, credential-free HF `cpu-basic` admission job
`6af32a3c9737d9a9e090acb9` ran the pinned image with a **600-second cap** and completed
in **7 reported total seconds** (including scheduling). No model, secrets, ports or
SSH were supplied. It found namespace denial and read-only cgroups; there was no
retry, flavor escalation or model workload. The source/receipts/log are hash-bound
in results. A validation script initially rejected the backend's empty-list secrets
representation; inspecting its type/length reconciled it as empty, without resubmission.
The advertised $0.01/hour rate gives roughly $0.00167 for the requested ten-minute
ceiling, subject to provider billing granularity; this is not an invoice.

The Python launcher/tests are offline control-plane tooling only. **Production
inference is Node-only**; no Python interpreter or Python files are in the engine tar.
Do not run `launch_admission.py --submit` again: its durable exclusive intent is
consumed, including in an unknown-outcome failure. It is independent of all completed
study launchers/budgets, which must not be reset or reused.

BGS upload URLs are public-readable even for private games. Do **not** use BGS
uploads as private artifact storage or dispatch existing publication workflows.
A future release needs separate authorization and the repository's release-branch/
mirror delivery procedure. This task delivers source/evidence on the feature branch only.
