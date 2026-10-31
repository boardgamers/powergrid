# Target reliability and learner generalization — 31 October 2026

## Completed sealed-bid assessment

The original mini-PC run (supervisor **961705**) completed at **03:52:37 Paris**,
31 October, in **3h29m41s**. Both queues exited successfully. All **6,160 original
continuations / 40 components / ten roots** were collected and independently
audited: exact terminal tie credits, action coverage, source pins and paired
sampled-world hashes, with **zero outer or nested caps**. No retries or replacements.
The mini-PC run is terminal; do not relaunch it.

The protocol selected a bid on one 28-world half and evaluated on the other,
in both directions, retaining all ten training roots across 2–6 players and both
editions. The reported quantities below are mean paired **sampled terminal-credit
margins**, multiplied by 100 for readability. They are **not game win-rate gains**.

| Selection population | Held-out neural population | Held-out reference search |
| --- | ---: | ---: |
| Neural population | +5.89 points | +1.52 points |
| Exact reference search | +0.89 points | +0.18 points |
| Equal mixture | +5.89 points | +0.54 points |

For reference-search selection evaluated against reference search, one root has
a positive cross-fit mean, two negative and seven zero. The expensive method
therefore supplies no convincing repeatable gain on this small diagnostic. This
does not establish that bidding cannot improve: there is only one root per
count/rules stratum, and the two cross-fit directions share roots. Do not count
20 directions as 20 independent positions or promote a selector from these data.

A retrospective alternative payoff—the fraction of opponents outranked using
exact terminal ordering—also gives little improvement against reference search
(+0.18 points for search-selected actions). This was inspected after the original
results and is **not** a selected training objective or confirmatory finding.
All adverse results and zero margins are retained.

Reports: `strong/sealed-target-quality-complete-v1.json` and
`strong/target-generalization-analysis-v1.json`. Original raw outputs:
`runs/sealed-target-quality-v1/collected`. The original input/launch archive is
`strong/sealed-target-quality-start-evidence-v1.json`. The new completion/recovery
archive descriptor is `strong/target-generalization-evidence-v1.json`.

## Why the next step changes the learning method

Reading the original, hash-verified learning curves showed that **all 16 neural
fits** reduced training mean squared error but ended with higher validation error.
Training error fell from roughly 0.031 to 0.010–0.012; validation error rose from
roughly 0.028–0.029 to 0.033–0.035. All final-epoch validation action gains were
negative. Earlier checkpoint selection prevented deploying those final epochs,
but the retained candidates still failed the prior game screen.

This is evidence of overfitting in that training recipe, not a lack of optimizer
updates. It does not isolate a cause: representation, regularization, noisy
long-horizon labels and opponent mismatch may all contribute. The previous
nomination-only neural candidate iteration remains closed; its deferred 35 game
shards remain unsubmitted. More epochs on those models is not the next action.

## Current bounded HF learner probe

One HF **L4** job, submitted **11:07:27 Paris**, 31 October:
**`6ae5bddf0e0338d1bb7d1fe6`**, name `pg-target-learner-probe-v1`.
Estimate **15–30 minutes plus queue/setup delay**, provisional for this new learner.
Suggested ping **11:45 Paris today**. One-hour job timeout, no automatic retries
or follow-on work. No new mini-PC simulations are running from this work.

The experiment trains four regularized XGBoost models: fixed depths **3 and 6**,
two fixed seeds each, at most 500 boosting rounds, with stopping after 40 rounds
without improvement on internal tuning RMSE. Both seeds and both depths are
retained. Their fixed mean ensembles are diagnostics, not selected game policies.
This is a different learning recipe, not a controlled proof that architecture
alone caused the previous failure.

It reuses the **5,770 current-engine, independently verified nomination targets**.
Whole source games and identical public-state hashes stay separate:

- **3,598 fit roots**, from original training deals excluding 11 and 13.
- **728 tuning roots**, from training deals 11 and 13 only.
- **1,444 legacy validation roots**, scored after fitting; these have previously
  been used in research, so they are not an untouched final test.

The 1,522 numeric inputs use existing public state, candidate and parent action
features, and their differences. They exclude target values, root/deal/seed IDs,
opponent identity and policy eligibility/shortlist flags. Negative and uncertain
targets remain; weights normalize to equal total weight per root. The parent
advantage is exactly zero. Routing uses the fixed 0.025 margin. No thresholds or
depths are tuned on legacy validation results.

Training runs only on the HF GPU. Saved numeric trees are also checked against
an independent NumPy CPU evaluator, both in the job and again during collection;
all action choices must match. Four focused tests cover split isolation,
label/flag exclusion, legal routing and numeric tree boundaries. The complete
real-data preflight passed with zero gradients or simulations. GPU invocation
follows the [official XGBoost interface](https://xgboost.readthedocs.io/en/release_2.1.0/gpu/index.html).
Original neural model files and serving behavior are unchanged.

Design: `strong/target-learner-probe-design-v1.json`.
Private source descriptor: `strong/target-learner-probe-source-v1.json`.
Original job receipt: `strong/target-learner-probe-launch-v1.json`.
The source archive was downloaded by immutable revision and SHA-verified before
launch; actual HF image, command, environment, flavor and timeout were verified.

```sh
PYTHONPATH=ai/strong ai/.venv/bin/python -u -B ai/strong/manage_target_learner_probe_v1.py status
```

Once terminal and successful, use `collect` instead of `status`. It preserves the
original job log/bucket receipt, verifies the raw archive and hashes, re-evaluates
all four saved trees independently on CPU, checks selected rounds and recomputes
metrics. The final report is `strong/target-learner-probe-results-v1.json`.
Inspect an existing final report before repeating collection. For failure or a
missing receipt, retain original logs and partial evidence; do not resubmit or
silently replace it. `prepare` and `launch` must not be repeated.

Next decision: assess generalization of the fixed recipes and whether it warrants
fresh, independent gameplay validation or a broader data/target redesign. A good
legacy target-fit result alone does not establish strength, solve the sealed-bid
opponent problem or justify promotion. No final seeds used, model qualified,
objective/automation created, production deployment or GitHub comment.
