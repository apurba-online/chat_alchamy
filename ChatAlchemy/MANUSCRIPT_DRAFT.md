# ChatAlchemy-Live: Provenance-Preserving Composition of Evolving Biomedical Evidence

> Working pre-results manuscript. The historical Freeze v1 is retained for auditability, but the final confirmatory study will use Publication Freeze v2 after the corrected method passes all validation gates. Numerical Results must be inserted only from frozen machine-generated artifacts. Do not manually invent, transcribe, or interpolate unverified values.

## Abstract

Biomedical evidence is distributed across heterogeneous online resources that differ in identifiers, record structures, scope, update cadence, and contextual qualifiers. We present ChatAlchemy-Live, a biomedical research-assistance system designed around explicit evidence state rather than opaque model-only synthesis. ChatAlchemy combines typed query planning, query-time database federation, entity normalization, deterministic cross-source evidence operations, source-level failure and provenance traces, context-aware evidence-relation analysis, and claim-to-evidence link validation. We evaluate the system with LiveBioEvidenceBench-v2.1, a 1,500-task-state benchmark with entity-disjoint development, test, and stress partitions and an independently executed direct-source oracle. The confirmatory evaluation compares ChatAlchemy with GPT-5.6 Sol LLM-only, same-retrieval LLM, and unrestricted same-tools agent baselines on a frozen 900-case test split, followed by component ablations, source-failure robustness, counterfactual grounding, and a separate 300-case stress split. [RESULTS_AUTOFILL]. ChatAlchemy is intended for biomedical research assistance and evidence exploration, not autonomous clinical decision making.

## 1. Introduction

Biomedical researchers routinely combine information from drug terminology services, regulatory records, product labels, clinical-trial registries, target databases, disease-association resources, and chemical databases. These resources are individually valuable but difficult to compose reliably. The same entity can appear under multiple aliases or identifiers, records can be incomplete or temporarily unavailable, and apparently inconsistent values may reflect different indications, study states, populations, jurisdictions, or time points rather than true contradiction.

Large language models can summarize retrieved material and interact with tools, but several operations central to biomedical evidence synthesis are naturally explicit computations: canonical entity resolution, filtering, counting, set intersection, cross-source joining, provenance retention, failure detection, and checking whether a structured answer is linked to the evidence records from which it was derived. Delegating all such operations to free-form generation makes it difficult to determine whether an answer came from retrieved evidence, model memory, an incorrect tool route, or a failed source.

ChatAlchemy-Live is designed around this distinction. Flexible language understanding and optional model synthesis are used where appropriate, while supported structured evidence tasks are represented as typed plans and executed over canonical evidence objects. The resulting state retains source identifiers, URLs, retrieval times, source execution traces, warnings, evidence relations, and claim-to-evidence links.

The central research question is:

**Does explicit planning and deterministic composition of live biomedical evidence improve correctness, provenance alignment, and failure-aware grounding compared with model-centric alternatives operating on the same questions and, where applicable, the same evidence or tools?**

### Contributions

1. **A provenance-preserving live-evidence architecture** that represents multi-source biomedical records as canonical evidence state rather than relying on a bundled pharmaceutical knowledge corpus.
2. **Explicit normalization and deterministic evidence composition** for structured operations such as filtering, counting, candidate-set intersection, and multi-source joins.
3. **Failure-aware evidence execution**, in which source outages and GraphQL/API errors are represented separately from genuine successful zero-result queries.
4. **LiveBioEvidenceBench-v2.1**, a 1,500-task-state evaluation framework with entity-disjoint public partitions, task-state fingerprints, and an independently executed direct-source oracle.
5. **A controlled comparison protocol** covering LLM-only, same-retrieval LLM, unrestricted same-tools agent, component ablations, source-failure injection, counterfactual grounding, stress testing, efficiency, external holdout evaluation, and blinded expert assessment.

We do not claim that ChatAlchemy is the first biomedical tool-using or multi-agent system. The contribution studied here is the combination of explicit live evidence state, deterministic composition, provenance/failure observability, and paired evaluation under changing public source state.

## 2. Related Work

### 2.1 Biomedical and scientific tool-using agents

Recent biomedical systems demonstrate that foundation models can orchestrate large collections of specialized tools. TxAgent uses multi-step therapeutic reasoning and real-time retrieval over a toolbox of 211 tools, with evaluation on drug-reasoning and personalized-treatment tasks [1]. SciToolAgent uses a scientific tool knowledge graph to organize and execute hundreds of tools across biology, chemistry, and materials science [2]. BioMedAgent uses a self-evolving multi-agent framework to learn biomedical tool workflows and was evaluated on BioMed-AQA and an external benchmark [3]. BioResearcher organizes translational-medicine tasks into scenario-guided multi-agent playbooks spanning literature, trials, patents, and quantitative analyses [4]. These systems establish that broad tool access and agentic orchestration are already active research directions; accordingly, ChatAlchemy does not treat the number of connected tools as its principal novelty.

ChatAlchemy instead studies a narrower question: when the task requires composition of records from changing biomedical databases, what is gained by representing the retrieved information as explicit evidence state and performing selected operations deterministically rather than leaving routing, joining, and answer construction entirely to unconstrained model reasoning?

### 2.2 Evaluation harnesses and comparability

Agent results can depend strongly on the available tool registry, execution harness, context policy, and scoring implementation. BioMedArena was introduced specifically to separate these layers, providing a common toolkit spanning many biomedical benchmarks, tools, and agent harnesses [5]. This concern motivates two design choices in our study. First, the unrestricted-agent baseline receives the same seven source adapters available to ChatAlchemy. Second, paired systems are scored against the same case-level oracle state rather than against independently refreshed live answers.

### 2.3 Structured evidence composition and provenance

Retrieval-augmented generation improves access to external information, but retrieval alone does not guarantee that the final answer follows the retrieved records or that cross-source computations are reproducible. For tasks such as identity resolution, regulatory/trial filtering, and candidate-set intersection, ChatAlchemy treats the final operation as a structured computation over evidence objects. Each evidence object retains its source, record identifier or URL, contextual qualifiers, and retrieval time, while execution traces preserve source success, failure, latency, and result counts.

This design distinguishes **evidence retrieval** from **evidence composition**. The same-retrieval LLM baseline therefore receives the retrieved evidence but performs final composition with the model, providing a direct test of whether deterministic composition contributes beyond retrieval alone.

### 2.4 Grounding, failure awareness, and dynamic source state

Live biomedical systems introduce an evaluation problem that is absent from static question-answering datasets: the source itself can change or become unavailable. ChatAlchemy therefore does not embed time-sensitive gold answers in the benchmark definition. An independently executed direct-source oracle recomputes supported outputs, and paired confirmatory comparisons use one fingerprint-matched frozen oracle snapshot. Oracle-unavailable cases are reported as unavailable rather than silently scored as successes or failures.

The system also distinguishes a genuine successful empty result from source failure. This is important because HTTP transport success does not necessarily imply query success; for example, GraphQL services can return HTTP 200 together with execution errors. Controlled failure injection and explicit source traces are used to evaluate whether the system surfaces such failures instead of substituting parametric model knowledge or presenting failure as biomedical absence.

### 2.5 Position of this work

ChatAlchemy is therefore complementary to broad biomedical tool agents. It does not attempt to maximize autonomous tool breadth. The study focuses on a constrained but auditable setting in which source routing, record provenance, deterministic evidence operations, source failure, and grounding can be evaluated against a direct-source procedure. The private author-independent holdout is used to test whether behavior extends beyond the public benchmark's controlled paraphrase structures.

## 3. Methods

### 3.1 System overview

ChatAlchemy-Live federates query-time evidence from seven public online resources: RxNorm/RxNav, DailyMed, Drugs@FDA through openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem. The application interface is a demonstration and research workspace; the primary scientific evaluation targets evidence operations for which a direct-source evaluation procedure can be defined.

The structured execution pipeline is:

1. map the user question to a typed query plan;
2. identify task entities and structured filters;
3. normalize supported entities when a cross-source workflow requires canonical identity;
4. execute the required live source adapters;
5. transform returned records into canonical evidence objects;
6. perform deterministic filtering, counting, joins, or intersections when specified by the plan;
7. retain source execution traces, failures, record identifiers, URLs, qualifiers, and retrieval times;
8. assess evidence relations where applicable;
9. construct the structured answer and attach evidence identifiers supporting its claims;
10. validate that referenced evidence identifiers exist in the retrieved evidence state.

General questions that do not map to a supported structured evidence workflow may use the configured server-side language model. These model-synthesis responses are separated from structured evidence results in the application.

### 3.2 Live evidence sources

RxNorm/RxNav provides canonical drug identity. DailyMed provides Structured Product Labeling records. Drugs@FDA through openFDA provides application and product records. ClinicalTrials.gov API v2 provides trial identifiers, phases, statuses, conditions, and interventions. ChEMBL provides target and mechanism records. Open Targets provides target, disease-association, and clinical-candidate evidence. PubChem provides compound identifiers and chemical properties.

Pharmaceutical evidence is queried from these public sources at execution time. The earlier local TTD-style prototype dataset is not used as the application's pharmaceutical knowledge source.

### 3.3 Typed planning and routing

The planner maps each supported structured task to a `QueryPlan` containing intent, entities, source operations, filters, and a final operation. The supported benchmark families include drug identity, label records, FDA application records, trial retrieval with filters, target-to-drug mechanisms, Open Targets gene evidence, PubChem compound records, cross-source target/FDA/trial intersections, and uploaded candidate-list composition.

The public benchmark uses controlled paraphrase structures, so routing accuracy on that benchmark is interpreted as correctness within the declared task grammar rather than evidence of unrestricted natural-language intent discovery. Natural-language product regressions outside those templates are maintained separately, including the disease-to-gene phrasing that motivated the NSCLC routing test.

### 3.4 Canonical evidence representation

Each `EvidenceItem` contains:

- subject;
- predicate;
- value;
- contextual qualifiers;
- source;
- source record identifier;
- source URL when available;
- retrieval timestamp;
- evidence type.

Stable evidence identifiers are derived from normalized record content. These objects form the representation used for deterministic composition, provenance comparison, evidence-relation analysis, and claim-to-evidence link validation.

### 3.5 Entity normalization

Cross-database reasoning is sensitive to brand/generic aliases and identifier mismatches. ChatAlchemy uses RxNorm-based drug normalization for supported workflows before comparing candidates across sources. Entity-normalization performance is evaluated separately with a no-normalization control.

### 3.6 Deterministic evidence operations

When a task requires filtering, counting, set intersection, or cross-source composition, ChatAlchemy performs the final operation over structured evidence records rather than delegating the calculation to unconstrained generation. This component is evaluated with a no-deterministic-join ablation and with a same-retrieval LLM baseline that receives the retrieved evidence but composes the answer itself.

### 3.7 Evidence relations

Evidence records may agree, be complementary, differ under context, or conflict. ChatAlchemy currently implements rule-based evidence-relation labels using normalized values, multi-valued predicate semantics, and selected contextual qualifiers. Because this classifier is intentionally simple, conflict/evidence-relation performance is reported as a central quantitative result only if the planned independently annotated evaluation set is completed. Otherwise it is treated as a supporting product capability.

### 3.8 Claim-to-evidence link validation

For structured answers, generated `Claim` objects contain identifiers of the evidence records from which the claim was constructed. The validator checks whether the referenced identifiers are present in the retrieved evidence state. We report claim-producing rate, valid-link rate conditional on claim-producing cases, and fully linked claim-case rate.

This component should not be interpreted as a general semantic entailment or clinical-truth verifier. It validates evidence linkage, not whether arbitrary natural-language text is logically entailed by a source document.

### 3.9 Source failure handling

Every source operation records source name, operation, success/failure, latency, result count, and error information. A complete upstream failure is kept distinct from a successful request returning no matching records.

The release-candidate correctness pass additionally enforces that:

- Open Targets GraphQL `errors` are treated as failure even if the HTTP status is 200;
- Open Targets disease-association requests use the current ordering contract;
- complete openFDA fallback failure is propagated to the trace layer;
- complete ChEMBL mechanism-service failure is propagated to the trace layer.

Controlled fault injection occurs only at the local source-adapter boundary and never modifies an upstream biomedical database.

## 4. LiveBioEvidenceBench-v2.1

### 4.1 Benchmark construction

LiveBioEvidenceBench-v2.1 contains 1,500 deterministic task states generated with seed 1729. Public partitions are development (300), test (900), and stress (300). Task-relevant drug, target, gene, and condition pools are entity-disjoint across public partitions.

The benchmark contains 11 structured task families spanning single-source retrieval, cross-source composition, gene/target/compound tasks, and uploaded-evidence operations. A task is uniquely identified by its complete state rather than surface wording alone because uploaded-evidence cases can reuse wording with different candidate sets.

Each generation emits a task signature and benchmark fingerprint. The benchmark definition contains task state, not frozen time-sensitive answers.

### 4.2 Direct-source oracle

Gold outputs are recomputed by an independently executed direct-source oracle that queries the relevant public APIs without invoking ChatAlchemy's planner, final deterministic composition path, evidence-relation classifier, or evidence-link validator.

The oracle is not assumed to be infallible or perfectly independent because it necessarily shares source schemas, identifiers, and some source-specific conventions with the system. Oracle coverage, source records, timestamps, and snapshot hashes are therefore retained, and a stratified subset is manually audited before final submission.

For confirmatory system comparisons, all systems are scored against one fingerprint-matched frozen oracle snapshot so changes in live source state during separate model runs do not create an unfair comparison.

### 4.3 Oracle outage and invalid-item policy

Cases for which the direct-source oracle is unavailable are not silently marked correct or incorrect. Oracle coverage is reported separately. Post-freeze invalid cases are excluded only with an explicit reason and are not replaced in the reported confirmatory run.

### 4.4 Benchmark scope

Public paraphrase structures are shared across splits. The benchmark therefore evaluates generalization across entities, source states, filters, and evidence-composition tasks within the declared task families; it does not establish unrestricted natural-language task discovery. A private independently authored holdout is required for stronger external-generalization claims.

## 5. Experimental Design

### 5.1 Publication Freeze v2

Historical Freeze v1 (`0b994c97e496d581ef3ae68bdb6503431ea1d664`) is retained for auditability. Before final confirmatory results were locked, general software/source-contract defects were identified in natural disease-to-gene routing and failure semantics. These were corrected before the final study rather than silently accepting known defects.

The final confirmatory study will use:

- method commit: `[FREEZE_V2_SHA_AUTOFILL]`;
- benchmark: `LiveBioEvidenceBench-v2.1`;
- seed: `1729`;
- primary split: test, `n=900`;
- stress split: `n=300`;
- model for model-based comparisons: `gpt-5.6-sol`;
- deterministic 10-shard execution;
- one fingerprint-matched frozen direct-source oracle snapshot for paired primary comparisons.

Publication Freeze v2 is created only after unit, publication-artifact, frontend, live-source, Open Targets NSCLC, and model-credential gates pass. No behavior-changing tuning is permitted after confirmatory results are inspected. A subsequent behavior change requires a new method version and rerun of affected comparisons.

### 5.2 Comparison systems

The primary comparison includes:

1. **LLM-only:** GPT-5.6 Sol receives the question without retrieved live evidence.
2. **Same-retrieval LLM:** GPT-5.6 Sol receives the same evidence objects retrieved for ChatAlchemy but performs final composition itself.
3. **Unrestricted same-tools agent:** GPT-5.6 Sol independently chooses sequential calls to the same seven source adapters with a 40-step ceiling, without ChatAlchemy's typed planner, normalization logic, deterministic final joins, evidence-relation classifier, or evidence-link validator.
4. **ChatAlchemy-full.**

Actual tool calls, model input/output tokens, latency, and model errors are retained for model-based comparisons.

### 5.3 Component ablations

Four pre-specified component ablations are evaluated against the same case-level oracle state:

- without entity normalization;
- without deterministic cross-source join;
- without evidence-relation/conflict analysis;
- without claim-to-evidence link validation.

### 5.4 Primary and secondary outcomes

The primary endpoint is mean task score on the frozen 900-case public test split.

Co-primary reliability outcomes are:

- oracle coverage;
- live-source execution success;
- provenance record F1;
- claim-producing rate;
- valid evidence-link rate conditional on claim production;
- fully linked claim-case rate.

Secondary outcomes include task-family score, routing accuracy, entity-normalization accuracy, evidence-relation macro-F1 if independently annotated, failure behavior, Grounded Obedience Score, Parametric Memory Intrusion Rate, median/p95 latency, source latency, API/tool calls, evidence-item counts, model tokens, and monetary cost.

The 300-case stress split is analyzed separately and is not pooled with the primary endpoint.

### 5.5 Counterfactual grounding

The counterfactual suite contains 120 deterministic synthetic evaluation cases covering mechanism, regulatory-status, target-relation, and trial-status reversals. Each is evaluated in question-only and evidence-constrained conditions. We report Grounded Obedience Score (GOS), Parametric Memory Intrusion Rate (PMIR), paired GOS gain, and paired PMIR reduction.

### 5.6 Failure-injection robustness

For each supported live source adapter, exception and empty-result faults are introduced locally. Injected and control conditions use matched cases and the same oracle state. We report score degradation, source-failure trace visibility, qualification/abstention behavior, false-zero behavior, and unlinked/unsupported claim cases.

### 5.7 Human expert evaluation

After automated outputs are frozen, 150–200 answers are sampled with stratification across task family and system. Two to three independent biomedical reviewers score blinded, randomized outputs for factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness on fixed 1–5 scales, plus a binary research-starting-point item. Inter-rater agreement is reported before adjudication.

### 5.8 Author-independent external holdout

A biomedical researcher who did not implement the planner independently creates approximately 200–300 private questions after Publication Freeze v2 using natural wording and unseen entity combinations within the declared scope. The holdout is fingerprinted before evaluation and run once on the immutable frozen system without tuning based on holdout performance.

If this holdout is not completed before submission, external natural-language generalization claims are explicitly narrowed rather than inferred from the public benchmark.

### 5.9 Temporal analysis

Temporal evaluation is optional strengthening evidence. If later time points are available, identical case IDs and the same immutable system version are rerun against refreshed direct-source oracle states. Genuine source-state changes are separated from API/schema outages. Strong temporal-adaptation claims are omitted if no real later measurements are available.

## 6. Statistical Analysis

For paired continuous per-case outcomes, we report the paired mean difference and 95% paired-bootstrap confidence interval using 10,000 resamples. For paired exact-correct binary outcomes, we use exact McNemar testing. Holm-Bonferroni correction is applied across the pre-specified family of pairwise comparisons. Effect sizes and confidence intervals are reported with p-values. When oracle coverage differs materially, common-case analyses are included.

The analysis pipeline rejects paired significance comparisons when benchmark fingerprints or recorded oracle states do not match.

## 7. Results

> All values in this section must be generated from frozen experiment artifacts. Do not manually fill values from console output or partial runs.

### 7.1 Primary 900-case test performance

[PRIMARY_TABLE_AUTOFILL]

Report mean task score, oracle coverage, execution success, provenance record F1, claim-producing rate, valid evidence-link rate, fully linked claim-case rate, p50/p95 latency, API calls, and model tokens/cost where applicable.

### 7.2 Comparison with model-centric baselines

[BASELINE_PAIRED_STATS_AUTOFILL]

Include paired effect size, 95% bootstrap CI, exact McNemar where applicable, Holm-adjusted p-values, and common-case analysis if coverage differs.

### 7.3 Component ablations

[ABLATION_TABLE_AUTOFILL]

Describe which measured components contribute most strongly overall and by task family. Do not infer mechanisms beyond the observed effects.

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

The deterministic failure-review sample is categorized into routing, normalization, retrieval, source outage, source incompleteness, deterministic composition, temporal mismatch, evidence-relation handling, model generation, evidence-link validation, oracle ambiguity, or other. Source/API failures are reported separately from system reasoning errors. Representative examples are accompanied by category frequencies rather than selected only for anecdotal effect.

## 9. Discussion

The final Discussion will interpret only effects supported by frozen results. The central questions are whether explicit structured evidence operations improve correctness relative to free-form model composition; whether provenance and evidence-link state improve auditability; where live-source failure dominates system behavior; and what trade-offs appear in latency, API calls, model tokens, and cost.

If the unrestricted same-tools GPT-5.6 Sol agent approaches or exceeds ChatAlchemy on particular task families, that result will be discussed directly. The goal is not to force a universal-superiority narrative, but to identify the conditions under which explicit evidence structure provides measurable value.

The broader implication is that biomedical research agents can be evaluated not only by answer accuracy or tool breadth, but also by whether source state, intermediate computations, and failure modes remain inspectable and reproducible.

## 10. Limitations

The public benchmark uses controlled structured task families and does not cover the full diversity of biomedical research questions. Its paraphrase structures are shared across public splits, so it does not by itself establish open-ended natural-language generalization. Public database coverage and terminology differ, and absence of a record does not necessarily imply biological, regulatory, or clinical absence. Source APIs and schemas can change or become unavailable. The direct-source oracle shares the same underlying public resources and some source conventions with the evaluated system and is therefore not infallible ground truth. The current evidence-link validator checks provenance linkage rather than general semantic entailment. Evidence-relation/conflict logic is rule-based and should not be interpreted as validated conflict resolution without the dedicated annotation study. Human evaluation is limited by reviewer sample size and expertise. The system is evaluated as research assistance and has not undergone patient-level clinical validation. Temporal adaptation is not claimed without actual repeated-time measurements.

## 11. Conclusion

[CONCLUSION_TO_BE_WRITTEN_AFTER_RESULTS]

The final conclusion must remain proportional to the empirical findings and must not make unsupported priority, clinical-safety, diagnosis, prescribing, or treatment-efficacy claims.

## Reproducibility Statement

Every final table and numerical claim must trace to raw per-case experiment artifacts containing the exact method commit, benchmark fingerprint, model identifier, seed, split, oracle snapshot hash, timestamps, predictions, source records, traces, model usage, and configuration. Final tables and figures are generated programmatically rather than manually transcribed. Backend dependency versions are pinned, and the final release artifact must archive the frontend lockfile and exact environment information.

## References

1. Gao S, Zhu R, Kong Z, et al. **TxAgent: An AI Agent for Therapeutic Reasoning Across a Universe of Tools.** arXiv:2503.10970 (2025).
2. Ding K, Yu J, Huang J, et al. **SciToolAgent: a knowledge-graph-driven scientific agent for multitool integration.** *Nature Computational Science*. 2025;5:962–972. doi:10.1038/s43588-025-00849-y.
3. Bu D, Sun J, Li K, et al. **Empowering AI data scientists using a multi-agent LLM framework with self-evolving capabilities for autonomous, tool-aware biomedical data analyses.** *Nature Biomedical Engineering* (2026). doi:10.1038/s41551-026-01634-6.
4. Kinas R, Krawczyk J, Powalski R, et al. **BioResearcher: Scenario-Guided Multi-Agent for Translational Medicine.** arXiv:2605.05985 (2026).
5. Wu J, Zhou H, Zeng M, et al. **BioMedArena: An Open-source Toolkit for Building and Evaluating Biomedical Deep Research Agents.** arXiv:2605.06177 (2026).
