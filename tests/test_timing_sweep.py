import math
from pathlib import Path
import tempfile
import unittest
from experiments.paired_timing import Observations, score
from experiments.timing_sweep import anchor_correct, run, simulate


class SweepTests(unittest.TestCase):
    def test_invalid_simulation_parameters(self):
        for params in ((0, 0, 0, -1, 0), (0, 0, 0, 0, -1), (math.nan, 0, 0, 0, 0)):
            with self.subTest(params=params), self.assertRaises(ValueError):
                simulate(*params, seed=0)

    def test_noise_free_boundary(self):
        for p in (-.1, 0, .1):
            for c in (-.1, 0, .1):
                result = simulate(p, c, 0, 0, 0, 0)
                self.assertAlmostEqual(result['slope_removal']['pat_mae_ms'], 300 * abs(p))
                self.assertAlmostEqual(result['no_correction']['pat_mae_ms'], 300 * abs(c))
                self.assertAlmostEqual(result['two_anchors']['pat_mae_ms'], 0)

    def test_offset_not_removed_by_slope_only(self):
        result = simulate(0, .1, 20, 0, 0, 0)
        self.assertAlmostEqual(result['slope_removal']['pat_mae_ms'], 20)
        self.assertAlmostEqual(result['two_anchors']['pat_mae_ms'], 0)

    def test_seed_reproducibility_and_variation(self):
        self.assertEqual(simulate(.1, .1, 20, 5, 5, 1), simulate(.1, .1, 20, 5, 5, 1))
        self.assertNotEqual(simulate(.1, .1, 20, 5, 5, 1), simulate(.1, .1, 20, 5, 5, 2))

    def test_exact_anchors_equal_oracle_with_noise(self):
        result = simulate(.1, -.1, 20, 5, 0, 4)
        for metric in result['oracle']:
            self.assertAlmostEqual(result['oracle'][metric], result['two_anchors'][metric])

    def test_anchor_bias_is_not_hidden(self):
        obs = Observations((0, 1, 2), (200, 201, 202))
        corrected = anchor_correct(obs, (0, 2), (10, 12))
        self.assertEqual(corrected, (190, 190, 190))

    def test_exact_endpoints_do_not_identify_nonlinear_clock(self):
        obs = Observations((0, 1, 2), (200, 220, 200))
        result = anchor_correct(obs, (0, 2), (0, 0))
        self.assertEqual(result, obs.delay_ms)
        self.assertGreater(score(result, (200, 200, 200))['pat_mae_ms'], 6)

    def test_invalid_anchors(self):
        obs = Observations((0, 1), (200, 200))
        for times, errors in (((0, 0), (0, 0)), ((0, 1), (0, math.nan)), ((.5, 1), (0, 0)), ((0,), (0,))):
            with self.subTest(times=times, errors=errors), self.assertRaises(ValueError):
                anchor_correct(obs, times, errors)

    def test_sweep_cardinality_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            rows = run(path, repeats=2)
            self.assertEqual(len(rows), 72 * 4)
            content = (path / 'trials.csv').read_bytes()
            self.assertEqual(len(content.splitlines()), 72 * 2 * 4 + 1)
            self.assertEqual(run(path, repeats=2), rows)
            self.assertEqual(content, (path / 'trials.csv').read_bytes())
