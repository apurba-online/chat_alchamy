# ChatAlchemy Paper Experiment Execution

This file is the operational companion to `PUBLICATION_PROTOCOL.md`. It describes how to execute the pre-specified experiments without changing the scientific protocol.

## 1. Freeze candidate

Use one exact commit of `agent/chatalchemy-paper-system`. Before any primary run, require the normal `ChatAlchemy-Live CI` workflow to be green on that commit. Record the commit SHA in the manuscript experiment log. Do not modify method behavior after inspecting primary test results. A bug fix after freeze creates a new system version and requires rerunning affected comparisons.

## 2. Primary confirmatory campaign

Use the GitHub Actions workflow:

`ChatAlchemy Frozen Primary Campaign`

Default paper configuration:

- split: `test`
- difficulty: `all`
- benchmark: `LiveBioEvidenceBench-v2.1`
- benchmark seed: `1729`
- cases: `900`
- shards: `10`
- maximum concurrent live-source shards: `2`
- model: exact model ID chosen before the run

The workflow executes in this order:

1. validate the frozen publication artifact;
2. generate a study manifest;
3. build ten independent-live-oracle shards;
4. merge them into one fingerprinted oracle snapshot;
5. run ChatAlchemy-full against that snapshot;
6. run LLM-only, same-retrieval LLM, and unrestricted same-tools LLM-agent baselines against the same snapshot;
7. run the four component ablations plus the full system against the same snapshot;
8. validate and merge all shards;
9. generate CSV/LaTeX tables and paired statistics from the merged per-case results;
10. generate a reproducible failure-review sample when failures are available.

The campaign requires the repository secret `OPENAI_API_KEY` for model baselines. The secret is never written into an artifact. Token usage is retained from the Responses API usage object.

## 3. Oracle-state rule

Primary paired significance is valid only when systems share:

- the same benchmark fingerprint;
- the same case IDs; and
- the same frozen oracle snapshot file SHA-256, or the same single-iteration shared oracle result.

`generate_paper_tables.py` refuses paired significance when recorded oracle states or benchmark fingerprints differ. Do not override this guard to obtain a p-value.

## 4. Main output artifacts

The primary campaign retains:

- `campaign-study-manifest`
- `campaign-oracle-snapshot`
- `campaign-main-merged`
- `campaign-baseline-llm_only-merged`
- `campaign-baseline-same_retrieval_llm-merged`
- `campaign-baseline-unrestricted_tool_agent-merged`
- `campaign-ablations-merged`
- `campaign-paper-tables`

Raw per-case results are authoritative. Aggregate numbers and manuscript tables are derived artifacts.

The primary ChatAlchemy result preserves question, plan/routing outcome, final answer text, prediction, oracle value, claims, conflict assessments, source traces, evidence/provenance records, task score, latency, warnings, and oracle snapshot hash for later audit and expert review.

## 5. Entity-normalization experiment

Run the `entity_normalization` option in `ChatAlchemy Paper Experiments`.

The evaluator resolves the split-specific brand aliases through live RxNorm/RxNav and reports:

- resolution rate;
- exact canonical generic accuracy;
- accuracy conditional on successful resolution;
- a no-normalization string-match control;
- median latency;
- per-case RxCUI/source record.

Report test/stress separately from development results.

## 6. Source-failure experiments

Run the `failure_injection` experiment for each pre-specified source/fault combination. At minimum include both `exception` and `empty` modes for sources central to the main cross-source tasks. Never modify the upstream service. Retain paired control/injected per-case results and report qualification/abstention and unsupported-claim behavior in addition to task-score degradation.

## 7. Counterfactual grounding

Run the `counterfactual` experiment only with the frozen model identifier. Report GOS, PMIR, paired GOS gain, and paired PMIR reduction. Counterfactual evidence exists only inside the evaluator and is never written upstream.

## 8. Conflict evaluation

Conflict labels must be supplied privately through the GitHub Actions secret `CONFLICT_ANNOTATIONS_B64`. The source CSV contains two independent rater labels and an adjudicated label. The public result artifact contains aggregate/per-case predictions but does not expose the private annotation source unless intentionally released after the study.

Report macro-F1, class-level precision/recall/F1, confusion counts, and Cohen's kappa for the two independent raters.

## 9. External holdout

The holdout is authored by a researcher who did not implement the planner and remains private until the system configuration is frozen. Store it as base64 in the Actions secret `EXTERNAL_HOLDOUT_B64`.

The `external_holdout` workflow target:

1. materializes the private file only on the runner;
2. validates its schema;
3. records raw-file and canonical-content SHA-256 fingerprints;
4. runs only the frozen `full` system once;
5. retains the freeze manifest and results.

Do not run component ablations or prompt tuning on the private holdout after inspection.

## 10. Temporal evaluation

At T0, T1, T2, ... run `oracle_snapshot` with the same frozen benchmark version, seed, split, and difficulty. Preserve each merged snapshot. Use `compare_temporal_runs.py` to distinguish changed source-supported answers from source outages/schema failures.

The system remains frozen across temporal timepoints. If a later code version is evaluated, report it as a separate system-version experiment rather than mixing it with temporal adaptation.

## 11. Expert evaluation

After automatic results are locked, use `prepare_expert_evaluation.py` with matched system result files. The script:

- intersects case IDs across systems;
- samples reproducibly across task families;
- randomizes response order;
- assigns blinded system codes;
- emits a rater CSV and a separate private blinding key.

Keep the blinding key hidden until all independent reviewer scores are locked. Use 2-3 biomedical reviewers and the rubric in `backend/benchmark/EXPERT_EVALUATION.md`.

## 12. Failure taxonomy

Use `prepare_failure_review.py` on the frozen main result. Default paper sample size is 120 failures where available. Review categories are routing error, entity-normalization error, source retrieval failure, source incompleteness, deterministic-composition error, temporal mismatch, conflict-classification error, generation error, verification error, oracle ambiguity, and other.

The sample is deterministic at seed 1729 and stratified across task families.

## 13. Paper tables and statistics

Use `generate_paper_tables.py` only on merged/frozen result files. It writes:

- `table_main.csv`
- `table_main.tex`
- `table_by_family.csv`
- `paired_statistics.json`
- `manifest.json`

Paired inference uses 10,000-resample bootstrap confidence intervals, exact McNemar tests for exact-correct outcomes, and Holm-Bonferroni correction across the pre-specified comparisons.

Never manually edit numeric table cells. If presentation formatting is changed in LaTeX, preserve the generated numeric values.

## 14. Results that cannot be pre-filled

Do not populate manuscript result claims until the corresponding real artifacts exist. In particular, the following require external collection and are not implementation placeholders:

- 900-case primary test outcomes;
- model-baseline outputs;
- independent private holdout performance;
- two-rater conflict annotations;
- later temporal timepoints;
- blinded human ratings.

A missing experiment is reported as incomplete, never inferred from smoke tests or unit tests.
