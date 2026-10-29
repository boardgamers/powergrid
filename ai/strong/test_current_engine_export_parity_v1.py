"""Reject numerically close but semantically different export outputs."""
import unittest
import numpy as np
from current_engine_export_parity_v1 import compare_outputs


class ExportParityTests(unittest.TestCase):
    def values(self):return [np.array([[1.,2.]]),np.array([[.4,.6,0,0,0,0]])]

    def test_equal_legal_choice_and_finite_normalized_values(self):
        i,errors=compare_outputs(self.values(),self.values(),2,2)
        self.assertEqual(i,1);self.assertEqual(errors,[0.,0.])

    def test_near_tie_with_different_argmax_rejected(self):
        a=self.values();b=self.values();a[0]=np.array([[1.,1.+1e-12]]);b[0]=np.array([[1.+1e-12,1.]])
        with self.assertRaises(AssertionError):compare_outputs(a,b,2,2)

    def test_nonfinite_inactive_or_unnormalized_values_rejected(self):
        for value in ([.4,.6,1e-20,0,0,0],[.4,.5,0,0,0,0],[float('nan'),.6,0,0,0,0],[-.1,1.1,0,0,0,0]):
            a=self.values();a[1]=np.array([value])
            with self.subTest(value=value),self.assertRaises(AssertionError):compare_outputs(self.values(),a,2,2)

    def test_wrong_action_or_player_shapes_rejected(self):
        for players,actions in ((1,2),(7,2),(2,3),(2,0)):
            with self.subTest(players=players,actions=actions),self.assertRaises(AssertionError):compare_outputs(self.values(),self.values(),players,actions)
        a=self.values();a[1]=a[1][:,:2]
        with self.assertRaises(AssertionError):compare_outputs(self.values(),a,2,2)


if __name__=='__main__':unittest.main()
