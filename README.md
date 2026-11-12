# ECG–PPG Timing Integrity

Research on correcting ECG–PPG timing errors while preserving physiological timing changes.

## Project details

- **Research vertical:** Sensing & Perception
- **Contributor:** Bhargav Gandhi
- **Status:** First synthetic experiment implemented and checked against its analytical predictions.

## The idea in simple language

An ECG records the heart's electrical activity. A PPG records changes in blood
volume using light, such as at a finger. The corresponding events do not happen
at exactly the same time: there is a real delay between them.

If the recording devices' clocks disagree, that adds a timing error. Software
that tries to remove this error could also remove a real change in the delay.
We want to investigate when this happens and how to measure it.

## Research question

Can we correct clock errors between ECG and PPG recordings without erasing
real changes in their physiological timing relationship?

## Starting hypothesis

A correction method that assumes the ECG-to-PPG delay should stay constant
may erase a genuine change in that delay. We will test this using examples
where we know which changes come from the simulated clock and which come
from the simulated physiology.

## First experiment

Uses computer-generated event times, rather than full sensor waveforms:

1. Create an example with a constant physiological delay and a drifting clock.
2. Create another with a changing physiological delay and an accurate clock.
3. Choose these changes so both examples have the same observed delay.
4. Apply a simple correction that removes the observed trend.
5. Measure whether it removes clock error or accidentally removes physiological change.

This illustrates an ambiguity in the timing information. It does not prove
that every synchronization method fails, or establish a new clinical finding.

## Data and equipment

The first experiment needs only a computer and synthetic data that we generate.
Later experiments may use existing public ECG/PPG recordings after we review
their documentation, access conditions, and suitability. No new sensor hardware
or participant recordings are required for the planned work.

## How we will evaluate the work

- Measure how much of a known, added clock error remains after correction.
- Measure how much the correction changes the original physiological delay pattern.
- Compare correction methods against leaving the timing unchanged.
- Record assumptions, failures, and cases where the available information is insufficient.

For public recordings, knowing the error we add does not mean we know the
recording's original physiological timing perfectly.

## Expected outcome

A reproducible experiment, a comparison of simple correction methods, and a
report explaining when timing correction helps and when it can mislead.
An improvement is a research possibility, not a guaranteed outcome.

## Repository contents

- `README.md`: project question, scope, and intended outcome.
- `WORK_PROGRESS.md`: dated record of completed work.
- [Assignment 02 research note](docs/research/assignment-02-literature-and-hypothesis.md):
  existing approaches, their limits, and our first precisely specified hypothesis.
- `.gitignore`: rules for keeping generated or private files out of Git.
- `experiments/`: synthetic experiment and plotting code.
- `tests/`: analytical and reproducibility checks.
- [Assignment 03 results](docs/research/assignment-03-results.md): measured results,
  interpretation, and limitations.

## Run Assignment 03

Use Python 3.12. From the repository root, create an isolated environment once:

```bash
python -m venv .venv
```

In Git Bash on Windows:

```bash
source .venv/Scripts/activate
```

On macOS/Linux, use `source .venv/bin/activate` instead. Then run:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m experiments.paired_timing
```

Outputs are written to `results/assignment-03/`: `metrics.csv`, `events.csv`,
`summary.json`, and PNG/SVG figures. This generated directory is ignored by Git;
a curated result snapshot is linked in the report. The summary records settings,
source hashes, and runtime versions. Use `--output-dir PATH` to keep a separate run.

For numerical results without plotting dependencies:

```bash
python -m experiments.paired_timing --no-plot
```

The local Windows environment for the first run used Python 3.12.7.
`.github/workflows/research-ci.yml` runs the tests and full experiment on pushes
to `main`/`assignment-*` and PRs targeting `main`. Hosted CI must pass before merging;
local test results do not establish the hosted result.
See [GitHub Actions documentation](https://docs.github.com/en/actions/get-started/quickstart).

## Working process

Each assignment uses a branch named `assignment-XX`, followed by a pull request
into this repository's `main` branch. Bhargav reviews the work and performs all
branch creation, staging, commits, pushes, pull requests, and merges.
Codex assists with explanations and explicitly requested file changes.
Every assignment updates `WORK_PROGRESS.md` alongside the work it describes.
