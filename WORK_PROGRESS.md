# Work Progress

Keep earlier entries. Add a dated entry for each work session that produces
changes, and commit it with the work it describes.

## 2026-11-12 — Assignment 01: Define the research project

**Contributor:** Bhargav Gandhi, with Codex assistance for documentation.

### Work completed

- Created the public repository and cloned it locally (Bhargav).
- Created the `assignment-01` branch (Bhargav).
- Expanded the README with the research question, initial hypothesis, scope,
  evaluation goals, and expected outcome.
- Started this dated research log.

## 2026-11-12 — Assignment 02: Literature review and first hypothesis

**Contributor:** Bhargav Gandhi, with Codex-assisted literature research and writing.

### Work completed

- Compared hardware timing, common-signal alignment, beat-pattern regression,
  nonlinear variability alignment, and device-artifact correction approaches.
- Recorded seven primary sources with reading coverage and access limitations.
- Defined H1, a controlled clock-drift versus physiological-change test, with
  explicit inputs, controls, metrics, and predicted outcomes.
- Added the [research note](docs/research/assignment-02-literature-and-hypothesis.md)
  and linked it from the README.

## 2026-11-12 — Assignment 03: Implement the paired timing experiment

**Contributor:** Bhargav Gandhi, with Codex-assisted implementation and validation.

### Work completed

- Implemented the two specified synthetic scenarios, three correction controls,
  and numerical exports with settings and source hashes.
- Passed seven analytical, input-validation, and reproducibility tests locally.
- Measured the predicted 60 ms endpoint error when slope removal erases the
  physiological change; recorded the full comparison in the
  [results report](docs/research/assignment-03-results.md).
- Added an isolated Python environment setup and a GitHub Actions workflow
  for tests and experiment execution; hosted execution awaits submission.
- Generated and visually checked the result figure; saved the metric and
  provenance snapshots and pinned the tested plotting dependencies.
