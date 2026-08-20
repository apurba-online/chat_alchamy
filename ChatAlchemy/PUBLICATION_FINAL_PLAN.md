# ChatAlchemy Final Publication Plan

This document defines the final execution path from frozen system to submission-ready manuscript. It does not change the frozen scientific method.

## Frozen study identity

- Method commit: `0b994c97e496d581ef3ae68bdb6503431ea1d664`
- Benchmark: `LiveBioEvidenceBench-v2.1`
- Seed: `1729`
- Confirmatory split: `test`, n=900
- Stress split: n=300
- Model baseline: `gpt-5.6-sol`
- Publication campaign branch: `paper-campaign-gpt56-2026-08-19`

No tuning of the frozen method is allowed after examining confirmatory test results. Software fixes are permitted only when they correct an implementation defect without changing the intended method; any such fix requires a new frozen identity and rerun of affected confirmatory experiments.

## Stage 1 — Automated confirmatory campaign

Required artifacts:

1. Independent live oracle snapshot for the 900-case test split.
2. Full ChatAlchemy results on the identical frozen cases.
3. GPT-5.6 Sol LLM-only baseline.
4. GPT-5.6 Sol same-retrieval baseline.
5. GPT-5.6 Sol unrestricted same-tools agent baseline.
6. Full ablation matrix:
   - no entity normalization;
   - no deterministic cross-source composition;
   - no conflict analysis;
   - no claim verifier.
7. Common-case paired comparisons.
8. 95% paired bootstrap confidence intervals.
9. Exact McNemar tests for exact-correct binary outcomes.
10. Holm-Bonferroni correction for the pre-specified comparison family.
11. Programmatic CSV and LaTeX result tables.
12. Efficiency metrics: p50/p95 latency, API calls, model tokens, and model cost.
13. Deterministic failure-review sample.

The same frozen oracle state must be used for all primary systems. Results from different oracle snapshots must never be combined in paired significance tests.

## Stage 2 — Automated robustness studies

After Stage 1:

1. Run the 300-case stress split and report it separately from confirmatory test results.
2. Run entity-normalization evaluation with the no-normalization control.
3. Run counterfactual grounding evaluation and report GOS and PMIR.
4. Run controlled source-failure experiments for every live source under both exception and empty-response conditions.
5. Separate source/API failures from reasoning errors and report abstention/unsupported-answer behavior.

## Stage 3 — Temporal evaluation

T0 is the publication-campaign source/oracle state.

- T1: August 26, 2026.
- T2: September 18, 2026.

Each timepoint must use the immutable method, benchmark seed, and identical frozen case IDs. For every comparison:

- separate genuine oracle/source-state changes from API/schema availability changes;
- calculate temporal adaptation performance only on genuine changed-oracle cases;
- report stale-prediction behavior separately;
- preserve raw oracle and system results for every timepoint.

If the manuscript is submitted before the temporal study is mature, the temporal contribution must be narrowed or removed rather than inferred from insufficient observations.

## Stage 4 — Independent external validation

An independent collaborator must create a private holdout after method freeze. Recommended size: 200–300 questions with unseen entities/combinations and more natural wording than the templated public benchmark.

Required procedure:

1. Validate and fingerprint the holdout before evaluation.
2. Do not expose answer labels to the implementation team before fingerprinting.
3. Evaluate the immutable frozen system exactly once.
4. Do not tune or retry based on holdout accuracy.
5. Preserve the raw result and fingerprint.

The implementation team must not self-author a supposedly independent holdout and call it independent validation.

## Stage 5 — Conflict/context annotation

Prepare 300–500 evidence pairs spanning:

- agreement;
- complementary evidence;
- context difference;
- true conflict.

Two independent annotators label the set before adjudication. Preserve raw labels. Report macro-F1, per-class precision/recall/F1, confusion matrix, and Cohen's kappa. Adjudicated labels must not replace the raw inter-annotator analysis.

## Stage 6 — Blinded expert evaluation

Use 150–200 stratified responses from the main systems. Recruit 2–3 independent biomedical reviewers.

Reviewers receive blinded/randomized system outputs and score:

- factual correctness;
- evidence grounding;
- completeness;
- appropriate uncertainty;
- scientific usefulness;
- binary usefulness as a starting point for further research.

Calculate inter-rater agreement before any adjudication. This is research-assistance evaluation, not clinical validation.

## Stage 7 — Manuscript assembly

Only after the required evidence gates are complete:

1. Lock raw result artifacts and hashes.
2. Generate all manuscript tables programmatically from raw results.
3. Generate final figures from frozen artifacts.
4. Write Methods from the frozen implementation and protocol.
5. Write Results only from generated tables/statistics.
6. Build the Discussion around demonstrated effects and the observed failure taxonomy.
7. Include external holdout and expert evaluation without post-hoc tuning.
8. Verify every numerical claim against its raw artifact.
9. Archive exact git SHA, benchmark fingerprint, model ID, prompt version, seed, retrieval timestamps, package versions, and reproduction commands.
10. Perform a clean-environment reproduction smoke.
11. Audit claims and citations.

## Submission-ready rule

The project may be called **READY FOR SUBMISSION** only when:

- the full automated confirmatory campaign is complete and valid;
- required robustness studies are complete;
- external holdout and blinded human evaluation are complete for claims that depend on them;
- temporal evaluation is complete if temporal adaptation is retained as a headline contribution;
- final tables/figures regenerate from frozen raw artifacts;
- the clean reproduction check passes;
- unsupported novelty, clinical-safety, and efficacy claims have been removed;
- limitations explicitly cover templated language, public-source coverage, live-source instability, and lack of clinical validation.

Canonical tracking issues:

- Issue #5 — publication readiness gate.
- Issue #6 — independent holdout, conflict annotation, and expert-review handoff.
- Issue #7 — final manuscript assembly.
