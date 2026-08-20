# ChatAlchemy Publication Protocol

This is the canonical pre-specified experimental protocol for the ChatAlchemy paper. Any change that alters task definitions, benchmark partitions, primary outcomes, comparison systems, source semantics, or statistical tests after confirmatory test results are inspected must be versioned and disclosed as post-hoc.

## Versioning and freeze policy

Historical Freeze v1 is preserved at `0b994c97e496d581ef3ae68bdb6503431ea1d664` for auditability. Before final confirmatory results were locked, software/source-contract defects were identified in user-facing disease→gene routing, Open Targets GraphQL handling, and source-failure semantics. These defects are being corrected before the confirmatory campaign. The corrected immutable method will be recorded as **Publication Freeze v2** after the full validation gate passes.

Freeze v1 must not be silently relabeled as Freeze v2. Freeze v2 receives a new exact Git SHA and all confirmatory comparisons are rerun from that version.

## Scientific question

ChatAlchemy evaluates whether typed planning, query-time biomedical database federation, entity normalization, deterministic evidence operations, explicit failure/provenance state, contextual evidence-relation handling, and claim-to-evidence link validation improve correctness and grounding when biomedical evidence is distributed across evolving online sources.

The product UI is a demonstration surface. Scientific claims are restricted to capabilities with a defined evaluation procedure. The system is evaluated as biomedical **research assistance**, not as diagnosis, prescribing, or autonomous clinical decision support.

## Biomedical sources

The evidence engine queries seven public resources at execution time:

1. RxNorm/RxNav;
2. DailyMed;
3. Drugs@FDA through openFDA;
4. ClinicalTrials.gov API v2;
5. ChEMBL;
6. Open Targets Platform;
7. PubChem.

The application does not use a bundled pharmaceutical corpus as the source of pharmaceutical claims.

## Benchmark

- Benchmark: `LiveBioEvidenceBench-v2.1`
- Default seed: `1729`
- Nominal size: `1500` task states
- Public partitions: `dev=300`, `test=900`, `stress=300`
- Drug, target, gene, and condition pools are entity-disjoint across public partitions.
- A benchmark item is uniquely identified by its complete **task state**, not only by surface wording.
- Each generation emits a SHA-256 fingerprint and manifest.
- Gold answers are not embedded as a static answer corpus.

The public benchmark uses controlled task families and shared paraphrase structures. It is designed to measure entity/source/evidence-composition behavior, not unrestricted natural-language task discovery. Stronger language-generalization claims require the independently authored private holdout defined below.

### Development policy

Only `dev` is intended for behavior tuning. `test` is the primary confirmatory public evaluation and `stress` is reported separately. Test/stress failures may motivate a new version only when a general software/source-contract defect is demonstrated without answer-specific tuning. Any such correction requires a new frozen version and complete rerun of affected comparisons.

### Broken-problem and oracle-outage policy

An oracle-unavailable case is never silently counted as correct or incorrect. Oracle coverage is reported separately. Persistent malformed/incompatible items identified before freeze may be repaired with a documented version change. A post-freeze invalid item is excluded only with an explicit reason and is not silently replaced.

## Direct-source evaluation oracle

The evaluation uses an **independently executed direct-source oracle**. The oracle bypasses ChatAlchemy's planner, final deterministic composition path, evidence-relation classifier, and evidence-link validator, and directly queries the public source APIs required by each task.

This oracle is not described as infallible or perfectly independent ground truth. It necessarily shares public API schemas, identifiers, and some source-specific interpretation conventions with the system under evaluation. Therefore:

- source records and retrieval timestamps are retained;
- oracle coverage is reported;
- a stratified subset is manually audited before final submission;
- API/schema outages are separated from system reasoning errors;
- claims are limited to the benchmark operations that the direct-source procedure can verify.

## Oracle-state policy for paired comparisons

Live biomedical source state can change during an experiment. Paired comparisons use one of two allowed designs:

1. **same-iteration pairing**: execute the direct-source oracle once for a case and score all compared systems against that same result; or
2. **frozen oracle snapshot**: create a versioned `LiveBioOracleSnapshot/v1` artifact and score all compared systems against one fingerprint-matched snapshot.

The confirmatory campaign uses the frozen-oracle-snapshot design. A refreshed snapshot is created only for an explicitly labeled temporal analysis.

## Systems compared

The minimum confirmatory comparison matrix is:

1. **LLM-only** — GPT-5.6 Sol receives the question without retrieved live evidence.
2. **Same-retrieval LLM** — GPT-5.6 Sol receives the evidence objects retrieved for ChatAlchemy but performs the final composition itself.
3. **Unrestricted same-tools LLM agent** — GPT-5.6 Sol chooses sequential calls to the same seven source adapters without ChatAlchemy's typed planner, normalization logic, deterministic final joins, evidence-relation classifier, or evidence-link validator. The agent receives a 40-step ceiling and actual calls are reported.
4. **ChatAlchemy-full**.
5. Component ablations:
   - no entity normalization;
   - no deterministic cross-source join;
   - no evidence-relation/conflict analysis;
   - no evidence-link validator.

An external biomedical-agent baseline may be added only when tool/source/task coverage is sufficiently comparable. Coverage and tool-budget differences must be reported rather than hidden inside one aggregate score.

The exact model for confirmatory model-based comparisons is **GPT-5.6 Sol**. Changing that model after confirmatory results are inspected constitutes a new experimental version unless the change is separately labeled as an additional analysis.

## Primary and reliability outcomes

Primary endpoint:

- mean task score on the frozen public `test` split.

Co-primary reliability outcomes:

- oracle coverage;
- live-source execution success;
- provenance record F1 against the direct-source oracle trace;
- claim-producing rate;
- valid claim-to-evidence link rate conditional on produced claims;
- fully linked claim-case rate.

The current evidence-link validator checks whether a produced structured claim is linked to evidence identifiers that are present in the retrieved evidence state. It is **not** described as a general semantic entailment verifier unless a separate semantic-verification component and evaluation are added.

Secondary outcomes:

- set F1 / structured-record score by task family;
- routing accuracy;
- entity-normalization accuracy where annotated;
- evidence-relation/conflict macro-F1 only if the independently annotated set is completed;
- appropriate abstention/qualification under source failure;
- Grounded Obedience Score (GOS);
- Parametric Memory Intrusion Rate (PMIR);
- median and p95 latency;
- source latency;
- API/tool calls and evidence items per question;
- model input/output/total tokens per question;
- monetary model cost using the recorded provider pricing applicable at experiment time.

A case with zero generated claims is not treated as evidence of perfect grounding merely because no unsupported link exists. Claim production and link validity are always reported together.

`stress` is reported separately and is not pooled into the primary `test` endpoint.

## Ablation protocol

The ablation runner executes one oracle state per case and scores all variants against that shared state. Report paired case-level effects and task-family effects in addition to aggregate results.

## Source-failure robustness

Fault injection occurs only at ChatAlchemy's local source-adapter boundary and never modifies an upstream biomedical database. For each tested source and fault mode (`exception` or `empty`), run a matched control and injected system on the same case/oracle state.

Report:

- task-score degradation;
- whether the failed source is visible in the trace;
- qualification/abstention behavior;
- whether an upstream failure was incorrectly presented as a verified zero-result finding;
- unsupported or unlinked claim cases.

A core correctness requirement is that complete source/API failure must not be converted into a successful empty result.

## Counterfactual grounding

The counterfactual suite contains 120 deterministic synthetic evaluation cases spanning mechanism, regulatory-status, target-relation, and trial-status reversals. Each case is evaluated in paired question-only and evidence-constrained conditions. Report GOS, PMIR, paired GOS gain, and paired PMIR reduction.

Synthetic counterfactual records are evaluation-only and never alter external biomedical APIs.

## Evidence-relation/conflict evaluation

ChatAlchemy can label evidence pairs as agreement, complementary evidence, context difference, or conflict. This remains a supporting capability unless the dedicated independently annotated evidence-pair set is completed. A central quantitative conflict claim requires macro-F1, per-class precision/recall/F1, confusion counts, and inter-annotator agreement.

## Private external holdout

After Freeze v2, obtain approximately 200–300 independently authored questions from a biomedical researcher who did not implement the planner. The holdout should use natural wording and unseen entity combinations while staying within the declared product/evidence scope.

Before evaluation:

- record only its count/schema/freeze time and SHA-256 fingerprint;
- do not inspect it for tuning;
- do not alter prompts, rules, source selection, or thresholds based on holdout outcomes.

Evaluate the holdout once on the immutable Freeze v2 system. If the holdout is not completed, narrow external-generalization claims rather than implying it exists.

## Human expert evaluation

After automated outputs are frozen, sample 150–200 answers stratified by task family and difficulty. Use 2–3 independent biomedical reviewers. Randomize and blind system identity.

Reviewers score factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness on fixed 1–5 scales, plus a binary research-starting-point item. Preserve raw ratings and report inter-rater agreement before adjudication.

## Temporal analysis

Temporal evaluation is optional strengthening evidence. If later timepoints are available, reuse the same benchmark fingerprint/case IDs and immutable system version while creating a new direct-source oracle snapshot. Distinguish genuine source-state changes from API/schema outages. Do not make strong temporal-adaptation claims without actual later measurements.

## Statistical analysis

For paired continuous per-case outcomes:

- report paired mean difference with 95% paired-bootstrap confidence interval using 10,000 resamples.

For paired binary exact-correct outcomes:

- use exact McNemar testing.

For the pre-specified family of pairwise hypotheses:

- apply Holm-Bonferroni family-wise error correction.

Always report effect sizes and confidence intervals together with p-values. If oracle coverage differs materially, also report a common-case analysis.

## Reproducibility record

Every reported run must preserve:

- exact Git commit SHA;
- benchmark version, seed, fingerprint, split, and difficulty;
- task IDs/signatures;
- oracle snapshot hash;
- system/ablation configuration;
- model provider and exact model identifier;
- prompt/configuration version where applicable;
- result limits and retry policy;
- tool-step ceiling and actual tool-call count for agent baselines;
- model input/output/total token usage;
- UTC start/end times;
- per-case oracle outputs and source records;
- per-case predictions and source traces;
- aggregate artifacts generated programmatically from raw cases;
- exact dependency versions.

Full benchmark runs are deterministically sharded and merged only after validating fingerprint, run configuration, shard coverage, and duplicate IDs. Final paper tables and figures are generated from saved artifacts rather than manually transcribed.

## Freeze v2 criteria

Publication Freeze v2 may be created only when:

- backend unit/mocked integration tests pass;
- publication/security artifact gate passes;
- live source contract tests pass;
- benchmark generation/leakage/task-signature/fingerprint gates pass;
- strict TypeScript check passes;
- production frontend build passes;
- dependency audit passes;
- the disease→gene Open Targets regression passes;
- GraphQL 200-with-errors is verified to surface as source failure;
- complete upstream source failure is verified not to become a successful zero-result trace;
- preview/API smoke tests pass on the exact candidate;
- no known high-severity security issue remains;
- primary hypotheses, comparison systems, and statistics are fixed.

After Freeze v2, any behavior-changing modification creates a new experimental version and requires complete rerun of affected confirmatory comparisons.
