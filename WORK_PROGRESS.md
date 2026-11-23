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

## 2026-11-16 — Assignment 04: Independent timing and noise sensitivity

**Contributor:** Bhargav Gandhi, with Codex-assisted research and implementation.

### Work completed

- Expanded the experiment to 72 conditions varying physiological trend, clock
  trend, clock offset, observation noise, and clock-anchor uncertainty.
- Evaluated four methods over 20 seeds per condition and saved full metrics,
  settings, source hashes, and a sensitivity figure.
- Passed 16 tests locally, retaining the original seven regression checks.
- Derived the noise-free slope-removal benefit boundary and documented cases
  where noisy anchors worsen correction or exact endpoints miss nonlinear drift.
- Reviewed additional related project documentation and the author-lab abstract;
  recorded provenance and reading limits in the
  [Assignment 04 report](docs/research/assignment-04-sensitivity.md).
- Extended CI to execute the sensitivity study.

## 2026-11-23 — Assignment 05: Nonlinear drift and selective correction

**Contributor:** Bhargav Gandhi, with Codex-assisted implementation and analysis.

### Work completed

- Added five clock profiles, four anchor spacings, and an event-level correction
  gate based on propagated anchor-measurement uncertainty.
- Selected the threshold using development seeds and evaluated on disjoint seeds
  across 160 conditions; saved complete metrics, settings, hashes, and a figure.
- Measured reduced >1 ms MAE-worsening frequency versus always correcting on this
  grid; documented residual failures and a tradeoff for linear drift.
- Passed all 25 local tests, preserving the previous 16 checks; extended CI.
- Recorded the hidden-oscillation failure and next research question in the
  [Assignment 05 report](docs/research/assignment-05-selective-correction.md).
