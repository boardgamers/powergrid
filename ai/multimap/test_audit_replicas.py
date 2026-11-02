"""Offline invariants and corruption tests for the independent replica auditor."""
import copy
import math
from types import SimpleNamespace
import unittest

import numpy as np
import audit_ppo
import audit_replicas as audit
from residual import PROTOCOL
from rollout import plans


class ReplicaAuditTests(unittest.TestCase):
    def protocol(self, replica=1):
        value = copy.deepcopy(PROTOCOL)
        value["seed"] += replica
        value["seedNamespace"] += f":replica-{replica}"
        return value

    def test_exact_two_protocol_overrides_and_no_mutation(self):
        frozen = copy.deepcopy(PROTOCOL)
        legacy = (audit_ppo.REVISION, audit_ppo.PREFIX, audit_ppo.SOURCE_REVISION)
        for replica in (1, 2):
            protocol = self.protocol(replica)
            result = audit.verify_protocol(protocol, frozen, replica)
            self.assertEqual(set(result), {"seed", "seedNamespace"})
            self.assertEqual(result["seed"]["actual"], 508 + replica)
        self.assertEqual(PROTOCOL, frozen)
        self.assertEqual((audit_ppo.REVISION, audit_ppo.PREFIX, audit_ppo.SOURCE_REVISION), legacy)
        self.assertEqual(audit.verify_protocol(frozen, frozen, 0), {})

    def test_protocol_drift_or_incorrect_namespace_rejected(self):
        for key, value in (("seed", 510), ("seedNamespace", PROTOCOL["seedNamespace"]),
                           ("targetKl", 0.051), ("selectionMaxMapRegression", 0.11),
                           ("updates", 15), ("players", [2, 3, 4, 5])):
            with self.subTest(key=key):
                protocol = self.protocol()
                protocol[key] = value
                with self.assertRaises(RuntimeError):
                    audit.verify_protocol(protocol, PROTOCOL, 1)
        protocol = self.protocol()
        protocol["newField"] = True
        with self.assertRaises(RuntimeError):
            audit.verify_protocol(protocol, PROTOCOL, 1)

    def test_full_independent_plans_and_nine_disjoint_namespaces(self):
        splits = {}
        for replica in (0, 1, 2):
            protocol = self.protocol(replica) if replica else PROTOCOL
            groups = {}
            for split, count, deals in (("selection", 320, 1), ("confirmation", 960, 2)):
                tasks = audit.independent_plan(protocol, split)
                self.assertEqual(tasks, plans(split, protocol=protocol))
                self.assertEqual(len(tasks), count)
                audit.check_plan_structure(tasks, protocol, split, deals, True)
                groups[split] = {t["seed"] for t in tasks}
            training = []
            for update in range(1, 17):
                tasks = audit.independent_plan(protocol, "train", update)
                self.assertEqual(tasks, plans("train", update, protocol=protocol))
                self.assertEqual(len(tasks), 80)
                audit.check_plan_structure(tasks, protocol, "train", 1, False)
                training.extend(tasks)
            groups["train"] = {t["seed"] for t in training}
            self.assertEqual(len(groups["train"]), 1280)
            splits[str(replica)] = groups
        report = audit.verify_namespaces(splits)
        self.assertEqual(report["pairwiseComparisons"], 36)
        self.assertEqual(report["independentDeals"], 4800)
        self.assertEqual(report["seedOverlap"], 0)
        with self.assertRaises(RuntimeError):
            audit.independent_plan(PROTOCOL, "final")

    def test_cross_run_cross_split_collision_rejected(self):
        with self.assertRaises(RuntimeError):
            audit.verify_namespaces({"one": {"train": {"duplicate"}},
                                     "two": {"confirmation": {"duplicate"}}})
        with self.assertRaises(RuntimeError):
            audit.verify_namespaces({"one": {"selection": {"duplicate"},
                                             "confirmation": {"duplicate"}}})

    def game(self):
        task = audit.independent_plan(PROTOCOL, "selection")[0]
        return dict(spec=task, terminal=True, credit=0.5, steps=50, rounds=10,
                    decisions=15, featureMs=1.0, inferenceMs=2.0, seconds=3.0)

    def test_duplicate_missing_wrong_spec_caps_nonterminal_nonfinite_rejected(self):
        game = self.game()
        tasks = [game["spec"]]
        audit.verify_games([game], tasks, "valid")
        for games in ([], [game, game]):
            with self.assertRaises(RuntimeError):
                audit.verify_games(games, tasks, "corrupt")
        for field, value in (("terminal", False), ("credit", float("nan")),
                             ("credit", 1.01), ("steps", game["spec"]["maxSteps"]),
                             ("rounds", 51), ("decisions", 51), ("featureMs", -1.0)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(RuntimeError):
                    audit.verify_games([dict(game, **{field: value})], tasks, "corrupt")
        wrong = copy.deepcopy(game)
        wrong["spec"]["map"] = "Italy"
        with self.assertRaises(RuntimeError):
            audit.verify_games([wrong], tasks, "corrupt")

    def test_terminal_credit_reciprocal_ties_not_arbitrary_fractions(self):
        game = self.game()
        for credit in (0, 0.5, 1):
            audit.check_terminal_credits([dict(game, credit=credit)])
        for credit in (0.3, 1 / 3, True, float("inf")):
            with self.subTest(credit=credit), self.assertRaises(RuntimeError):
                audit.check_terminal_credits([dict(game, credit=credit)])
        game["spec"]["players"] = 3
        audit.check_terminal_credits([dict(game, credit=1 / 3)])

    def test_equal_cells_not_seat_weighting(self):
        games = [dict(spec={"cell": "Germany|2|original|0"}, credit=1.0)] * 2
        games += [dict(spec={"cell": "Germany|6|original|0"}, credit=0.0)] * 6
        self.assertEqual(audit.recompute(games)["macroCredit"], 0.5)
        self.assertEqual(audit.mean(g["credit"] for g in games), 0.25)

    def metrics(self, score, germany=None, france=None, failures=0):
        return dict(macroCredit=score, failures=failures,
                    maps=dict(Germany=score if germany is None else germany,
                              France=score if france is None else france))

    def test_selection_baseline_eligible_floor_strict_earliest_tie(self):
        candidates = {0: self.metrics(0.5), 4: self.metrics(0.6), 8: self.metrics(0.6),
                      12: self.metrics(0.65, germany=0.39, france=0.91),
                      16: self.metrics(0.6 + 5e-13)}
        update, _, rows = audit.select_checkpoint(candidates, PROTOCOL)
        self.assertEqual(update, 4)
        self.assertTrue(rows[0]["eligible"])
        self.assertFalse(rows[3]["eligible"])
        candidates[4] = self.metrics(0.49)
        candidates[8] = self.metrics(0.5)
        candidates[16] = self.metrics(0.7, failures=1)
        self.assertEqual(audit.select_checkpoint(candidates, PROTOCOL)[0], 0)
        # The map floor is inclusive, not a strict greater-than rule.
        candidates[4] = self.metrics(0.6, germany=0.4, france=0.8)
        self.assertEqual(audit.select_checkpoint(candidates, PROTOCOL)[0], 4)

    def test_unbiased_variance_standard_error_and_invalid_shapes(self):
        stats = audit.stratified_standard_error([[1, -1], [1, -1], [1, -1]])
        self.assertAlmostEqual(stats["stratifiedPairedStandardError"], math.sqrt(1 / 3))
        self.assertAlmostEqual(stats["pairedDifferenceApproxNormal95Interval"][0],
                               -1.959963984540054 / math.sqrt(3))
        constant = audit.stratified_standard_error([[0.2, 0.2]])
        self.assertEqual(constant["stratifiedPairedStandardError"], 0)
        for invalid in ([], [[1]], [[1, 2, 3]], [[1, float("nan")]]):
            with self.assertRaises(RuntimeError):
                audit.stratified_standard_error(invalid)

    def test_paired_clusters_preserve_rotations_and_expose_bootstrap_optimism(self):
        selected, teacher = {}, {}
        for task in audit.independent_plan(PROTOCOL, "confirmation"):
            key = audit.game_key(task)
            selected[key] = dict(spec=task, credit=float(task["deal"] == 0))
            teacher[key] = dict(spec=dict(task, focalTeacher=True), credit=float(task["deal"] == 1))
        paired = audit.paired_confirmation(selected, teacher, PROTOCOL)
        self.assertEqual(paired["aggregate"]["difference"], 0)
        self.assertEqual(paired["aggregate"]["independentDeals"], 240)
        self.assertEqual(paired["aggregate"]["pairedSeatGames"], 960)
        audit.add_standard_errors(paired, selected, teacher, PROTOCOL)
        se = paired["aggregate"]["stratifiedPairedStandardError"]
        self.assertAlmostEqual(se, 1 / math.sqrt(120))
        boot = paired["aggregate"]["pairedDifference95PercentileInterval"]
        normal = paired["aggregate"]["pairedDifferenceApproxNormal95Interval"]
        self.assertLess(boot[1] - boot[0], normal[1] - normal[0])
        # Exact empirical bootstrap variance at n=2 is half the unbiased estimate.
        empirical = np.array([-1.0, 0.0, 0.0, 1.0]).var() / 120
        self.assertAlmostEqual(empirical * 2, se**2)
        self.assertEqual(set(paired["byMap"]), set(PROTOCOL["trainMaps"] + PROTOCOL["transferMaps"]))
        self.assertEqual(set(paired["byPlayers"]), {str(n) for n in PROTOCOL["players"]})
        teacher.pop(next(iter(teacher)))
        with self.assertRaises(RuntimeError):
            audit.paired_confirmation(selected, teacher, PROTOCOL)

    def fake_api(self, size=1, extra=False, stage="COMPLETED"):
        identity = audit.REPLICAS[0]
        names = audit.expected_artifacts() | {"artifacts.json"}
        if extra:
            names.add("ppo/trajectories.pt")
        siblings = [SimpleNamespace(rfilename=f"runs/{identity['run']}/{n}", size=size) for n in names]
        environment = dict(RUN_ID=identity["run"], MODEL_REPO=audit.REPO, WORKFLOW="ppo",
                           REPLICA="1", SOURCE_REVISION="source", SOURCE_SHA256="hash")
        return SimpleNamespace(
            inspect_job=lambda **kwargs: SimpleNamespace(status=SimpleNamespace(stage=stage), environment=environment),
            model_info=lambda *args, **kwargs: SimpleNamespace(sha=identity["revision"], private=True, siblings=siblings))

    def test_exact_allowlist_32_artifacts_and_preflight_size_fail_closed(self):
        self.assertEqual(len(audit.expected_artifacts()), 32)
        for kwargs in (dict(size=audit.BUDGET), dict(size=None), dict(extra=True), dict(stage="RUNNING")):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                audit.inspect_artifacts(self.fake_api(**kwargs), audit.REPLICAS[0])
        inspected = audit.inspect_artifacts(self.fake_api(), audit.REPLICAS[0])
        self.assertEqual(inspected["bytes"], 33)


if __name__ == "__main__":
    unittest.main()
