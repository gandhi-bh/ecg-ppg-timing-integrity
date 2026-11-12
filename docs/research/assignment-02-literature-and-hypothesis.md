# Assignment 02: Existing methods and our first hypothesis

Reviewed: 2026-11-12. Contributor: Bhargav Gandhi, with Codex-assisted research.
Status: focused literature review and experiment specification; no new experimental results.

## 1. What we are trying to learn

Can we correct ECG–PPG clock errors without removing a real change in the time
between the heart's electrical activity and the arrival of the peripheral pulse?

Our immediate goal is to build a reproducible test of this failure mode. Our
longer-term goal is to establish when correction is trustworthy, what additional
timing information it requires, and when an algorithm should report uncertainty.

## 2. Terms we must keep separate

- **Beat matching:** deciding which ECG heartbeat belongs with which PPG pulse.
- **Clock correction:** putting recording timestamps onto a consistent time base.
- **PAT (pulse arrival time):** here, the interval from an ECG R-peak to the foot
  (start of the upstroke) of the corresponding peripheral PPG pulse.
- **PTT (pulse transit time):** transit between vascular locations; ECG-to-PPG
  timing also includes cardiac electromechanical timing and should not be called
  pure PTT. Some source titles use PTT more broadly; we retain their titles.

The PAT definition follows Montree et al. [S7]. We will keep the PPG landmark
fixed: a pulse peak and a pulse foot are not interchangeable timing references.

Matching beats correctly does not, by itself, establish an accurate PAT.

## 3. What existing approaches do

The final column gives our assessment for this project, not a demonstrated
failure of the cited implementation. These approaches solve different tasks;
their reported accuracy numbers should not be ranked as if measured identically.

| Approach and source | What the source does | Information or assumptions it uses | Relevance and limits for us |
| --- | --- | --- | --- |
| Hardware triggering and delay calibration [S1] | Triggers PPG acquisition from ECG timing and accounts for acquisition/filter delays. | Access to device timing and configuration. | Independent timing information can avoid attributing all observed delay to physiology. We can simulate such information without buying hardware. |
| Same-signal cross-correlation [S2] | Aligns a common signal type recorded across devices; evaluated using ECG signals. | A sufficiently similar common signal, with attention to signal quality and sampling. | A reference ECG channel could help synchronize devices. This is not evidence that directly correlating ECG amplitudes with PPG amplitudes preserves PAT. |
| Beat-pattern matching plus regression [S3] | Patent disclosure matches ECG/PPG segments and fits offset/drift from matched time locations. | Corresponding beat patterns and a fitted clock relationship. | Useful prior art for drift estimation. The patent is a method disclosure, not independent evidence of physiological-change preservation. Our simple detrending baseline will not be called a reproduction of it. |
| Nonlinear HRV/PRV alignment [S4] | Uses normalized mutual information from distance matrices of heartbeat/pulse interval variability. | Related variability patterns and sufficient signal quality. | The paper explicitly limits its suitability for blood-pressure estimation based on HRV–PRV differences. Its alignment evaluation is not a millisecond PAT-preservation guarantee. |
| Device-artifact correction with beat matching [S5] | Published abstract describes heartbeat matching using variability, experimental hardware timing profiling, and temporal-uncertainty modeling. | Device-specific timing information in addition to recorded waveforms. | Closest prior work: it already addresses multiple timing confounders. Full published methods remain to be reviewed before reproduction or detailed comparison. |
| Sawtooth-artifact analysis [S6] | Identifies and analyzes a recurring artifact in monitor-derived timing; illustrates a removal approach. | A recognizable artifact pattern in particular monitor recordings. | Timing artifacts are already documented. The authors caution that the removal approach needs further evaluation and may not generalize to other artifacts. |

Adjacent work: Montree et al. [S7] estimates PAT more accurately in low-rate
recordings using template matching. This concerns timing-feature estimation;
it does not establish a general solution to separating clock drift from PAT change.

## 4. What is already known, and what remains our candidate contribution

We cannot claim to discover that ECG/PPG recordings contain timing artifacts:
[S6] documents this, and [S5] develops a correction methodology. Nor can we claim
that physiological differences are universally ignored: [S4] explicitly discusses
a limitation relevant to such differences.

**Candidate contribution:** an openly reproducible benchmark that varies clock
error and physiological timing independently, evaluates both correction and
distortion, and states what information each method receives.

This is a project direction, not a verified novelty claim. This focused review
does not prove that no comparable benchmark exists. Before claiming novelty,
review the full published methods of [S5], trace benchmark/code references from
[S4–S6], and search specifically for PAT-preservation and identifiability benchmarks.

## 5. Why the problem can be ambiguous

Our simplified event-time model is:

```text
observed_delay_i = true_PAT_i + relative_clock_error_i + timing_noise_i
```

All delay terms are in milliseconds. The ECG timeline is the reference. For the
first experiment, beat identities are known, noise is zero, and device/filter
delays are zero. Real recordings need those additional effects modeled separately.

**Our mathematical inference:** if the only input is the observed delay, adding
any function g_i to true PAT and subtracting g_i from clock error leaves the
observation unchanged. Therefore, those inputs alone cannot uniquely determine
both components without extra assumptions or independent information.

This statement is conditional on our observation model. It is not an impossibility
claim about every waveform-based method or every device configuration.

## 6. One precise, testable hypothesis: H1

**H1:** In the noise-free paired scenarios below, a method that estimates clock
drift by fitting a straight line to observed ECG–PPG delays and subtracting its
slope will remove the 60 ms clock drift in A, but will also erase the 60 ms
physiological change in B, producing a 60 ms endpoint error in B.

Use 601 event pairs, with ECG reference times t = 0, 1, ..., 600 seconds.
Here t is in seconds; every expression in the table is in milliseconds.

| Scenario | True PAT | Relative clock error | Observed delay |
| --- | --- | --- | --- |
| A: clock changes | 200 | 0.1 × t | 200 + 0.1 × t |
| B: physiology changes | 200 + 0.1 × t | 0 | 200 + 0.1 × t |

The drift slope is 0.1 ms/s, equivalent to 100 parts per million in this additive
model. These are illustrative test settings, not measured values or clinical norms.

Fit observed_delay = intercept + slope × t by ordinary least squares, then use:

```text
corrected_delay_i = observed_delay_i - fitted_slope * (t_i - t_0)
```

The method keeps the initial level; it does not subtract the 200 ms baseline.
H1 concerns this explicit baseline, not the full algorithms in the literature.

### Controls and measurements

1. **No correction:** establishes the starting error in each scenario.
2. **Slope removal:** tests H1 using only reference times and observed delays.
3. **Oracle correction:** subtracts the actual simulated clock error. This is a
   privileged-information control, not a deployable competitor.

For each scenario and method, report:

- PAT mean absolute error: mean absolute difference from true PAT, in ms.
- PAT endpoint error: absolute difference from true PAT at t = 600 s, in ms.
- Change distortion: absolute difference between corrected start-to-end change
  and true start-to-end change, in ms.

In this noise-free model, PAT estimation error and residual clock-correction
error are algebraically linked; do not present them as independent evidence.

**Predicted, not measured:** slope removal returns a constant 200 ms in both
scenarios; endpoint errors are 0 ms in A and 60 ms in B. No correction is exact
in B; the oracle is exact in both. Verify numerical agreement within 1e-6 ms.

This first test is an analytically predictable implementation check. If code
disagrees, investigate the implementation or model before claiming a discovery.
The substantive research comes from extending the benchmark and testing methods
with realistic uncertainty and clearly specified extra information.

## 7. What extra information could help?

These are possible directions, not dependencies for our first experiment:

- **Independent timing anchors:** shared triggers or trustworthy clock observations
  at multiple times can constrain drift, rather than inferring it from PAT.
  Two exact anchors identify an affine clock map, but not arbitrary nonlinear drift.
- **Device-delay measurements:** buffering/filter calibration helps separate
  instrument delay from physiology, as motivated by [S1, S5].
- **A common reference signal:** the same signal recorded on both devices can
  provide alignment evidence without assuming ECG-to-PPG delay is constant [S2].
- **Explicit prior assumptions:** bounded drift or different change time scales
  may help, but are assumptions to stress-test, not independent ground truth.

We can simulate anchors and calibration information. Additional sensors or
participant recruitment are not required for this project's initial stages.

## 8. How this grows into an ongoing project

1. Assignment 03: implement the paired scenarios, controls, metrics, plots, and
   automated checks. Keep simulator truth separate from algorithm inputs.
2. Expand to independent physiological and clock trends, noise, missing beats,
   and non-linear drift. Keep the simple scenarios as permanent regression checks.
3. Add a method using simulated timing anchors; evaluate how anchor uncertainty
   and spacing affect both correction error and preservation of physiological change.
4. Examine public recordings and inject known errors into copies. Their original
   timing is a reference for added-error recovery, not perfect physiological truth.
5. Reproduce a suitable published method only after documenting its assumptions,
   available implementation, required inputs, and evaluation target.

Carry forward experiment settings, seeds when randomness is introduced, method
versions, failed cases, and dated decisions. Later changes should extend the
benchmark while keeping earlier results reproducible.

## 9. Sources and reading coverage

Focused web search on 2026-11-12, using queries around ECG/PPG synchronization,
clock drift, PAT, and physiological-delay preservation. Primary research,
author-hosted papers, a manufacturer note, and a patent were used. This is not
a systematic review. Access limitations are recorded rather than treated as full reads.

- **S1 — Don Elloway, Analog Devices:** [Chips to Measure ECG and PPG with Temporal Correlation](https://www.analog.com/en/resources/design-notes/chips-to-measure-ecg-and-ppg-with-temporal-correlation--maxim-integrated.html).
  Read the system overview and timing/delay sections. Manufacturer application note.
- **S2 — Xiao, Ding and Hu (2022):** [Time Synchronization of Multimodal Physiological Signals through Alignment of Common Signal Types and Its Technical Considerations in Digital Health](https://www.mdpi.com/2313-433X/8/5/120).
  DOI: 10.3390/jimaging8050120. Read publisher abstract and reviewed method scope.
- **S3 — WO2021160306A1 (2021):** [Computer-implemented method for synchronizing a PPG signal with an ECG signal](https://patents.google.com/patent/WO2021160306A1/en).
  Read the segment-matching and regression description, especially paragraphs 49–54.
  Patent disclosure; not a peer-reviewed performance comparison.
- **S4 — Padovano et al. (2025):** [A Novel Nonlinear Method for Cardiovascular Data Synchronization](https://publications.pik-potsdam.de/rest/items/item_32558_1/component/file_32559/content?download=true).
  DOI: 10.1109/ACCESS.2025.3571070. Read abstract, approach description,
  limitations and conclusion in the author-hosted publisher PDF.
- **S5 — Ruffolo et al. (2025):** [High-fidelity measurement of pulse arrival time in critically ill children using standard bedside monitoring equipment](https://pubmed.ncbi.nlm.nih.gov/41187451/).
  DOI: 10.1088/1361-6579/ae1b70. Published abstract retrieved through indexed
  PubMed text; direct page retrieval was incomplete. Earlier medRxiv full-text
  access was blocked. Detailed published-method review is outstanding.
- **S6 — Lin et al. (2019):** [Unexpected sawtooth artifact in beat-to-beat pulse transit time measured from patient monitor data](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0221319).
  DOI: 10.1371/journal.pone.0221319. Read abstract, discussion, artifact-removal
  illustration description, and limitations in the publisher text.
- **S7 — Montree et al. (2024):** [Increasing accuracy of pulse arrival time estimation in low frequency recordings](https://pubmed.ncbi.nlm.nih.gov/38387047/).
  DOI: 10.1088/1361-6579/ad2c12. Reviewed indexed abstract and PDF introduction
  excerpts; full PDF retrieval was blocked. Detailed reproduction is out of scope here.
