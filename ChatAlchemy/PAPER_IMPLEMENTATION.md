# ChatAlchemy-Live: Publication Implementation Record

## Scientific scope

ChatAlchemy-Live studies provenance-preserving reasoning over live biomedical databases whose records are distributed across sources, context dependent, and operationally dynamic. The product demonstrates the system; the paper evaluates the evidence engine, structured composition, provenance/failure behavior, grounding, and robustness.

The system is designed for biomedical **research assistance**, not diagnosis, prescribing, or autonomous clinical decision making.

## Version history

- Historical Freeze v1: `0b994c97e496d581ef3ae68bdb6503431ea1d664`.
- Freeze v1 is retained for auditability.
- Before final confirmatory results were locked, general software/source-contract defects were identified and corrected in the release candidate.
- Publication Freeze v2 will be created only after the complete validation gate passes.
- All final confirmatory comparisons must use Freeze v2 and one shared oracle state; no Freeze v1 results may be silently mixed with Freeze v2 results.

## Live evidence sources

The research engine queries live evidence from:

1. RxNorm/RxNav — canonical drug identity;
2. DailyMed — SPL label records;
3. Drugs@FDA/openFDA — application/product records;
4. ClinicalTrials.gov — trial records;
5. ChEMBL — target/mechanism evidence;
6. Open Targets — target/disease/drug evidence;
7. PubChem — small-molecule identifiers and properties.

The application does not use the earlier bundled TTD-style pharmaceutical dataset as its pharmaceutical knowledge source.

## Core implementation

The method contains:

1. typed query planning for supported structured evidence operations;
2. canonical evidence-state objects containing subject, predicate, value, qualifiers, source, source record identifier/URL, retrieval time, and evidence type;
3. drug/entity normalization for selected cross-source workflows;
4. deterministic filtering, joining, counting, and set intersection where the requested task is structured;
5. explicit source traces recording source, operation, success/failure, latency, result count, and error text;
6. evidence-relation labeling for agreement, complementary evidence, contextual difference, and conflict;
7. claim-to-evidence link validation for structured claims;
8. user-uploaded candidate-drug × live-source joins;
9. retry/backoff handling for transient source failures;
10. controlled local fault injection for robustness experiments;
11. optional server-side model generation for general conversational synthesis and controlled evaluation baselines.

### Important terminology boundary

The current `verify_claims` component validates that a structured claim's referenced evidence identifiers exist in the retrieved evidence state. This is **claim-to-evidence link validation**, not a general semantic entailment verifier. The paper must not describe it as proving semantic truth unless a separate semantic-verification method is implemented and evaluated.

### Failure semantics

A complete source failure must not be interpreted as a valid empty evidence set. The release-candidate hardening includes:

- Open Targets GraphQL `errors` are raised even when the transport status is HTTP 200;
- Open Targets association ordering follows the current schema contract (`score desc`);
- complete openFDA fallback failure is propagated to the trace layer rather than returned as `[]`;
- complete ChEMBL mechanism-service failure is propagated rather than returned as a successful zero;
- source traces and warnings therefore distinguish retrieval failure from genuine absence of records.

These are software-correctness/source-contract fixes and must be included in Publication Freeze v2 before confirmatory evaluation.

## LiveBioEvidenceBench-v2.1

The publication benchmark is a dynamic task specification rather than a static answer corpus.

Default configuration:

- benchmark version: `LiveBioEvidenceBench-v2.1`;
- 1,500 task states;
- deterministic seed `1729`;
- public partitions `dev=300`, `test=900`, `stress=300`;
- entity-disjoint public pools for task-relevant drugs, targets, genes, and conditions;
- eleven structured task families spanning single-source, cross-source, and uploaded-evidence operations;
- unique task signatures;
- SHA-256 benchmark fingerprint and manifest.

The benchmark's public paraphrase structures are controlled and shared across splits. It tests entity/source/evidence-composition generalization, not unrestricted natural-language task discovery. A private independently authored holdout is required for stronger language/generalization claims.

## Direct-source oracle

Gold answers are recomputed from public source APIs using an independently executed direct-source oracle that bypasses ChatAlchemy's planner, final deterministic composition path, evidence-relation classifier, and evidence-link validator.

The oracle is not treated as infallible or perfectly independent ground truth because it necessarily shares public API schemas and source conventions. Therefore source records, timestamps, oracle coverage, and snapshot hashes are retained, and a stratified subset must be manually audited before final submission.

For confirmatory comparison, all systems are scored against one fingerprint-matched `LiveBioOracleSnapshot/v1` so source changes during separate model runs cannot create an unfair comparison.

## Baselines

Implemented controlled baselines are:

- `LLM-only`: GPT-5.6 Sol receives the question without live evidence;
- `same-retrieval LLM`: GPT-5.6 Sol receives ChatAlchemy's retrieved evidence objects but performs final composition itself;
- `unrestricted same-tools LLM agent`: GPT-5.6 Sol chooses sequential calls to the same seven live source adapters without using ChatAlchemy's typed planner, normalization logic, deterministic joins, evidence-relation classifier, or evidence-link validator;
- `ChatAlchemy-full`.

The unrestricted same-tools agent receives a 40-step ceiling. Actual tool calls, latency, and model token usage are retained per case.

## Ablations

The pre-specified ablations are:

- no entity normalization;
- no deterministic cross-source join;
- no evidence-relation/conflict analysis;
- no evidence-link validator.

Ablations share the same case-level oracle state as the full system.

## Robustness experiments

### Counterfactual grounding

The counterfactual harness contains 120 deterministic synthetic cases spanning mechanism, regulatory-status, target-relation, and trial-status reversals. Each is evaluated in question-only and evidence-constrained conditions, reporting Grounded Obedience Score (GOS) and Parametric Memory Intrusion Rate (PMIR).

### Source failure

The fault-injection harness supports deterministic `exception` and `empty` failures for the main live sources. Each injected run is paired with an unperturbed control on the same case/oracle state. Primary reliability questions include whether failure is visible and whether the system incorrectly turns failure into a verified zero-result answer.

### Evidence relations/conflicts

The repository contains a two-annotator + adjudication format and evaluator for agreement/complementary/context-difference/conflict labels. No central conflict-performance claim is allowed until the planned manual annotation is completed and macro-F1/per-class metrics/inter-rater agreement are available.

## External holdout

The repository contains a strict loader/freezer/runner for a private holdout. The content itself is intentionally not committed.

After Freeze v2, approximately 200–300 questions should be independently authored by a biomedical researcher who did not implement the planner. The set is fingerprinted before one-time evaluation and must not be used for tuning.

## Human evaluation

A blinded expert-evaluation protocol and CSV template are included for a 150–200-answer study with 2–3 independent biomedical reviewers. Planned dimensions are factual correctness, evidence grounding, completeness, appropriate uncertainty, scientific usefulness, and usefulness as a research starting point.

These ratings must come from real reviewers; they are not generated by the implementation pipeline.

## Statistical implementation

Implemented utilities include:

- paired bootstrap confidence intervals;
- exact McNemar tests;
- Holm-Bonferroni correction;
- case-ID-aligned paired comparison;
- common-case analysis support;
- latency/tool/token/cost reporting from saved artifacts.

The primary endpoint is mean task score on public `test`. The `stress` split is reported separately.

## Reproducible experiment execution

Two manual-only workflows are retained:

- `ChatAlchemy Paper Experiments` for targeted experiments and diagnostics;
- `ChatAlchemy Frozen Primary Campaign` for the complete confirmatory oracle → system → baselines → ablations → paper-table pipeline.

The frozen primary campaign:

- captures one sharded live oracle snapshot;
- merges and validates that snapshot;
- evaluates ChatAlchemy and model baselines against the same snapshot;
- executes paired ablations;
- merges shards only after configuration/fingerprint checks;
- generates tables/statistics from saved artifacts.

The default confirmatory model is GPT-5.6 Sol.

## Software/release controls

The release candidate includes:

- server-side provider credentials only;
- bounded request and file sizes;
- API no-store caching;
- Vercel security/privacy headers;
- explicit model-unavailable responses;
- exact deployment commit/branch/environment in `/api/health`;
- pinned Python dependencies;
- production frontend dependency audit and strict TypeScript build;
- live source contract tests;
- disease→gene Open Targets regression coverage;
- publication artifact/security/leakage gates.

## What is implemented versus what is measured

The system and experimental infrastructure are implemented. **Publication-scale empirical claims are not complete until the required artifacts are actually collected.**

Still requiring real execution/collection after Freeze v2:

- full `test` run (`n=900`);
- full `stress` run (`n=300`);
- LLM-only baseline;
- same-retrieval LLM baseline;
- unrestricted same-tools agent baseline;
- full ablation campaign;
- entity-normalization experiment;
- failure-injection experiment;
- 120-case counterfactual model experiment;
- private independently authored holdout;
- manual evidence-relation annotation if retained as a central claim;
- 150–200-answer blinded expert evaluation;
- final statistics/tables/figures generated from frozen artifacts.

None of these may be described as completed merely because the runner exists.
