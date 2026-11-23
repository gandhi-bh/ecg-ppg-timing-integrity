import json
import math
from pathlib import Path
import tempfile
import unittest
from experiments.paired_timing import Observations
from experiments.selective_correction import Condition, clock_error, interpolate_clock, selective_correct, simulate, select_threshold, run


class SelectiveTests(unittest.TestCase):
    def test_affine_interpolation_and_noise_propagation(self):
        estimate, sd = interpolate_clock((0, 5, 10), (0, 10), (20, 40), 4)
        self.assertEqual(estimate, (20, 30, 40))
        self.assertEqual(sd[0], 4)
        self.assertAlmostEqual(sd[1], math.sqrt(8))

    def test_exact_knots_with_irregular_spacing(self):
        estimate, _ = interpolate_clock((0, 2, 7), (0, 2, 7), (3, -1, 8), 0)
        self.assertEqual(estimate, (3, -1, 8))

    def test_gate_retains_uncertain_and_corrects_negative_error(self):
        obs = Observations((0, 1, 2), (200, 200, 200))
        values, fraction = selective_correct(obs, (2, -3, 0), (1, 1, 0), 2)
        self.assertEqual(values, (200, 203, 200))
        self.assertAlmostEqual(fraction, 1/3)

    def test_hidden_oscillation_despite_exact_anchors(self):
        obs, truth, clock, estimate, sd = simulate(Condition('oscillating', 150, 0, 0, 0), 0)
        self.assertAlmostEqual(clock[75], 20)
        self.assertLess(max(abs(v) for v in estimate), 1e-10)
        corrected, fraction = selective_correct(obs, estimate, sd, 3)
        self.assertEqual(fraction, 0)
        self.assertAlmostEqual(corrected[75]-truth[75], 20)

    def test_no_clock_exact_anchors_leaves_signal_unchanged(self):
        obs, _, _, estimate, sd = simulate(Condition('none', 60, 5, 0, .1), 3)
        self.assertEqual(selective_correct(obs, estimate, sd, 3), (obs.delay_ms, 0))

    def test_invalid_inputs(self):
        for times, anchors, values, sd in (((0,1), (0,0), (0,0), 0), ((0,2), (0,1), (0,0), 0), ((0,1), (0,1), (0,math.nan), 0), ((0,1), (0,1), (0,0), -1)):
            with self.assertRaises(ValueError):
                interpolate_clock(times, anchors, values, sd)
        with self.assertRaises(ValueError):
            selective_correct(Observations((0,), (200,)), (0,), (0,), -1)

    def test_selection_uses_development_scores_and_tie_rule(self):
        self.assertEqual(select_threshold({0.: 5, 1.: 2, 2.: 2, 3.: 3}), 1.)

    def test_split_validation_and_reproducible_exports(self):
        conditions = [Condition('none', 60, 5, 5, 0), Condition('quadratic', 300, 0, 0, .1)]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with self.assertRaises(ValueError):
                run(out, conditions=conditions, development_seeds=(0,1), evaluation_seeds=(1,2))
            first, meta = run(out, conditions=conditions, development_seeds=(0,1), evaluation_seeds=(100,101))
            content = (out/'trials.csv').read_bytes()
            second, _ = run(out, conditions=conditions, development_seeds=(0,1), evaluation_seeds=(100,101))
            self.assertEqual(first, second)
            self.assertEqual(content, (out/'trials.csv').read_bytes())
            self.assertEqual(meta['evaluation_rows'], 16)
            self.assertFalse(set(meta['development_seeds']) & set(meta['evaluation_seeds']))

    def test_profile_definitions_and_seed_variation(self):
        self.assertEqual(clock_error('quadratic', 300), 15)
        self.assertEqual(clock_error('step', 274), 0)
        self.assertEqual(clock_error('step', 275), 30)
        c = Condition('linear', 150, 5, 5, 0)
        self.assertEqual(simulate(c, 1), simulate(c, 1))
        self.assertNotEqual(simulate(c, 1), simulate(c, 2))
