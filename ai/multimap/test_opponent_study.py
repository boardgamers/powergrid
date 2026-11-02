import json
from pathlib import Path
import tempfile
import unittest
import torch
from data import digest
from residual import ResidualPolicy, save
from ppo import config
from opponent_study import plan, key, initialize, one_game, summarize, read_existing


class OpponentStudyTests(unittest.TestCase):
    def test_frozen_plan_balanced_and_disjoint(self):
        tasks=plan();smoke=plan(True)
        self.assertEqual(len(tasks),11520)
        self.assertEqual(len({key(t) for t in tasks}),11520)
        self.assertEqual(len({t['spec']['seed'] for t in tasks}),1440)
        self.assertFalse({t['spec']['seed'] for t in tasks}&{t['spec']['seed'] for t in smoke})
        for style in ('economic','geographic','rush'):
            subset=[t for t in tasks if t['spec']['opponentStyle']==style]
            self.assertEqual(len(subset),3840)
        for t in tasks:self.assertNotIn('final',t['spec']['seed'])

    def test_game_legality_zero_actor_and_explicit_failure(self):
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.pt'
            save(path,ResidualPolicy(16),update=8,config=config(True))
            initialize(path)
            selected,teacher=plan(True)[:2]
            a=one_game(selected);b=one_game(teacher)
            for k in ('terminal','credit','steps','rounds'):self.assertEqual(a[k],b[k])
            self.assertTrue(a['terminal'])
            failed=one_game(dict(selected,spec=dict(selected['spec'],maxSteps=1)))
            self.assertFalse(failed['terminal']);self.assertEqual(failed['credit'],0)
            self.assertIn('capped',failed['error'])
            summary=summarize([failed,b])
            self.assertEqual(summary['failures'],1)

    def test_resume_checks_and_partial_write_recovery(self):
        tasks=plan(True)[:2]
        records=[dict(t,terminal=True,credit=.5,steps=100,rounds=10) for t in tasks]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'games.jsonl'
            line=json.dumps(records[0])+'\n'
            path.write_text(line+'{"spec":')
            saved,done=read_existing(path,tasks)
            self.assertEqual(saved,records[:1]);self.assertEqual(done,{key(tasks[0])})
            self.assertEqual(path.read_text(),line)
            path.write_text(line+line)
            with self.assertRaisesRegex(ValueError,'duplicate'):read_existing(path,tasks)
        s=summarize(records)
        self.assertEqual(s['groups']['all']['difference'],0)


if __name__=='__main__':unittest.main()
