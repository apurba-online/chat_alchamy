# ChatAlchemy Publication Protocol

This document defines the pre-specified experimental protocol for the ChatAlchemy paper. Changes that alter task definitions, benchmark splits, primary metrics, or statistical tests after test-set inspection must be documented as post-hoc analyses.

## Scientific question

ChatAlchemy evaluates whether typed planning, live biomedical database federation, entity normalization, deterministic evidence operations, conflict handling, and claim-level verification improve correctness and grounding when biomedical evidence is distributed across evolving online sources.

The product UI is a demonstration surface. The scientific contribution is the evidence-state reasoning and evaluation framework.

## Benchmark

- Benchmark: `LiveBioEvidenceBench-v2`
- Default seed: `1729`
- Nominal size: `1500` cases
- Splits: `dev`, `test`, `stress`
- Entity pools are disjoint across splits.
- Test/stress examples must not be used for prompt tuning, rule tuning, source-specific bug fixes, or threshold selection.
- The independent live oracle must not call the ChatAlchemy planner, generator, conflict classifier, or claim verifier.
- Raw live responses may be stored only as experiment/audit artifacts with retrieval timestamps; they are not an application knowledge base.

### Development policy

Only `dev` may be used for iterative development. Bugs discovered on `test` or `stress` may be fixed only if the fix is source-contract/general software correctness and is not tailored to a specific test answer. Any such fix must be logged in the paper artifact history and the affected evaluation rerun from scratch.

### External holdout

A separate author-independent holdout should be created after architecture freeze. It must remain unavailable to implementation decisions. Before evaluation, record only its count, SHA-256 fingerprint, schema version, and freeze time using `scripts/freeze_external_holdout.py`.

## Systems compared

Primary comparisons should use the same test items and, where applicable, the same live-source retrieval time window.

1. `LLM-only`: model receives the question without tool evidence.
2. `Same-retrieval LLM`: model receives the evidence retrieved by ChatAlchemy but performs the reasoning/generation itself.
3. `Unrestricted tool agent`: same available source set, but tool selection/combination is delegated to the model.
4. `ChatAlchemy full`: typed planner + normalization + deterministic operations + conflict handling + verification.
5. Component ablations:
   - no normalization
   - no deterministic join
   - no conflict analysis
   - no verifier

If an external biomedical agent can be reproduced with overlapping source/task coverage, report it separately and describe coverage differences rather than forcing incomparable aggregate scores.

## Primary outcomes

Primary endpoint:
- mean task score on the frozen `test` split.

Co-primary reliability outcomes:
- supported-claim rate
- source execution success
- oracle coverage

Secondary outcomes:
- set F1 / structured record accuracy by task family
- routing accuracy
- entity normalization accuracy
- attribution precision
- abstention precision
- conflict macro-F1
- Grounded Obedience Score (GOS)
- Parametric Memory Intrusion Rate (PMIR)
- p50/p95 latency
- API calls per question
- token and monetary cost where model APIs are used

`stress` is reported separately and must not be pooled into the primary test score.

## Statistics

For paired system comparisons on continuous per-case scores:
- report the paired mean difference with 95% paired-bootstrap CI (10,000 resamples).

For paired binary exact-correct outcomes:
- use exact McNemar testing.

For multiple pre-specified pairwise hypothesis tests:
- control family-wise error with Holm-Bonferroni.

Report effect sizes and confidence intervals in addition to p-values. Do not report significance when oracle coverage differs materially without also reporting a common-case analysis.

## Temporal evaluation

At repeated time points `T0...Tk`, rerun the same frozen case IDs and independent oracle. For cases whose oracle answer changes, report temporal adaptation accuracy: the fraction for which the system changes to the new oracle-supported answer. Also report source outages separately from semantic answer changes.

## Counterfactual grounding

Counterfactual evidence experiments are evaluation-only. They must not alter external APIs. The model is explicitly instructed to use the supplied evidence. Report GOS and PMIR and preserve the injected evidence, expected answer, and forbidden-memory answer in the experiment artifact.

## Human evaluation

Use 2-3 biomedical reviewers on a blinded, randomized subset of 150-200 responses. Reviewers score factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness on fixed 1-5 rubrics. Collect ratings independently before adjudication. Report inter-rater agreement and system identity must remain hidden during initial scoring.

## Reproducibility

Every result artifact must include:
- benchmark version and seed
- split and difficulty filters
- git commit SHA
- model/provider and exact model identifier
- prompt version
- run start/end UTC timestamps
- source trace timestamps
- configured ablation flags
- software/runtime versions when available
- aggregate and per-case results

Final paper tables must be generated from saved result artifacts, not manually transcribed.

## Freeze criteria

The architecture is considered frozen when:
- offline tests pass
- live source contract tests pass
- frontend typecheck/build pass
- benchmark leakage tests pass
- preview smoke tests pass
- no known high-severity security issue remains

After freeze, modifications that change model behavior require a new experiment version and complete rerun of all affected primary comparisons.
