"""Analytical checks independent of plotting and external datasets."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.paired_timing import Observations, evaluate, make_scenarios, remove_linear_slope, score


class PairedTimingTests(unittest.TestCase):
    def test_same_observations_distinct_truth(self):
        a, b = make_scenarios()
        self.assertEqual(a.observations, b.observations)
        self.assertNotEqual(a.truth, b.truth)
        for scenario in (a, b):
            self.assertEqual(len(scenario.observations.time_s), 601)
            for observed, pat, clock in zip(scenario.observations.delay_ms,
                                            scenario.truth.pat_ms, scenario.truth.clock_error_ms):
                self.assertAlmostEqual(observed, pat + clock, delta=1e-6)

    def test_h1_and_controls_against_analytical_errors(self):
        expected = {
            "A_clock_drift": {"no_correction": (30, 60, 60), "slope_removal": (0, 0, 0), "oracle": (0, 0, 0)},
            "B_physiological_change": {"no_correction": (0, 0, 0), "slope_removal": (30, 60, 60), "oracle": (0, 0, 0)},
        }
        for scenario in make_scenarios():
            for method, prediction in evaluate(scenario).items():
                with self.subTest(scenario=scenario.name, method=method):
                    metrics = score(prediction, scenario.truth.pat_ms)
                    for key, target in zip(("pat_mae_ms", "endpoint_error_ms", "change_distortion_ms"),
                                           expected[scenario.name][method]):
                        self.assertAlmostEqual(metrics[key], target, delta=1e-6)

    def test_negative_slope_irregular_times_and_nonzero_origin(self):
        observation = Observations((10, 12, 17, 30), (220, 218, 213, 200))
        for value in remove_linear_slope(observation):
            self.assertAlmostEqual(value, 220, delta=1e-6)

    def test_constant_delay_is_preserved(self):
        observation = Observations((0, 1, 4, 9), (180, 180, 180, 180))
        self.assertEqual(remove_linear_slope(observation), observation.delay_ms)

    def test_metrics_distinguish_level_error_from_change_distortion(self):
        self.assertEqual(score((110, 120, 130), (100, 110, 120)), {
            "pat_mae_ms": 10, "endpoint_error_ms": 10, "change_distortion_ms": 0,
        })

    def test_invalid_observations_fail_explicitly(self):
        for observation in (
            Observations((0,), (200,)), Observations((0, 1), (200,)),
            Observations((0, 0), (200, 201)), Observations((1, 0), (200, 201)),
            Observations((0, 1), (200, float("nan"))),
            Observations((0, float("inf")), (200, 201)),
        ):
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                remove_linear_slope(observation)

    def test_cli_exports_reproducible_numerical_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            command = [sys.executable, "-m", "experiments.paired_timing", "--no-plot", "--output-dir", directory]
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
            first = {name: (output / name).read_bytes() for name in ("events.csv", "metrics.csv", "summary.json")}
            summary = json.loads(first["summary.json"])
            self.assertTrue(summary["observations_identical"])
            self.assertEqual(len(summary["metrics"]), 6)
            with (output / "events.csv").open(newline="", encoding="utf-8") as stream:
                events = list(csv.DictReader(stream))
            self.assertEqual(len(events), 1202)
            self.assertEqual(float(events[-1]["true_pat_ms"]), 260)
            self.assertAlmostEqual(float(events[-1]["slope_removal_ms"]), 200, delta=1e-6)
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
            for name, content in first.items():
                self.assertEqual((output / name).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
