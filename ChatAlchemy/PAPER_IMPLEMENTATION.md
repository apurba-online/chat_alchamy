# ChatAlchemy-Live: Publication-Grade Implementation Record

## Scientific scope

ChatAlchemy-Live studies provenance-preserving reasoning over live biomedical databases whose records are distributed across sources, context dependent, potentially conflicting, and time varying. The application demonstrates the system; the paper evaluates the evidence engine, dynamic benchmark, grounding, robustness, and temporal behavior.

The system is designed for biomedical **research assistance**, not autonomous clinical decision making.

## Product implementation retained from the supplied ChatAlchemy project

The paper branch preserves the richer application workflow while replacing unsafe/prototype internals:

- ChatAlchemy and Biomedical Analysis landing modes;
- persistent/recent chats, rename/delete/new chat, side menu, and dark mode;
- CSV/XLS/XLSX upload with tables and charts;
- PDF/TXT biomedical-document processing;
- gene/disease exploration;
- Open Targets evidence tables;
- gene–disease–drug network visualization and export;
- PubChem compound information;
- result export and Continue-in-Chat workflow.

OpenAI/model requests are server-side. No browser API credential is required or allowed. The old bundled TTD pharmaceutical dataset is not used as the pharmaceutical knowledge source.

## Live evidence sources

The research engine uses query-time online evidence from:

1. RxNorm/RxNav — canonical drug identity;
2. DailyMed — SPL label records;
3. Drugs@FDA/openFDA — application/product records;
4. ClinicalTrials.gov — trial records;
5. ChEMBL — drug/target mechanism evidence;
6. Open Targets — gene/disease/drug evidence;
7. PubChem — small-molecule compound records.

The Biomedical Analysis extension can additionally use g:Profiler for enrichment rather than presenting the earlier prototype enrichment calculation as a new statistical method.

## Core research components

Implemented components include:

1. typed deterministic query planning for auditable/reproducible task execution;
2. canonical evidence-state objects with subject, predicate, value, qualifiers, source, record ID/URL, retrieval time, and evidence type;
3. cross-source drug/entity normalization;
4. deterministic filter/join/intersection operations rather than delegating structured computation to free-form generation;
5. explicit evidence-relation classes: agreement, complementary, context difference, and conflict;
6. claim-level support verification;
7. provenance traces linked to source records;
8. user-uploaded candidate-drug × live-source joins;
9. source retry/backoff/failure traces;
10. controlled source-failure injection for robustness evaluation;
11. server-side optional model generation while structured live tasks remain independently auditable.

## LiveBioEvidenceBench-v2.1

The publication benchmark is implemented as a **dynamic task specification**, not a static answer corpus.

Default configuration:

- 1,500 task states;
- deterministic seed `1729`;
- `dev=300`, `test=900`, `stress=300`;
- easy/medium/hard operation-level difficulty labels;
- eleven structured task families spanning single-source, cross-source, and uploaded-evidence tasks;
- task-relevant drug, target, gene, and condition entities isolated across public partitions;
- unique task signatures;
- SHA-256 benchmark fingerprint and manifest;
- independent live API oracle that bypasses ChatAlchemy's planner/final reasoning/verifier.

Uploaded-data tasks can have the same surface wording with different candidate lists; the unique experimental unit is therefore the complete task state rather than the question string alone.

CI sends all 1,500 frozen tasks through the planner and verifies the required route/entities/filters in addition to validating benchmark cardinality and leakage constraints.

## Fair live-oracle comparison

Live biomedical truth can change during an experiment. The evaluation layer therefore supports two controlled designs:

- **same-iteration pairing:** execute the independent oracle once and score every compared system against that result;
- **frozen oracle snapshot:** create a `LiveBioOracleSnapshot/v1` artifact tied to the benchmark fingerprint and reuse it across separate system/model runs.

Snapshot artifacts retain task IDs/signatures, source records, coverage, and hashes. Temporal experiments intentionally create a new snapshot at a later timepoint.

## Baselines and ablations

Implemented controlled baselines:

- `LLM-only`: question without live evidence;
- `same-retrieval LLM`: receives ChatAlchemy's retrieved evidence objects but performs final composition itself;
- `unrestricted same-tools LLM agent`: independently chooses sequential calls to the same seven live source adapters without using ChatAlchemy's rule planner, normalization, deterministic joins, conflict classifier, or verifier;
- `ChatAlchemy-full` evaluated alongside each model baseline on the same cases/oracle state.

The unrestricted same-tools agent receives a generous 40-step ceiling so it is not handicapped on multi-candidate cross-source questions. Actual tool calls, model input/output/total tokens, and latency are retained per case and reported as efficiency outcomes.

Implemented component ablations:

- no entity normalization;
- no deterministic cross-source join;
- no conflict analysis;
- no claim verifier.

Ablations execute one independent oracle result per case and share it across all variants.

Additional external biomedical-agent baselines can be added only when tool/source coverage is sufficiently comparable; harness/tool-budget differences must be explicitly reported.

## Grounding and robustness protocols

### Counterfactual grounding

The counterfactual harness contains 120 deterministic synthetic evaluation cases across:

- mechanism reversal;
- regulatory-status reversal;
- target-relation reversal;
- trial-status reversal.

Each case is run in paired question-only and evidence-constrained conditions. It reports Grounded Obedience Score (GOS), Parametric Memory Intrusion Rate (PMIR), paired GOS gain, and paired PMIR reduction. Synthetic counterfactual records never modify external biomedical APIs.

### Source failure

The fault-injection harness supports deterministic exception or empty-result faults for each main live source. Each injected run is paired with an unperturbed ChatAlchemy control on the same case and oracle state. It records performance degradation, source-failure trace visibility, qualification/abstention, and unsupported-claim cases.

## Dedicated conflict evaluation

The repository contains a blinded two-annotator + adjudication format for evidence-pair labeling and an evaluator that reports:

- macro F1;
- per-class precision/recall/F1;
- confusion counts;
- Cohen's kappa between independent annotators.

No conflict-performance claim should be made until the planned manually labeled evidence-pair set has actually been completed.

## External holdout

The repository provides a strict private-holdout schema/loader and runner. The holdout content itself is intentionally not committed.

After system freeze, approximately 300 independently authored questions should be created by a biomedical researcher who did not implement the planner. The holdout is fingerprinted before evaluation, contains operation/source metadata but no frozen time-sensitive answers, and is evaluated with a shared independent live oracle result per case.

## Temporal evaluation

The system can create/merge sharded oracle snapshots and compare repeated source states. A temporal result is scored only when the independent oracle demonstrates that the supported answer actually changed. Source outages/schema errors are tracked separately from genuine semantic drift.

## Statistical analysis

Implemented analysis utilities include:

- paired bootstrap confidence intervals for per-case score differences;
- exact McNemar test for paired binary outcomes;
- Holm-Bonferroni correction for planned multiple comparisons;
- case-ID aligned result comparison.

The primary paper endpoint is pre-specified as mean task score on the public `test` split. Reliability measures include oracle coverage, execution success, claim coverage/support, and provenance record F1. Stress-set performance is reported separately rather than silently pooled into the primary endpoint.

## Reproducible experiment execution

The manual `ChatAlchemy Paper Experiments` GitHub Actions workflow supports:

- full main benchmark;
- paired ablations;
- LLM-only baseline;
- same-retrieval LLM baseline;
- unrestricted same-tools LLM agent baseline;
- source-failure injection;
- counterfactual grounding.

The full benchmark is deterministically split into ten shards. The merger rejects benchmark-fingerprint mismatch, run-configuration mismatch, missing/unexpected shard indexes, and duplicate task IDs before producing an aggregate artifact.

Model baselines require a server-side `OPENAI_API_KEY`; no credential is stored in source code. The Responses API usage fields are recorded per model call so input, output, and total token consumption can be measured from actual runs rather than estimated afterward.

## Automated publication gates

The standard CI now checks:

- backend unit/mocked integration tests;
- the publication artifact/security gate;
- benchmark generation and manifest validation;
- 1,500 unique benchmark task states;
- exact 300/900/300 public split sizes;
- split entity isolation;
- all 1,500 benchmark questions against planner route/entity/filter expectations;
- strict frontend TypeScript checking;
- production frontend build;
- production dependency audit;
- live source contract tests;
- a live benchmark smoke drawn from the frozen publication benchmark IDs.

The publication gate also rejects browser-side OpenAI credential patterns, a committed `ChatAlchemy/.env`, and reintroduction of the old bundled TTD pharmaceutical data file.

## Human evaluation assets

A blinded expert-evaluation protocol and CSV template are included for a future 150-200 answer study with 2-3 independent biomedical reviewers. Planned dimensions are factual correctness, evidence grounding, completeness, appropriate uncertainty, scientific usefulness, and usefulness as a research starting point.

These ratings must be collected from real reviewers; they are not generated by the implementation pipeline.

## What is implemented versus what is measured

The **experimental infrastructure is implemented**. Publication-scale performance claims are **not yet complete** until the corresponding experiment artifacts exist.

Still requiring actual collection:

- frozen full public test/stress benchmark results;
- LLM-only, same-retrieval, and unrestricted same-tools agent runs using configured model credentials;
- any additional fair external biomedical-agent baseline;
- private independently authored external holdout;
- 300-500 manually annotated conflict/context evidence pairs with two raters and adjudication;
- repeated real temporal timepoints;
- execution of the 120-case counterfactual model experiment;
- 150-200 blinded expert-evaluation answers with 2-3 reviewers;
- final statistical analysis/tables/figures from the frozen artifacts.

These are empirical data-collection steps. They must not be fabricated or described as completed simply because the runner exists.
