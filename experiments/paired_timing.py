"""Assignment 03: implement H1 from the Assignment 02 research note.

This is an additive event-time simulation, not a device-clock simulator or a
clinical model. All delays are milliseconds; reference times are seconds.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
from statistics import fmean
from typing import Sequence


@dataclass(frozen=True)
class Observations:
    time_s: tuple[float, ...]
    delay_ms: tuple[float, ...]


@dataclass(frozen=True)
class GroundTruth:
    pat_ms: tuple[float, ...]
    clock_error_ms: tuple[float, ...]


@dataclass(frozen=True)
class Scenario:
    name: str
    observations: Observations
    truth: GroundTruth


def make_scenarios() -> tuple[Scenario, Scenario]:
    """Construct the exact, noise-free H1 cases; no randomness is used."""
    times = tuple(float(t) for t in range(601))
    constant_pat = (200.0,) * len(times)
    ramp = tuple(0.1 * t for t in times)
    changing_pat = tuple(p + c for p, c in zip(constant_pat, ramp))
    a = Scenario(
        "A_clock_drift",
        Observations(times, changing_pat),
        GroundTruth(constant_pat, ramp),
    )
    b = Scenario(
        "B_physiological_change",
        Observations(times, changing_pat),
        GroundTruth(changing_pat, (0.0,) * len(times)),
    )
    return a, b


def remove_linear_slope(observations: Observations) -> tuple[float, ...]:
    """OLS slope removal, preserving the observed value at the first time.

    Only observations enter this function. No scenario label, true PAT, or
    true clock error is available to the estimator.
    """
    times, delays = observations.time_s, observations.delay_ms
    if len(times) != len(delays) or len(times) < 2:
        raise ValueError("Need at least two paired times and delays.")
    if not all(math.isfinite(x) for x in (*times, *delays)):
        raise ValueError("Times and delays must be finite.")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Reference times must be strictly increasing.")
    mean_t, mean_d = fmean(times), fmean(delays)
    numerator = math.fsum((t - mean_t) * (d - mean_d) for t, d in zip(times, delays))
    denominator = math.fsum((t - mean_t) ** 2 for t in times)
    slope = numerator / denominator
    return tuple(d - slope * (t - times[0]) for t, d in zip(times, delays))


def score(estimated: Sequence[float], truth: Sequence[float]) -> dict[str, float]:
    """Score PAT accuracy and change distortion, all in milliseconds."""
    if len(estimated) != len(truth) or len(truth) < 2:
        raise ValueError("Need at least two paired estimates and truth values.")
    if not all(math.isfinite(x) for x in (*estimated, *truth)):
        raise ValueError("Estimates and truth must be finite.")
    return {
        "pat_mae_ms": fmean(abs(e - p) for e, p in zip(estimated, truth)),
        "endpoint_error_ms": abs(estimated[-1] - truth[-1]),
        "change_distortion_ms": abs(
            (estimated[-1] - estimated[0]) - (truth[-1] - truth[0])
        ),
    }


def evaluate(scenario: Scenario) -> dict[str, tuple[float, ...]]:
    """Run observable-only baselines and a separately labelled oracle control."""
    observed = scenario.observations.delay_ms
    return {
        "no_correction": observed,
        "slope_removal": remove_linear_slope(scenario.observations),
        "oracle": tuple(
            d - c for d, c in zip(observed, scenario.truth.clock_error_ms)
        ),
    }


def run(output_dir: Path, *, make_plot: bool = True) -> dict:
    scenarios = make_scenarios()
    predictions = {s.name: evaluate(s) for s in scenarios}
    metrics = [
        {"scenario": s.name, "method": method, **score(values, s.truth.pat_ms)}
        for s in scenarios
        for method, values in predictions[s.name].items()
    ]
    summary = {
        "experiment": "assignment-03-paired-timing",
        "specification": "docs/research/assignment-02-literature-and-hypothesis.md#6-one-precise-testable-hypothesis-h1",
        "settings": {
            "event_pairs_per_scenario": 601,
            "duration_s": 600,
            "initial_pat_ms": 200,
            "trend_ms_per_s": 0.1,
            "noise_ms": 0,
            "random_seed": None,
            "randomness": "none",
            "model": "additive event-time model; known beat correspondence",
        },
        "provenance": {
            "python_version": platform.python_version(),
            "experiment_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "observations_identical": scenarios[0].observations == scenarios[1].observations,
        "metrics": metrics,
        "limitations": [
            "Synthetic event times, not measured signals or full waveforms.",
            "No noise, missing beats, device delays, or beat-matching errors.",
            "Oracle uses ground truth unavailable to the other methods.",
            "Analytical sanity check, not a novel clinical finding or a test of all synchronization methods.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    with (output_dir / "events.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "scenario", "time_s", "observed_delay_ms", "true_pat_ms", "clock_error_ms",
            "no_correction_ms", "slope_removal_ms", "oracle_ms",
        ])
        for s in scenarios:
            values = predictions[s.name]
            for i, t in enumerate(s.observations.time_s):
                writer.writerow([
                    s.name, t, s.observations.delay_ms[i], s.truth.pat_ms[i],
                    s.truth.clock_error_ms[i], values["no_correction"][i],
                    values["slope_removal"][i], values["oracle"][i],
                ])
    if make_plot:
        from experiments.plot_paired_timing import plot_results

        summary["provenance"].update(plot_results(scenarios, predictions, output_dir))
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/assignment-03"))
    parser.add_argument("--no-plot", action="store_true", help="Run numerical experiment using only the standard library.")
    args = parser.parse_args()
    summary = run(args.output_dir, make_plot=not args.no_plot)
    print("Scenario / method: PAT MAE, endpoint error, change distortion (ms)")
    for row in summary["metrics"]:
        print(f"{row['scenario']} / {row['method']}: "
              f"{row['pat_mae_ms']:.6f}, {row['endpoint_error_ms']:.6f}, "
              f"{row['change_distortion_ms']:.6f}")
    print(f"Artifacts: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
