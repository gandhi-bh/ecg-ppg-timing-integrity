# ECG–PPG Timing Integrity

Research on correcting ECG–PPG timing errors while preserving physiological timing changes.

## Project details

- **Research vertical:** Sensing & Perception
- **Contributor:** Bhargav Gandhi
- **Status:** Research planning; no experimental results yet in this repository.

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

## First planned experiment

Start with computer-generated event times, rather than full sensor waveforms:

1. Create an example with a constant physiological delay and a drifting clock.
2. Create another with a changing physiological delay and an accurate clock.
3. Choose these changes so both examples have the same observed delay.
4. Apply a simple correction that removes the observed trend.
5. Measure whether it removes clock error or accidentally removes physiological change.

This will illustrate an ambiguity in the timing information. It will not prove
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
- `WORK_PROGRESS.md`: dated work record, findings, blockers, and next steps.
- [Assignment 02 research note](docs/research/assignment-02-literature-and-hypothesis.md):
  existing approaches, their limits, and our first precisely specified hypothesis.
- `.gitignore`: rules for keeping generated or private files out of Git.

Experiment code and run instructions will be added in a later assignment.

## Working process

Each assignment uses a branch named `assignment-XX`, followed by a pull request
into this repository's `main` branch. Bhargav reviews the work and performs all
branch creation, staging, commits, pushes, pull requests, and merges.
Codex assists with explanations and explicitly requested file changes.
Every assignment updates `WORK_PROGRESS.md` alongside the work it describes.
