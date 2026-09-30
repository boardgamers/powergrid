import copy
import unittest
from teacher_contract import validate_game, validation_game, validation_seeds
from multiplayer import rotate_outcome


class TeacherContractTests(unittest.TestCase):
    def test_player_rotation_and_invalid_targets(self):
        for n in range(2, 7):
            for seat in range(n):
                value = [0.0] * n
                value[n - 1] = 1.0
                game = dict(
                    playerCount=n,
                    featureRevision="4.0-multiplayer",
                    variant="original",
                    sealed=True,
                    seed=f"{n}-{seat}",
                    truncated=False,
                    value=value,
                    rows=[
                        dict(
                            state=[1] * n + [0] * (1149 - n),
                            actions=[[0.0] * 98],
                            target=0,
                            seat=seat,
                            value=rotate_outcome(value, seat),
                            searchValues=[[0, 0.5]],
                        )
                    ],
                )
                validate_game(game)
                broken = copy.deepcopy(game)
                broken["rows"][0]["value"] = [0.0] * 6
                with self.assertRaises(ValueError):
                    validate_game(broken)
                broken = copy.deepcopy(game)
                broken["rows"][0]["target"] = 1
                with self.assertRaises(ValueError):
                    validate_game(broken)
                broken = copy.deepcopy(game)
                broken["truncated"] = True
                with self.assertRaises(ValueError):
                    validate_game(broken)

    def test_split_does_not_exclude_a_five_player_seat_or_rule(self):
        cells = {
            (i // 4 % 5, i % 4)
            for i in range(960)
            if validation_game(f"multiplayer-teacher-v1-5p-{i}")
        }
        self.assertEqual(len(cells), 20)

    def test_stratified_split_covers_every_real_shard_cell(self):
        games = [
            dict(
                seed=f"multiplayer-teacher-v1-{n}p-{i}",
                playerCount=n,
                variant="recharged" if i % 2 else "original",
                sealed=i % 4 < 2,
                rows=[dict(seat=i // 4 % n)],
            )
            for n in range(2, 7)
            for i in range((n - 2) * 240, (n - 1) * 240)
        ]
        selected = validation_seeds(games)
        key = lambda g: (
            g["playerCount"],
            g["rows"][0]["seat"],
            g["variant"],
            g["sealed"],
        )
        expected = {key(g) for g in games}
        self.assertEqual({key(g) for g in games if g["seed"] in selected}, expected)
        self.assertEqual({key(g) for g in games if g["seed"] not in selected}, expected)
        self.assertEqual(selected, validation_seeds(list(reversed(games))))


if __name__ == "__main__":
    unittest.main()
