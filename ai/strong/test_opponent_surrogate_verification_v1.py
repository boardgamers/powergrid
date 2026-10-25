"""Exercise real HF rows, false credits, private leakage and runtime isolation."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from strategic_collection import ROOT,read,write,digest
from opponent_surrogate_verification_v1 import verify_row,verify_game,verify_artifacts

FOLDER=ROOT/'ai/runs/opponent-surrogate-runtime-collected-v1/opponent-surrogate-runtime-v1-2p-0-1/artifacts'
PROTOCOL=read(ROOT/'ai/strong/opponent-surrogate-collection-protocol-v1.json')
SOURCE=read(ROOT/'ai/strong/opponent-surrogate-source-v1.json')
EVIDENCE={'manifest_sha256':digest(FOLDER/'manifest.json'),'archived_files':60}


class SurrogateVerificationTest(unittest.TestCase):
    def test_complete_real_hf_artifact(self):
        r=verify_artifacts(FOLDER,PROTOCOL,SOURCE,2,0,1,'runtime',EVIDENCE)
        self.assertEqual((r['games'],r['twin_games'],r['teacher_rows'],r['public_replays']),(8,8,382,48))
        self.assertEqual(r['split_games'],{'runtime':8})
        self.assertEqual(r['training_rows'],0)
        self.assertFalse(r['training_eligible'])

    def test_runtime_data_cannot_be_read_as_training(self):
        with self.assertRaises(AssertionError):
            verify_artifacts(FOLDER,PROTOCOL,SOURCE,2,0,1,'collection',EVIDENCE)

    def test_private_or_invalid_teacher_rows_rejected(self):
        folder=FOLDER/'games/game-0';q=read(folder/'contract.json')
        with (folder/'opponent-decisions.jsonl').open() as f:row=json.loads(f.readline())
        verify_row(row,0,q)
        edits=[lambda r:r.update(target=len(r['observation']['moves'])),
               lambda r:r['request']['state'].update(powerPlantsDeck=[1]),
               lambda r:r['request']['state'].update(hiddenLog=[{'secret':1}]),
               lambda r:r['request']['state']['players'][0].update(bid=1),
               lambda r:r['request']['state']['options'].update(showMoney=False),
               lambda r:r['observation']['state'].__setitem__(0,float('nan')),
               lambda r:r['teacher']['options'].update(samples=8),
               lambda r:r['teacher']['result'].update(truncated=1),
               lambda r:r['teacher']['result'].update(winEstimate=2),
               lambda r:r.update(qualification_eligible=True)]
        for edit in edits:
            bad=copy.deepcopy(row);edit(bad)
            with self.assertRaises(AssertionError):verify_row(bad,0,q)

    def test_resealed_false_terminal_credit_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'game-0';shutil.copytree(FOLDER/'games/game-0',folder)
            q=read(folder/'contract.json');result=read(folder/'verified.json')
            terminal=read(folder/'terminal.json')
            terminal['value']=[.5,.5] if terminal['value']!=[.5,.5] else [1,0]
            write(folder/'terminal.json',terminal)
            result['files']['terminal.json']=digest(folder/'terminal.json');write(folder/'verified.json',result)
            with self.assertRaises(AssertionError):verify_game(folder,q,result)


if __name__=='__main__':unittest.main()
