"""Checksum-verified, offline-reproducible audit of one public ECG/PPG CSV."""
import argparse
import csv
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import urllib.request

BASE = "https://physionet.org/files/pulse-transit-time-ppg/1.1.0/"
SOURCE = "https://physionet.org/content/pulse-transit-time-ppg/1.1.0/"
FILES = {
    "csv/s1_sit.csv": "25601a60611e01fe138a88829b202c95f047764f5ee232b4d3457df460133391",
    "s1_sit.hea": "8f4570b9f58c43d9f0bf1dac3eba71d91acd0d85c6bff33067b7db897ae7209f",
    "SHA256SUMS.txt": "02b3393e8aecc711a6ec56c19c1c3c9bb6ac0048691780f2c815318dd5c3a3de",
    "LICENSE.txt": "bcdfcd4f31c790e30fb645dc36414907172405897adff329ad379eed85d12017",
}
ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ensure_file(path, expected, url, download=False):
    path = Path(path)
    if not path.exists():
        if not download:
            raise FileNotFoundError(f"{path}: run with --download first")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".part")
        try:
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            if sha256(temporary) != expected:
                raise ValueError(f"Checksum mismatch: {path.name}")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    if sha256(path) != expected:
        raise ValueError(f"Checksum mismatch: {path.name}; existing file preserved")


def audit(csv_path, header_path):
    fields = Path(header_path).read_text().splitlines()[0].split()
    frequency, expected_rows = float(fields[2]), int(fields[3])
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError("Invalid sampling frequency")
    steps, anomalies, peaks = Counter(), [], []
    ecg, ppg, elapsed = [], [], []
    previous = first = None
    with Path(csv_path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"time", "ecg", "pleth_3", "peaks"}.issubset(reader.fieldnames or []):
            raise ValueError("Required columns missing")
        columns = reader.fieldnames
        for index, row in enumerate(reader):
            try:
                now = datetime.fromisoformat(row["time"])
                values = {key: float(row[key]) for key in columns if key != "time"}
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid row {index}") from exc
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError(f"Nonfinite value at row {index}")
            if values["peaks"] not in (0, 1):
                raise ValueError(f"Nonbinary peak annotation at row {index}")
            if first is None:
                first = now
            if previous is not None:
                delta = now - previous
                us = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
                steps[us] += 1
                if us <= 0 or abs(us - 1000000 / frequency) > 1:
                    anomalies.append({"row_index_zero_based": index, "delta_us": us,
                                      "consistent_with_32bit_us_wrap": us < 0 and abs(us + 2**32 - 1000000 / frequency) <= 1})
            elapsed.append((now - first).total_seconds())
            ecg.append(values["ecg"])
            ppg.append(values["pleth_3"])
            if values["peaks"] == 1:
                peaks.append(index)
            previous = now
    n = len(ecg)
    if n != expected_rows or n < 2:
        raise ValueError(f"Header/CSV sample count mismatch or insufficient rows: {expected_rows}, {n}")
    summary = {
        "record": "s1_sit", "sample_count": n, "header_channels": int(fields[1]),
        "csv_columns": columns, "nominal_frequency_hz": frequency,
        "nominal_last_sample_s": (n - 1) / frequency,
        "raw_timestamp_last_minus_first_s": elapsed[-1],
        "timestamp_step_counts_us": {str(k): v for k, v in sorted(steps.items())},
        "timestamp_anomalies": anomalies, "raw_timestamps_strictly_increasing": all(k > 0 for k in steps),
        "annotated_peak_count": len(peaks), "all_numeric_columns_finite": True,
        "raw_timestamp_timeline_accepted": not anomalies,
        "nominal_timeline_assumption": "sample index / header frequency; does not prove no dropped samples or clock drift",
        "selected_ppg": "pleth_3", "signal_units": "native CSV values; no calibration applied",
    }
    return summary, (ecg, ppg, elapsed, peaks)


def plot(summary, signals, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ecg, ppg, elapsed, peaks = signals
    t = np.arange(len(ecg)) / summary["nominal_frequency_hz"]
    selected = (t >= 10) & (t < 15)
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), layout="constrained")
    for ax, values, label in zip(axes[:2], (ecg, ppg), ("ECG", "PPG pleth_3 (green)")):
        ax.plot(t[selected], np.asarray(values)[selected], linewidth=0.8)
        ax.set_ylabel(label + "\n(native CSV units)")
        ax.set_xlabel("Nominal sample time (s)")
    visible = [i for i in peaks if 10 <= t[i] < 15]
    axes[0].scatter(t[visible], np.asarray(ecg)[visible], s=18, color="red", label="Dataset peak annotation")
    axes[0].legend()
    axes[2].plot(t, elapsed, linewidth=1)
    axes[2].set(xlabel="Nominal sample time (s)", ylabel="Raw timestamp elapsed (s)")
    fig.suptitle("s1_sit: raw signals and a timestamp discontinuity")
    fig.supxlabel("Source: Mehrgardt et al., Pulse Transit Time PPG v1.1.0 | doi:10.13026/jpan-6n92 | ODbL 1.0", fontsize=8)
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/pulse-transit-time-ppg/1.1.0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/assignment-07")
    args = parser.parse_args()
    for name, digest in FILES.items():
        ensure_file(args.data_dir / name, digest, BASE + name, args.download)
    manifest = (args.data_dir / "SHA256SUMS.txt").read_text()
    if not any(line.split() == [FILES["csv/s1_sit.csv"], "csv/s1_sit.csv"] for line in manifest.splitlines()):
        raise ValueError("CSV checksum absent from publisher manifest")
    summary, signals = audit(args.data_dir / "csv/s1_sit.csv", args.data_dir / "s1_sit.hea")
    summary.update(source=SOURCE, source_version="1.1.0", input_sha256=FILES,
                   audit_code_sha256=sha256(__file__),
                   license="Open Data Commons Open Database License v1.0",
                   license_url="https://physionet.org/content/pulse-transit-time-ppg/view-license/1.1.0/")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(summary, signals, args.output_dir / "recording.png")
    print(json.dumps(summary, indent=2))
    print("Audit completed; raw timestamp timeline accepted:", summary["raw_timestamp_timeline_accepted"])
    # A completed audit is distinct from a passed dataset qualification.


if __name__ == "__main__":
    main()
