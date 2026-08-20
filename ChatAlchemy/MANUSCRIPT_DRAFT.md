# ChatAlchemy-Live: Provenance-Preserving Reasoning over Evolving Biomedical Evidence

> Working manuscript draft. Methods and experimental design are grounded in the frozen implementation and pre-specified protocol. Numerical Results must be inserted only from frozen machine-generated artifacts. Do not manually invent or transcribe unverified values.

## Abstract

Biomedical evidence is distributed across heterogeneous databases that differ in identifiers, record structure, scope, update cadence, and contextual qualifiers. We present ChatAlchemy-Live, a biomedical research-assistance system that combines typed query planning, live database federation, entity normalization, deterministic cross-source evidence operations, context-aware evidence relation analysis, provenance tracking, and claim-level verification. We evaluate the system using LiveBioEvidenceBench-v2.1, a 1,500-state dynamic benchmark with entity-disjoint development, test, and stress partitions and an independent live-data oracle. The confirmatory evaluation compares ChatAlchemy against GPT-5.6 Sol LLM-only, same-retrieval LLM, and unrestricted same-tools agent baselines on a frozen 900-case test split, followed by component ablations, robustness experiments, counterfactual grounding tests, and a 300-case stress split. [RESULTS_AUTOFILL]. ChatAlchemy is intended for biomedical research assistance rather than autonomous clinical decision making.

## 1. Introduction

Biomedical researchers increasingly rely on multiple online resources to answer questions about drug identity, regulatory status, clinical trials, molecular targets, genes, diseases, and compound properties. These sources are individually useful but difficult to combine reliably because the same entity may appear under multiple names, evidence may be distributed across databases, and records may differ by population, indication, date, or other contextual qualifiers.

A general-purpose language model can summarize retrieved material, but several important operations in biomedical evidence synthesis are better treated as explicit and auditable computations. Examples include canonical entity resolution, filtering, set intersection, cross-source joins, provenance retention, and determining whether two records agree, complement one another, differ only in context, or genuinely conflict.

ChatAlchemy-Live is designed around this distinction. The system uses language models where flexible language understanding is useful while representing evidence as structured records and performing reproducible evidence operations explicitly. The resulting output retains source identifiers, URLs, retrieval times, intermediate source traces, evidence relations, and claim-level support information.

The paper asks a focused question: **does combining typed planning, live biomedical database federation, entity normalization, deterministic evidence composition, contextual conflict handling, and claim verification improve correctness and grounding compared with model-centric alternatives using the same questions and, where appropriate, the same evidence or tools?**

### Contributions

1. A provenance-preserving architecture for reasoning over multiple live biomedical databases without relying on a bundled pharmaceutical knowledge corpus.
2. Explicit entity normalization and deterministic cross-source evidence operations for auditable biomedical question answering.
3. Context-aware evidence-relation modeling and claim-level verification linked to source records.
4. LiveBioEvidenceBench-v2.1, a dynamic 1,500-task-state evaluation framework with entity-disjoint public partitions and an independent live-data oracle.
5. A controlled evaluation protocol covering LLM-only, same-retrieval, unrestricted same-tools agent, component ablations, source failures, counterfactual grounding, stress testing, efficiency, and human expert evaluation.

No claim is made that ChatAlchemy is the first biomedical multi-tool agent, and the system is not evaluated as an autonomous clinical decision system.

## 2. Related Work

[RELATED_WORK_TO_BE_WRITTEN_FROM_CURRENT_PRIMARY_SOURCES]

Organize this section around: biomedical tool-using agents; retrieval-augmented biomedical reasoning; structured database/question-answering systems; provenance and grounding; dynamic/temporal benchmark design; and counterfactual grounding. Avoid unsupported priority claims.

## 3. Methods

### 3.1 System overview

ChatAlchemy-Live is a biomedical research-assistance system that federates query-time evidence from seven primary online resources: RxNorm/RxNav, DailyMed, Drugs@FDA/openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem. The application interface is a demonstration layer; the scientific evaluation targets the evidence engine and tasks for which an independent oracle can be defined.

The core execution pipeline is:

1. parse the user question into a typed query plan;
2. normalize entities into canonical source-compatible forms;
3. execute the required live source adapters;
4. convert returned records into canonical evidence-state objects;
5. apply deterministic filtering, joins, and intersections when the task requires structured composition;
6. classify relations among evidence records as agreement, complementary evidence, context difference, or conflict;
7. construct the answer while retaining source provenance;
8. verify generated claims against the available evidence objects and attach source-support identifiers.

### 3.2 Live evidence sources

RxNorm/RxNav provides canonical drug identity; DailyMed provides Structured Product Labeling records; Drugs@FDA/openFDA provides regulatory application and product records; ClinicalTrials.gov provides trial records; ChEMBL provides drug-target and mechanism evidence; Open Targets provides gene-disease-drug evidence; and PubChem provides small-molecule compound records.

Pharmaceutical knowledge is queried online at execution time. The earlier bundled TTD-style local pharmaceutical corpus is not used as the application's knowledge source.

### 3.3 Typed planning and routing

The planner maps each supported task into a typed plan specifying the required entities, source adapters, filters, and final operation. This representation makes routing independently testable. The benchmark CI validates all 1,500 frozen task states against expected route, entity, and filter behavior.

### 3.4 Canonical evidence representation

Retrieved records are transformed into canonical evidence-state objects containing a subject, predicate, value, contextual qualifiers, evidence type, source, source record identifier or URL, and retrieval time. These objects form the common representation used for deterministic composition, provenance scoring, conflict analysis, and claim verification.

### 3.5 Entity normalization

Cross-database biomedical reasoning is sensitive to aliases and identifier mismatches. ChatAlchemy therefore normalizes supported drug and biomedical entities before downstream operations. Entity-normalization performance is evaluated separately using a live RxNorm-based alias-to-generic benchmark with a no-normalization control.

### 3.6 Deterministic evidence operations

When a question requires filtering, counting, set intersection, or cross-source composition, ChatAlchemy performs the operation deterministically over structured evidence records rather than delegating the computation to unconstrained generation. This design is tested with a no-deterministic-join ablation.

### 3.7 Context-aware evidence relations

Evidence from different sources may not be strictly identical or contradictory. ChatAlchemy represents four relation classes: agreement, complementary evidence, context difference, and conflict. Context may include indication, population, study status, regulatory scope, time, or other qualifiers. Conflict-classification performance is reported only if the manually annotated evaluation set is completed.

### 3.8 Claim-level verification and provenance

Generated claims are linked to supporting evidence identifiers and classified as supported or unsupported relative to the available source records. Because a system can avoid unsupported claims by producing no claims, claim-producing rate and supported-claim rate are reported together. Provenance quality is evaluated against the independent oracle source trace.

### 3.9 Source failure handling

Source adapters record success, failure, latency, and result metadata. Controlled failure injection occurs only at the local source-adapter boundary and never modifies an upstream biomedical database. Exception and empty-result failures are tested separately for each main source.

## 4. LiveBioEvidenceBench-v2.1

### 4.1 Benchmark construction

LiveBioEvidenceBench-v2.1 contains 1,500 deterministic task states generated with seed 1729. The public partitions are development (300), test (900), and stress (300). Drug, target, gene, and condition entity pools are disjoint across public partitions.

The benchmark contains 11 structured task families spanning single-source, cross-source, gene/target/compound, and uploaded-evidence operations. A task is uniquely identified by its complete state rather than surface wording alone because uploaded-evidence cases may reuse wording with different candidate sets.

### 4.2 Dynamic independent oracle

Gold answers are not stored as a static answer corpus. An independent evaluation oracle queries the necessary live public sources and recomputes source-supported answers. The oracle bypasses ChatAlchemy's planner, final deterministic reasoning operation, conflict classifier, and claim verifier.

For the confirmatory comparison, all systems are scored against one fingerprint-matched frozen oracle snapshot so live database changes during model execution cannot create an unfair comparison.

### 4.3 Oracle outage policy

Cases for which the independent oracle is unavailable are not silently marked correct or incorrect. Oracle coverage is reported separately. Post-freeze invalid cases are excluded only with an explicit reason and are not replaced in the reported run.

## 5. Experimental Design

### 5.1 Frozen confirmatory study

The confirmatory study uses:

- method commit: `0b994c97e496d581ef3ae68bdb6503431ea1d664`;
- benchmark: `LiveBioEvidenceBench-v2.1`;
- seed: `1729`;
- primary split: test, `n=900`;
- stress split: `n=300`;
- model for model-based comparisons: `gpt-5.6-sol`;
- deterministic 10-shard execution;
- identical frozen oracle snapshot for paired primary comparisons.

No behavior-changing tuning is permitted after inspecting confirmatory test outcomes. Any such change requires a new system version and rerun.

### 5.2 Comparison systems

The planned primary comparison includes:

1. **LLM-only:** GPT-5.6 Sol receives the question without retrieved live evidence.
2. **Same-retrieval LLM:** GPT-5.6 Sol receives the evidence objects retrieved for ChatAlchemy but performs the final composition itself.
3. **Unrestricted same-tools agent:** GPT-5.6 Sol independently chooses calls to the same seven source adapters with a 40-step ceiling, without ChatAlchemy's typed planner, normalization logic, deterministic final joins, conflict classifier, or verifier.
4. **ChatAlchemy-full.**

Actual tool calls, model token usage, and latency are retained for model-based comparisons.

### 5.3 Ablations

Four pre-specified component ablations are evaluated against the same oracle state:

- without entity normalization;
- without deterministic cross-source join;
- without conflict analysis;
- without claim verification.

### 5.4 Primary and secondary outcomes

The primary endpoint is mean task score on the frozen 900-case public test split.

Co-primary reliability outcomes are oracle coverage, live-source execution success, provenance record F1, claim-producing rate, supported-claim rate conditional on produced claims, and fully-supported claim-case rate.

Secondary outcomes include task-family score, routing accuracy, entity-normalization accuracy, conflict macro-F1 if manually annotated, failure behavior, Grounded Obedience Score, Parametric Memory Intrusion Rate, median and p95 latency, API calls, evidence items, model tokens, and monetary cost.

The 300-case stress split is analyzed separately and is not pooled with the primary endpoint.

### 5.5 Counterfactual grounding

The counterfactual suite contains 120 deterministic synthetic evaluation cases covering mechanism, regulatory-status, target-relation, and trial-status reversals. Each is tested in question-only and evidence-constrained conditions. The analysis reports Grounded Obedience Score (GOS), Parametric Memory Intrusion Rate (PMIR), paired GOS gain, and paired PMIR reduction.

### 5.6 Failure-injection robustness

For each of the seven live source adapters, exception and empty-result faults are introduced locally. Injected and control conditions use matched cases and oracle states. Report score degradation, source-failure trace visibility, qualification or abstention behavior, and unsupported-claim cases.

### 5.7 Human expert evaluation

After automated outputs are frozen, 150–200 answers are sampled with stratification across task family and difficulty. Two to three independent biomedical reviewers score blinded, randomized system outputs for factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness on fixed 1–5 scales, plus a binary research-starting-point item. Inter-rater agreement is reported before adjudication.

### 5.8 Independent external holdout

A biomedical researcher who did not implement the planner independently creates approximately 200–300 private questions after method freeze using natural wording and unseen entity combinations. The holdout is fingerprinted before evaluation and is run once on the immutable frozen system without tuning based on holdout performance.

### 5.9 Temporal analysis

Temporal evaluation is optional strengthening evidence for the main submission. If later timepoints are available, the identical frozen case IDs and system version are rerun against refreshed live-source oracle states. Genuine source-state changes are separated from API or schema outages. Strong temporal-adaptation claims are omitted if later measurements are not available before submission.

## 6. Statistical Analysis

For paired continuous per-case outcomes, report the paired mean difference and 95% paired-bootstrap confidence interval using 10,000 resamples. For paired exact-correct binary outcomes, use exact McNemar testing. Apply Holm-Bonferroni correction across the pre-specified family of pairwise comparisons. Report effect sizes and confidence intervals together with p-values. When oracle coverage differs materially, include common-case analyses.

The analysis code refuses paired significance comparisons when benchmark fingerprints or recorded oracle states do not match.

## 7. Results

> All values in this section must be generated from frozen experiment artifacts. Do not manually fill numbers from console output.

### 7.1 Primary 900-case test performance

[PRIMARY_TABLE_AUTOFILL]

Report: mean task score, oracle coverage, execution success, provenance record F1, claim-producing rate, supported-claim rate, fully-supported claim-case rate, p50/p95 latency, API calls, and model tokens/cost where applicable.

### 7.2 Comparison with model-centric baselines

[BASELINE_PAIRED_STATS_AUTOFILL]

Include paired effect size, 95% bootstrap CI, exact McNemar where applicable, Holm-adjusted p-values, and common-case analysis if coverage differs.

### 7.3 Component ablations

[ABLATION_TABLE_AUTOFILL]

Describe which components contribute most strongly overall and by task family. Do not infer mechanism beyond measured effects.

### 7.4 Stress evaluation

[STRESS_TABLE_AUTOFILL]

Report the 300-case stress split independently from the primary test split.

### 7.5 Entity normalization

[ENTITY_NORMALIZATION_AUTOFILL]

### 7.6 Counterfactual grounding

[COUNTERFACTUAL_AUTOFILL]

### 7.7 Source-failure robustness

[FAILURE_INJECTION_AUTOFILL]

### 7.8 Human expert evaluation

[HUMAN_EVAL_AUTOFILL]

### 7.9 External holdout

[EXTERNAL_HOLDOUT_AUTOFILL_OR_EXPLICIT_LIMITATION]

## 8. Error Analysis

Use the deterministic failure-review sample and categorize failures into routing, normalization, retrieval, source incompleteness, deterministic composition, temporal mismatch, conflict handling, generation, verification, oracle ambiguity, or other. Report both representative cases and category frequencies. Preserve source/API failures separately from reasoning errors.

## 9. Discussion

The discussion should interpret only effects supported by the frozen results. Key questions are whether structured evidence operations improve correctness relative to free-form model composition; whether provenance and verification improve support quality; where live-source failures dominate system reasoning failures; and what trade-offs appear in latency, tool calls, token usage, and cost.

If the unrestricted same-tools GPT-5.6 agent approaches ChatAlchemy on some task families, discuss the conditions under which explicit structure remains valuable rather than forcing a universal-superiority narrative.

## 10. Limitations

The public benchmark uses structured task families and does not cover the full diversity of biomedical research questions. Public source availability and schemas may change. The live oracle itself can become unavailable on some cases. The system is evaluated as research assistance rather than a clinically validated decision-support system. Human evaluation is limited by reviewer sample size and expertise. External holdout generalization depends on the independently authored question set. Temporal adaptation should not be claimed without real later-timepoint evidence.

## 11. Conclusion

[CONCLUSION_TO_BE_WRITTEN_AFTER_RESULTS]

The final conclusion must remain proportional to the empirical findings and must not make clinical-safety, treatment-efficacy, or unsupported priority claims.

## Reproducibility statement

Every final table and numerical claim must trace to raw per-case experiment artifacts containing the exact method commit, benchmark fingerprint, model identifier, seed, split, oracle snapshot hash, timestamps, predictions, source records, and traces. Final tables and figures are generated programmatically rather than manually transcribed.
