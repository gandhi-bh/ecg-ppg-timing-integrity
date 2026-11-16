"""Synthetic sensitivity study; all parameter ranges are experimental choices."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
from statistics import fmean, stdev

from experiments.paired_timing import Observations, remove_linear_slope, score


def anchor_correct(observations, anchor_times, anchor_errors):
    """Correct an affine clock using two independent observed clock errors.

    Anchors are noisy measurements supplied by the simulator, not PAT labels.
    Interpolation is supported only within the anchor interval.
    """
    if len(anchor_times) != 2 or len(anchor_errors) != 2:
        raise ValueError("Exactly two anchors required.")
    a, b = anchor_times
    if not all(math.isfinite(v) for v in (*anchor_times, *anchor_errors)) or b <= a:
        raise ValueError("Anchors must be finite and ordered.")
    t, d = observations.time_s, observations.delay_ms
    if not t or len(t) != len(d) or not all(math.isfinite(v) for v in (*t, *d)):
        raise ValueError("Finite paired observations required.")
    if any(y <= x for x, y in zip(t, t[1:])) or t[0] < a or t[-1] > b:
        raise ValueError("Ordered observations must fall within anchors.")
    return tuple(v - (anchor_errors[0] + (anchor_errors[1] - anchor_errors[0])
                     * (x - a) / (b - a)) for x, v in zip(t, d))


def simulate(pat_slope, clock_slope, offset, noise_sd, anchor_sd, seed):
    if not all(math.isfinite(v) for v in (pat_slope, clock_slope, offset, noise_sd, anchor_sd)):
        raise ValueError("Simulation parameters must be finite.")
    if noise_sd < 0 or anchor_sd < 0:
        raise ValueError("Noise standard deviations must be nonnegative.")
    t = tuple(float(i) for i in range(601))
    signal_rng = random.Random(seed)
    anchor_rng = random.Random(seed + 100000)
    pat = tuple(200 + pat_slope * x for x in t)
    clock = tuple(offset + clock_slope * x for x in t)
    observed = Observations(t, tuple(p + c + signal_rng.gauss(0, noise_sd)
                                    for p, c in zip(pat, clock)))
    anchors = tuple(c + anchor_rng.gauss(0, anchor_sd) for c in (clock[0], clock[-1]))
    predictions = {
        "no_correction": observed.delay_ms,
        "slope_removal": remove_linear_slope(observed),
        "two_anchors": anchor_correct(observed, (0, 600), anchors),
        "oracle": tuple(d - c for d, c in zip(observed.delay_ms, clock)),
    }
    return {method: score(values, pat) for method, values in predictions.items()}


def run(output, repeats=20):
    if repeats < 2:
        raise ValueError("At least two repeats required for sample standard deviation.")
    fields = ("pat_slope_ms_s", "clock_slope_ms_s", "offset_ms", "noise_sd_ms", "anchor_sd_ms")
    grid = list(itertools.product((-.1, 0, .1), (-.1, 0, .1), (0, 20), (0, 5), (0, 5)))
    rows, aggregates = [], []
    for settings in grid:
        conditions = dict(zip(fields, settings))
        trials = [simulate(*settings, seed) for seed in range(repeats)]
        for seed, trial in enumerate(trials):
            for method, metrics in trial.items():
                rows.append({**conditions, "seed": seed, "method": method, **metrics})
        for method in trials[0]:
            record = {**conditions, "method": method, "repeats": repeats}
            for metric in trials[0][method]:
                values = [trial[method][metric] for trial in trials]
                record[metric + "_mean"] = fmean(values)
                record[metric + "_sd"] = stdev(values)
            differences = [trial[method]["pat_mae_ms"] - trial["no_correction"]["pat_mae_ms"] for trial in trials]
            record["paired_mae_delta_mean_ms"] = fmean(differences)
            record["paired_mae_delta_sd_ms"] = stdev(differences)
            aggregates.append(record)
    output.mkdir(parents=True, exist_ok=True)
    for name, records in (("trials.csv", rows), ("aggregate.csv", aggregates)):
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    metadata = {
        "conditions": len(grid), "repeats": repeats, "simulation_runs": len(grid) * repeats,
        "method_evaluations": len(rows), "seeds": list(range(repeats)),
        "common_random_numbers": "Same signal noise across conditions for each seed; separate anchor stream seed+100000.",
        "duration_s": 600, "events": 601, "initial_pat_ms": 200,
        "parameter_grid": {field: sorted(set(row[field] for row in aggregates)) for field in fields},
        "noise": "Independent zero-mean Gaussian event timing noise and independent endpoint anchor errors.",
        "interpretation": "SD is across synthetic seeds, not a clinical confidence interval. Noise-free repeats are identical, not independent evidence.",
        "python": platform.python_version(),
        "source_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                          ("experiments/timing_sweep.py", "experiments/paired_timing.py")},
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return aggregates


def plot(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for ax, method in zip(axes, ("slope_removal", "two_anchors")):
        data = [[next(r["paired_mae_delta_mean_ms"] for r in rows if
                      r["method"] == method and r["pat_slope_ms_s"] == p and
                      r["clock_slope_ms_s"] == c and r["offset_ms"] == 0 and
                      r["noise_sd_ms"] == 0 and r["anchor_sd_ms"] == 0)
                 for c in (-.1, 0, .1)] for p in (-.1, 0, .1)]
        im = ax.imshow(data, cmap="RdBu_r", vmin=-30, vmax=30, origin="lower")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{data[i][j]:.0f}", ha="center", va="center",
                        color="white" if abs(data[i][j]) > 20 else "black")
        ax.set_xticks(range(3), [-.1, 0, .1])
        ax.set_yticks(range(3), [-.1, 0, .1])
        ax.set_xlabel("Clock slope (ms/s)")
        ax.set_ylabel("Physiological slope (ms/s)")
        ax.set_title(method.replace("_", " ").title())
    fig.colorbar(im, ax=axes, label="PAT MAE change vs no correction (ms)")
    fig.suptitle("Noise-free, zero offset: negative = improvement\nTwo-anchor method receives extra, exact clock information")
    fig.savefig(output / "sensitivity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/assignment-04"))
    args = parser.parse_args()
    results = run(args.output_dir)
    plot(results, args.output_dir)
    print(f"Saved 72 conditions x 20 seeds x 4 methods to {args.output_dir}")
