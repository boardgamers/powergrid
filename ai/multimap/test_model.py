import copy
import json
import subprocess
import tempfile
import gzip
from pathlib import Path
import unittest

import torch

from data import ROOT, specs, Bridge, atomic_json, digest
from model import GraphPolicy, tensor_row, collate


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(508)
        torch.set_num_threads(1)
        cls.model = GraphPolicy().eval()
        request = dict(op="start", spec=dict(map="UK & Ireland", players=3, variant="recharged", fastBid=True, seed="tensor-test"))
        result = subprocess.run(["node", str(ROOT / "ai/multimap/game.cjs")], input=json.dumps(request)+"\n", capture_output=True, text=True, check=True)
        cls.row = tensor_row(json.loads(result.stdout)["observation"])

    def test_padding_and_city_permutation(self):
        a = self.row
        baseline = self.model(collate([a]))
        perm = torch.randperm(len(a["nodes"]))
        inverse = torch.argsort(perm)
        b = copy.deepcopy(a)
        b["nodes"] = a["nodes"][perm]
        b["relations"] = a["relations"][:, perm][:, :, perm]
        b["actionCity"] = torch.where(a["actionCity"] >= 0, inverse[a["actionCity"].clamp_min(0)], a["actionCity"])
        actual = self.model(collate([b]))
        for x, y in zip(baseline, actual):
            torch.testing.assert_close(x, y, atol=1e-6, rtol=1e-5)
        # A larger companion observation forces padding of players, nodes and actions.
        other = copy.deepcopy(a)
        other["players"] = torch.cat([a["players"], a["players"]])
        other["nodes"] = torch.cat([a["nodes"], a["nodes"]])
        n = len(other["nodes"])
        other["relations"] = torch.zeros(4, n, n)
        other["actions"] = torch.cat([a["actions"], a["actions"]])
        other["actionCity"] = torch.cat([a["actionCity"], a["actionCity"]])
        other["targets"] = torch.cat([a["targets"], a["targets"]])
        padded = self.model(collate([a, other]))
        torch.testing.assert_close(baseline[0][0], padded[0][0, :len(a["actions"])], atol=1e-6, rtol=1e-5)
        torch.testing.assert_close(baseline[1][0], padded[1][0], atol=1e-6, rtol=1e-5)
        self.assertTrue((padded[0][0, len(a["actions"]):] == -1e9).all())

    def test_action_permutation(self):
        a = self.row
        b = copy.deepcopy(a)
        perm = torch.randperm(len(a["actions"]))
        for key in ("actions", "actionCity", "targets"):
            b[key] = a[key][perm]
        x, y = self.model(collate([a])), self.model(collate([b]))
        torch.testing.assert_close(x[0][:, perm], y[0])
        torch.testing.assert_close(x[1], y[1])

    def test_exact_checkpoint_resume(self):
        from train import train
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = Bridge()
            try:
                for split in ('train', 'validation', 'transfer'):
                    spec = dict(specs(split, 1)[0], seed='resume-unit:' + split, samplesPerPhase=1)
                    game = bridge.call({'op':'collect','spec':spec})
                    directory = root/'data'/split
                    directory.mkdir(parents=True)
                    path = directory/'game.json.gz'
                    with gzip.open(path,'wt') as file:
                        json.dump(game,file)
                    atomic_json(directory/'manifest.json', {'games':[{'file':path.name,'sha256':digest(path),'spec':spec}]})
            finally:
                bridge.close()
            train(root/'data',root/'full',epochs=2,device='cpu')
            def interrupt(epoch):
                raise RuntimeError('simulated interruption')
            with self.assertRaisesRegex(RuntimeError,'simulated interruption'):
                train(root/'data',root/'resumed',epochs=2,device='cpu',checkpoint_callback=interrupt)
            train(root/'data',root/'resumed',epochs=2,device='cpu')
            a=torch.load(root/'full/last.pt',weights_only=True)
            b=torch.load(root/'resumed/last.pt',weights_only=True)
            for key in a['state_dict']:
                torch.testing.assert_close(a['state_dict'][key],b['state_dict'][key],rtol=0,atol=0)

    def test_deal_splits_and_heldout_maps(self):
        train, val, transfer = (specs(split, 1) for split in ("train", "validation", "transfer"))
        self.assertFalse({x["seed"] for x in train} & {x["seed"] for x in val})
        self.assertFalse({x["map"] for x in train} & {x["map"] for x in transfer})
        with self.assertRaises(ValueError):
            specs("final")


if __name__ == "__main__":
    unittest.main()
