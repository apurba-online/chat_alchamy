# ChatAlchemy publication evaluation protocol

This file defines the evaluation contract for the paper. Change it only before the system/test configuration is frozen; any later change must be versioned and disclosed.

## Scientific claim under test

ChatAlchemy is evaluated as a provenance-preserving reasoning system over live biomedical databases. The core comparison claim is that typed planning, cross-source normalization, deterministic evidence operations, contextual conflict handling, and claim verification improve reliability compared with weaker reasoning harnesses under equivalent query conditions.

The user interface is a demonstration layer. Product features that lack an independent ground-truth procedure are tested as software functionality, not counted as benchmark wins.

## Public LiveBioEvidenceBench-v2

- 1,500 deterministic query specifications at seed `1729`.
- Gold answers are **not stored**. They are recomputed at evaluation time by `LiveOracle`, which calls public APIs independently of the ChatAlchemy planner/generator.
- Public partitions: `dev=300`, `test=900`, `stress=300`.
- Drug, target, gene, and condition pools are entity-disjoint across those partitions.
- Cases are stratified across task families and labeled `easy`, `medium`, or `hard`.
- Every generated benchmark has a SHA-256 fingerprint and manifest.
- The same question set, source budgets, result limits, retry policy, and scoring rules must be used for paired system comparisons.

The public test set may be used for reproducible comparisons but is not considered an independent private holdout.

## Private external holdout

After the system is frozen, obtain approximately 300 independently authored biomedical questions from a researcher who did not implement the planner. Questions should match the supported evidence operations but should not be generated from the public templates.

Requirements:

1. Keep the source file private from system developers until the system configuration is frozen.
2. Record task family, required source(s), expected operation, entity fields, and oracle procedure; do not hand-write time-sensitive answers.
3. Run `scripts/freeze_external_holdout.py` and preserve its SHA-256 manifest before evaluation.
4. Do not tune prompts, regex rules, source selection, or model settings after inspecting holdout results.
5. Report all valid holdout cases, including zero-result cases. Document exclusions and their reasons.

## Broken-problem and oracle-outage policy

A case whose independent oracle cannot execute is **not silently counted as a model error or success**. Report oracle coverage separately. Before the final frozen evaluation, audit persistent failures:

- transient source/API outage: retain the case and repeat according to the preregistered retry policy;
- entity/source incompatibility or malformed benchmark item confirmed on repeated runs: mark the case invalid and replace it before benchmark freeze;
- post-freeze invalid item: report it as excluded with an explicit reason and do not replace it.

Always report the number and fraction of oracle-unavailable cases.

## Systems to compare

Minimum experimental matrix:

1. `ChatAlchemy-full`.
2. `no_normalization` ablation.
3. `no_deterministic_join` ablation.
4. `no_conflict` ablation.
5. `no_verifier` ablation.
6. `llm_only`: same question, no retrieved evidence.
7. `same_retrieval_llm`: same live evidence objects as ChatAlchemy, but the LLM performs final composition instead of the deterministic reasoning result.

When additional external agent baselines are used, match source/tool access and clearly document any harness differences rather than presenting unlike systems as directly equivalent.

## Primary metrics

Report at least:

- task score / set F1 or structured-record score;
- routing accuracy;
- oracle coverage;
- live-source execution success;
- claim-producing rate;
- supported-claim rate **conditional on cases that actually make claims**;
- fully-supported claim-case rate;
- provenance record F1 against the independent oracle trace;
- median and p95 latency;
- mean API calls and evidence items per question.

Do not use a supported-claim score of 1.0 on abstentions as evidence that the system is well grounded; claim coverage and support must be reported together.

## Counterfactual grounding

Use `run_counterfactual.py` only with synthetic evaluation evidence. Never modify public biomedical APIs. Measure Grounded Obedience Score (GOS) and Parametric Memory Intrusion Rate (PMIR). Counterfactual facts must be clearly isolated from production answers.

## Source-failure robustness

Use `run_failure_injection.py` to inject deterministic exception/empty-result failures at the source adapter boundary. Evaluate:

- task-score degradation;
- whether the source failure is observable in traces/warnings;
- qualified-answer or abstention rate;
- unsupported-claim case rate.

Run at least one experiment for each source used in the main benchmark.

## Temporal evaluation

Repeat the same frozen benchmark configuration at multiple real timepoints. Preserve benchmark fingerprint, source record IDs, retrieval timestamps, and oracle snapshot hashes. Temporal adaptation is scored only on cases whose oracle state actually changed between runs.

Do not alter the system between temporal timepoints unless a new system version is explicitly evaluated as a separate condition.

## Human expert evaluation

After automatic experiments are frozen, sample 150-200 questions stratified by task family and difficulty. Use 2-3 independent biomedical reviewers and the blinded template in this directory. Reviewers score factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness. Preserve raw ratings and report agreement.

## Statistical analysis

For paired systems:

- paired bootstrap confidence intervals for mean-score differences;
- exact McNemar test for paired binary correctness when applicable;
- Holm-Bonferroni correction across multiple planned hypothesis tests;
- effect sizes and 95% confidence intervals, not p-values alone.

All comparison scripts must align cases by benchmark ID.

## Reproducibility record

For every reported run preserve:

- Git commit SHA;
- benchmark fingerprint and seed;
- system/ablation configuration;
- model/provider identifier when a model baseline is used;
- prompt version;
- source retry/result limits;
- start/end timestamps;
- raw case-level predictions and oracle outputs;
- source record IDs and snapshot hashes;
- aggregate result JSON generated from the raw cases.

Paper tables and figures should be generated from these artifacts rather than manually transcribed.

## Scope and safety

This evaluation concerns biomedical research assistance and database reasoning. It does not establish clinical safety, diagnostic accuracy, or suitability for autonomous patient-care decisions.
