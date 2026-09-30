import copy
import unittest
from arena_statistics import validate_pairs


def rows_for(n):
    return [
        dict(
            gameSeed="test",
            seat=s,
            variant=v,
            sealed=b,
            playerCount=n,
            roles=["learner" if i == s else "economic" for i in range(n)],
            value=[1.0 if i == 0 else 0.0 for i in range(n)],
            win=float(s == 0),
            truncated=False,
        )
        for s in range(n)
        for v in ["original", "recharged"]
        for b in [False, True]
    ]


class PairingTests(unittest.TestCase):
    def test_every_count_and_rejection_of_malformed_evidence(self):
        for n in range(2, 7):
            rows = rows_for(n)
            validate_pairs(rows, n)
            cases = [rows[:-1], rows + [rows[0]]]
            for field, value in [
                ("playerCount", 7),
                ("seat", n),
                ("value", [1]),
                ("win", 0.5),
                ("roles", ["learner"] * n),
            ]:
                broken = copy.deepcopy(rows)
                broken[0][field] = value
                cases.append(broken)
            for broken in cases:
                with self.assertRaises(ValueError):
                    validate_pairs(broken, n)


if __name__ == "__main__":
    unittest.main()
