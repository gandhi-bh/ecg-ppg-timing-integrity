"""Plot simulator truth and correction results; never used by estimators."""

from pathlib import Path
import hashlib


def plot_results(scenarios, predictions, output_dir: Path) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True, layout="constrained")
    titles = ("A: clock drift; constant physiology", "B: accurate clock; changing physiology")
    for column, (scenario, title) in enumerate(zip(scenarios, titles)):
        t = scenario.observations.time_s
        true_pat = scenario.truth.pat_ms
        values = predictions[scenario.name]
        ax = axes[0, column]
        ax.plot(t, true_pat, color="black", linewidth=3.5, label="True PAT")
        ax.plot(t, values["no_correction"], color="#d97706", linestyle=":", linewidth=2.5,
                label="Observed / no correction")
        ax.plot(t, values["slope_removal"], color="#2563eb", linestyle="--", linewidth=2,
                label="Slope removal")
        ax.plot(t[::60], values["oracle"][::60], color="#138a64", linestyle="none",
                marker="o", markerfacecolor="none", markersize=6, label="Oracle (true clock known)")
        ax.set_title(title)
        ax.set_ylabel("ECG-to-PPG delay (ms)")
        ax.set_ylim(190, 275)
        ax.legend(fontsize=8, loc="upper left")
        error_ax = axes[1, column]
        for name, label, color, style in (
            ("no_correction", "No correction", "#d97706", ":"),
            ("slope_removal", "Slope removal", "#2563eb", "--"),
            ("oracle", "Oracle", "#138a64", "-"),
        ):
            error_ax.plot(t, [p - q for p, q in zip(values[name], true_pat)],
                          label=label, color=color, linestyle=style, linewidth=2)
        error_ax.set_ylim(-65, 65)
        error_ax.set_ylabel("Estimated PAT − true PAT (ms)")
        error_ax.set_xlabel("ECG reference time (s)")
        error_ax.legend(fontsize=8, loc="upper left")
    for ax in axes.flat:
        ax.grid(alpha=0.2)
    fig.suptitle("Identical observed delays; different causes\nSynthetic, noise-free event-time experiment", fontsize=14)
    fig.savefig(output_dir / "paired_timing.png", dpi=180)
    fig.savefig(output_dir / "paired_timing.svg")
    plt.close(fig)
    return {
        "matplotlib_version": matplotlib.__version__,
        "numpy_version": numpy.__version__,
        "plot_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
