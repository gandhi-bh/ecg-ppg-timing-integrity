import math
from pathlib import Path
import tempfile
import unittest
from experiments.anchor_schedule import Condition,default_conditions,evaluate,schedule,run,THRESHOLD


class ScheduleTests(unittest.TestCase):
    def test_budget_endpoints_order_and_bounds(self):
        for spacing in (60,150,300,600):
            for seed in (200,201,219):
                regular=schedule(spacing,seed)
                jittered=schedule(spacing,seed,True)
                self.assertEqual(len(regular),len(jittered))
                self.assertEqual((jittered[0],jittered[-1]),(0,600))
                self.assertTrue(all(a<b for a,b in zip(jittered,jittered[1:])))
                self.assertTrue(all(abs(a-b)<=.3*spacing for a,b in zip(regular,jittered)))

    def test_seed_behavior_and_two_anchor_negative_control(self):
        self.assertEqual(schedule(150,200,True),schedule(150,200,True))
        self.assertNotEqual(schedule(150,200,True),schedule(150,201,True))
        c=Condition('oscillating',300,0,600,5)
        result,_=evaluate(c,200)
        self.assertEqual(result['regular'],result['jittered'])

    def test_jitter_exposes_exact_zero_crossing_anchors(self):
        result,_=evaluate(Condition('oscillating',300,0,150,0),200)
        self.assertTrue(result['regular']['blind_schedule'])
        self.assertFalse(result['jittered']['blind_schedule'])

    def test_affine_exact_anchors_agree_with_oracle(self):
        result,_=evaluate(Condition('linear',0,0,150,0),200)
        for method in ('regular','jittered'):
            self.assertAlmostEqual(result[method]['pat_mae_ms'],result['oracle']['pat_mae_ms'])

    def test_accurate_clock_exact_anchors_no_change(self):
        result,_=evaluate(Condition('none',0,0,60,0),200)
        for method in ('regular','jittered'):
            self.assertEqual(result[method]['corrected_fraction'],0)
            self.assertEqual(result[method]['pat_mae_ms'],result['no_correction']['pat_mae_ms'])

    def test_grid_and_frozen_threshold(self):
        self.assertEqual(len(default_conditions()),112)
        self.assertEqual(THRESHOLD,2)
        with self.assertRaises(ValueError):
            schedule(17,200)
        with self.assertRaises(ValueError):
            evaluate(Condition('oscillating',300,0,60,-1),200)

    def test_export_repeatability(self):
        conditions=[Condition('none',0,0,60,5),Condition('oscillating',200,math.pi/4,150,5)]
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            first=run(out,conditions=conditions,seeds=(200,201))
            data={name:(out/name).read_bytes() for name in ('trials.csv','aggregate.csv','schedules.csv')}
            self.assertEqual(len(first),8)
            self.assertEqual(first,run(out,conditions=conditions,seeds=(200,201)))
            for name,content in data.items():
                self.assertEqual((out/name).read_bytes(),content)
