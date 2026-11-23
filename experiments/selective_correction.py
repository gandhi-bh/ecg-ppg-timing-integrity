"""Assignment 05: nonlinear clocks and uncertainty-gated correction.

This is our synthetic protocol, not an implementation of a published method.
All delay values are milliseconds, times seconds. No clinical thresholds.
"""
import argparse
from bisect import bisect_right
import csv
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
from statistics import fmean, stdev

from experiments.paired_timing import Observations, score

PROFILES = ("none", "linear", "quadratic", "oscillating", "step")
THRESHOLDS = (0., 1., 2., 3.)


@dataclass(frozen=True)
class Condition:
    profile: str
    spacing_s: int
    observation_sd_ms: float
    anchor_sd_ms: float
    pat_slope_ms_s: float


def clock_error(profile, time):
    if profile == "none":
        return 0.
    if profile == "linear":
        return .1 * time
    if profile == "quadratic":
        return 60 * (time / 600) ** 2
    if profile == "oscillating":
        return 20 * math.sin(2 * math.pi * time / 300)
    if profile == "step":
        return 0. if time < 275 else 30.
    raise ValueError("Unknown clock profile.")


def interpolate_clock(times, anchor_times, anchor_values, anchor_sd):
    """Piecewise linear clock estimate and propagated anchor-noise SD.

    The SD models independent measurement noise ONLY, not interpolation bias.
    """
    if len(anchor_times) < 2 or len(anchor_times) != len(anchor_values) or not times:
        raise ValueError("At least two paired anchors and observation times required.")
    if not all(math.isfinite(v) for v in (*times, *anchor_times, *anchor_values, anchor_sd)) or anchor_sd < 0:
        raise ValueError("Finite inputs and nonnegative anchor SD required.")
    if any(b <= a for a, b in zip(anchor_times, anchor_times[1:])) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Times must be strictly increasing.")
    if times[0] < anchor_times[0] or times[-1] > anchor_times[-1]:
        raise ValueError("No extrapolation beyond anchors.")
    estimates, uncertainty = [], []
    for t in times:
        i = min(bisect_right(anchor_times, t) - 1, len(anchor_times) - 2)
        w = (t - anchor_times[i]) / (anchor_times[i+1] - anchor_times[i])
        estimates.append((1-w) * anchor_values[i] + w * anchor_values[i+1])
        uncertainty.append(anchor_sd * math.sqrt((1-w)**2 + w**2))
    return tuple(estimates), tuple(uncertainty)


def selective_correct(observations, estimate, uncertainty, threshold):
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Threshold must be finite and nonnegative.")
    if not len(estimate) == len(uncertainty) == len(observations.delay_ms) or not estimate:
        raise ValueError("Paired nonempty vectors required.")
    if not all(math.isfinite(x) for x in (*estimate, *uncertainty, *observations.delay_ms)) or any(x < 0 for x in uncertainty):
        raise ValueError("Finite values and nonnegative uncertainty required.")
    applied = tuple(abs(c) > max(threshold*s, 1e-12) for c, s in zip(estimate, uncertainty))
    values = tuple(d-c if use else d for d, c, use in zip(observations.delay_ms, estimate, applied))
    return values, fmean(applied)


def simulate(condition, seed):
    c = condition
    if c.profile not in PROFILES or c.spacing_s not in (60, 150, 300, 600):
        raise ValueError("Unsupported profile or anchor spacing.")
    if not all(math.isfinite(v) for v in (c.observation_sd_ms, c.anchor_sd_ms, c.pat_slope_ms_s)) or min(c.observation_sd_ms, c.anchor_sd_ms) < 0:
        raise ValueError("Finite parameters and nonnegative noise SD required.")
    times = tuple(range(601))
    truth = tuple(200 + c.pat_slope_ms_s*t for t in times)
    clock = tuple(clock_error(c.profile, t) for t in times)
    rng = random.Random(seed)
    observed = Observations(times, tuple(p+e+rng.gauss(0, c.observation_sd_ms) for p, e in zip(truth, clock)))
    anchor_times = tuple(range(0, 601, c.spacing_s))
    # A shared anchor time has the same noise across spacing conditions.
    anchor_values = tuple(clock_error(c.profile, t) + random.Random(1000000 + seed*1000+t).gauss(0, c.anchor_sd_ms) for t in anchor_times)
    estimate, sd = interpolate_clock(times, anchor_times, anchor_values, c.anchor_sd_ms)
    return observed, truth, clock, estimate, sd


def select_threshold(development_scores):
    """Only development metrics enter threshold selection; prefer smaller k on ties."""
    return min(development_scores, key=lambda k: (development_scores[k], k))


def run(output, *, conditions=None, development_seeds=tuple(range(10)), evaluation_seeds=tuple(range(100, 120))):
    if len(development_seeds) < 2 or len(evaluation_seeds) < 2 or set(development_seeds) & set(evaluation_seeds):
        raise ValueError("Use disjoint development/evaluation seeds, at least two per split.")
    if len(set(development_seeds)) != len(development_seeds) or len(set(evaluation_seeds)) != len(evaluation_seeds):
        raise ValueError("Duplicate seeds are not independent repeats.")
    if conditions is None:
        conditions = [Condition(*x) for x in itertools.product(PROFILES, (60,150,300,600), (0,5), (0,5), (0,.1))]
    if not conditions:
        raise ValueError("Conditions cannot be empty.")
    dev = {k: [] for k in THRESHOLDS}
    for condition in conditions:
        for seed in development_seeds:
            obs, truth, _, estimate, sd = simulate(condition, seed)
            for k in THRESHOLDS:
                values, _ = selective_correct(obs, estimate, sd, k)
                dev[k].append(score(values, truth)["pat_mae_ms"])
    dev_means = {k: fmean(values) for k, values in dev.items()}
    chosen = select_threshold(dev_means)
    trials, aggregate = [], []
    for condition in conditions:
        cell = []
        for seed in evaluation_seeds:
            obs, truth, clock, estimate, sd = simulate(condition, seed)
            selective, coverage = selective_correct(obs, estimate, sd, chosen)
            outputs = {
                "no_correction": (obs.delay_ms, 0.),
                "always_correct": (tuple(d-e for d,e in zip(obs.delay_ms, estimate)), 1.),
                "selective": (selective, coverage),
                "oracle": (tuple(d-e for d,e in zip(obs.delay_ms, clock)), 1.),
            }
            baseline = score(obs.delay_ms, truth)["pat_mae_ms"]
            for method, (values, fraction) in outputs.items():
                metrics = score(values, truth)
                row = {**asdict(condition), "seed": seed, "method": method, **metrics,
                       "corrected_fraction": fraction,
                       "mae_delta_ms": metrics["pat_mae_ms"]-baseline,
                       "harm_over_1ms": metrics["pat_mae_ms"]-baseline > 1.}
                cell.append(row)
                trials.append(row)
        for method in outputs:
            subset = [r for r in cell if r["method"] == method]
            row = {**asdict(condition), "method": method, "repeats": len(evaluation_seeds)}
            for metric in ("pat_mae_ms", "endpoint_error_ms", "change_distortion_ms", "corrected_fraction", "mae_delta_ms", "harm_over_1ms"):
                row[metric+"_mean"] = fmean(r[metric] for r in subset)
                row[metric+"_sd"] = stdev(r[metric] for r in subset)
            aggregate.append(row)
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("trials.csv", trials), ("aggregate.csv", aggregate)):
        with (output/name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    metadata = {
        "conditions": [asdict(c) for c in conditions], "condition_count": len(conditions),
        "development_seeds": list(development_seeds), "evaluation_seeds": list(evaluation_seeds),
        "threshold_candidates": THRESHOLDS, "development_pat_mae_ms": dev_means,
        "selected_threshold": chosen, "selection": "Minimum mean development PAT MAE, uniform weighting of specified conditions; smaller k breaks ties.",
        "evaluation_rows": len(trials), "duration_s": 600, "events": 601,
        "clock_profiles": {"none": "0", "linear": "0.1*t", "quadratic": "60*(t/600)^2", "oscillating": "20*sin(2*pi*t/300)", "step": "0 before 275s; 30ms thereafter"},
        "noise": "Independent Gaussian noise; known anchor SD; same seeded noise reused across conditions. SD excludes model bias.",
        "limits": "Held-out seeds on the same condition grid; not held-out profiles, real data, clinical confidence intervals, or validated safety guarantees. 1ms harm margin is an arbitrary reporting threshold.",
        "python": platform.python_version(),
        "source_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ("experiments/selective_correction.py", "experiments/paired_timing.py")},
    }
    (output/"metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return aggregate, metadata


def plot(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    methods = ("no_correction", "always_correct", "selective")
    colors = ("#777777", "#d97706", "#2563eb")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for j, (method, color) in enumerate(zip(methods, colors)):
        values = [fmean(r["pat_mae_ms_mean"] for r in rows if r["profile"] == p and r["method"] == method) for p in PROFILES]
        axes[0].bar([i+(j-1)*.25 for i in range(5)], values, width=.25, label=method.replace("_", " "), color=color)
    axes[0].set_xticks(range(5), PROFILES, rotation=20)
    axes[0].set_ylabel("PAT MAE (ms)")
    axes[0].set_title("Held-out seeds: equal-weight condition means")
    axes[0].legend(fontsize=8)
    for method, color in zip(methods, colors):
        values = [next(r["pat_mae_ms_mean"] for r in rows if r["profile"] == "oscillating" and r["spacing_s"] == s and r["observation_sd_ms"] == 0 and r["anchor_sd_ms"] == 0 and r["pat_slope_ms_s"] == 0 and r["method"] == method) for s in (60,150,300,600)]
        axes[1].plot((60,150,300,600), values, marker="o", color=color, label=method.replace("_", " "))
    axes[1].set_xlabel("Anchor spacing (s)")
    axes[1].set_ylabel("PAT MAE (ms)")
    axes[1].set_title("Oscillating clock: exact anchors, no noise")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=.2)
    fig.suptitle("Synthetic nonlinear clocks: extra measurements do not guarantee recovery")
    fig.savefig(output/"nonlinear.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/assignment-05"))
    args = parser.parse_args()
    rows, metadata = run(args.output_dir)
    plot(rows, args.output_dir)
    print(json.dumps({"conditions": metadata["condition_count"], "selected_threshold": metadata["selected_threshold"], "evaluation_rows": metadata["evaluation_rows"]}))
