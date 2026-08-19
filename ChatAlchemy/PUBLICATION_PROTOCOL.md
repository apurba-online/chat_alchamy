# ChatAlchemy Publication Protocol

This is the canonical pre-specified experimental protocol for the ChatAlchemy paper. Changes that alter task definitions, benchmark partitions, primary outcomes, comparison systems, or statistical tests after test-set inspection must be versioned and disclosed as post-hoc changes.

## Scientific question

ChatAlchemy evaluates whether typed planning, live biomedical database federation, entity normalization, deterministic evidence operations, contextual conflict handling, and claim-level verification improve correctness and grounding when biomedical evidence is distributed across evolving online sources.

The product UI is a demonstration surface. Product functionality is tested end-to-end, but benchmark claims are restricted to capabilities with an independent ground-truth procedure.

## Benchmark

- Benchmark: `LiveBioEvidenceBench-v2.1`
- Default seed: `1729`
- Nominal size: `1500` task specifications
- Public partitions: `dev=300`, `test=900`, `stress=300`
- Drug, target, gene, and condition pools are entity-disjoint across public partitions.
- A benchmark item is uniquely identified by its **task state**, not only its surface question. Uploaded-data tasks may share wording while carrying different candidate evidence.
- Each generation emits a SHA-256 fingerprint and manifest.
- Gold answers are not stored in the benchmark definition. An independent oracle recomputes source-supported answers from live public APIs.
- The independent oracle must not call ChatAlchemy's planner, final reasoning operation, conflict classifier, or claim verifier.
- Raw live responses/source records may be retained as timestamped experiment artifacts but are not used as the application's pharmaceutical knowledge base.

### Development policy

Only `dev` is intended for iterative behavior tuning. The public `test` split is the primary reproducible evaluation and `stress` is reported separately. Test/stress failures may motivate general source-contract or software-correctness fixes only when the fix is not tailored to the expected answer; such fixes require a new system version and complete rerun of affected comparisons.

### Private external holdout

After architecture freeze, obtain approximately 300 independently authored questions from a biomedical researcher who did not implement the planner. The private holdout should cover the supported evidence operations without copying public benchmark templates. Before evaluation, record only its count, schema, freeze time, and SHA-256 fingerprint using `scripts/freeze_external_holdout.py`. Do not tune prompts, rules, source selection, or thresholds after holdout inspection.

### Broken-problem and oracle-outage policy

Oracle-unavailable cases are never silently converted into correct or incorrect model outcomes. Report oracle coverage separately. Persistent invalid benchmark items identified before freeze may be repaired or replaced with the change documented. A post-freeze invalid item is excluded with an explicit reason and is not replaced in the reported run.

## Oracle-state policy for paired comparisons

Live truth can change. Therefore method comparisons use one of two acceptable designs:

1. **same-iteration pairing**: the independent oracle is executed once for a case and all compared systems/ablations are scored against that result; or
2. **frozen oracle snapshot**: build a versioned `LiveBioOracleSnapshot/v1` artifact and score all compared systems against the same fingerprint-matched snapshot.

A refreshed snapshot is created only when temporal change is intentionally being measured.

## Systems compared

Minimum comparison matrix:

1. `LLM-only`: same question, no retrieved live evidence.
2. `Same-retrieval LLM`: receives the evidence objects retrieved for ChatAlchemy but performs the final composition itself instead of using ChatAlchemy's deterministic result.
3. `Unrestricted same-tools LLM agent`: the model chooses sequential calls to the same seven live source adapters without ChatAlchemy's rule planner, normalization logic, deterministic final joins, conflict classifier, or claim verifier. The agent receives a generous 40-step ceiling so difficult multi-candidate tasks are not artificially handicapped; actual calls and token usage are recorded.
4. `ChatAlchemy full`.
5. Component ablations:
   - no entity normalization;
   - no deterministic cross-source join;
   - no conflict analysis;
   - no claim verifier.

An additional external biomedical-agent baseline may be reported only when source/task coverage is sufficiently comparable. Coverage, call limits, and tool-budget differences must be described rather than hidden in one aggregate number.

The model-baseline harness evaluates ChatAlchemy-full and each model baseline on every case against the same oracle state, making the main comparisons paired by construction.

## Primary outcomes

Primary endpoint:
- mean task score on frozen public `test`.

Co-primary reliability outcomes:
- oracle coverage;
- live-source execution success;
- provenance record F1 against the independent oracle source trace;
- claim-producing rate;
- supported-claim rate conditional on cases that actually produce claims;
- fully-supported claim-case rate.

Secondary outcomes:
- set F1 / structured-record score by task family;
- routing accuracy;
- entity-normalization accuracy where annotated;
- conflict classification macro-F1 on the manually annotated conflict set;
- appropriate abstention/qualification under source failure;
- Grounded Obedience Score (GOS);
- Parametric Memory Intrusion Rate (PMIR);
- median and p95 latency;
- API/tool calls and evidence items per question;
- model input/output/total tokens per question;
- monetary cost derived from the exact model/provider pricing applicable at experiment time.

A verifier score of 1.0 on a case with zero claims must not be interpreted as perfect grounding. Claim coverage and claim support are always reported together.

`stress` is reported separately and is not pooled into the primary `test` endpoint.

## Ablation protocol

The ablation runner executes the independent oracle once per case and scores all variants against that shared result. The default set is full, no-normalization, no-deterministic-join, no-conflict, and no-verifier. Report case-level paired effects and family-level results in addition to aggregate performance.

## Source-failure robustness

Fault injection occurs only at ChatAlchemy's source-adapter boundary and never modifies an upstream API. For each tested source and fault mode (`exception` or `empty`), run an unperturbed control and injected system on the same case and oracle state. Report score degradation, failure-trace visibility, qualification/abstention, and unsupported-claim case rate.

## Counterfactual grounding

Counterfactual evidence experiments are synthetic evaluation-only tests. External biomedical APIs are never altered. The default suite contains 120 deterministic cases spanning mechanism, regulatory, target-relation, and trial-status reversals. Each case is run in paired question-only and evidence-constrained conditions. Report GOS, PMIR, paired GOS gain, and paired PMIR reduction.

## Temporal evaluation

At repeated timepoints `T0...Tk`, reuse the same benchmark fingerprint/case IDs and create a new independent oracle snapshot. For cases whose oracle-supported answer changes, report temporal adaptation accuracy. Distinguish genuine source-state changes from source outage/schema failure using source records, timestamps, and snapshot hashes. Do not change the system between timepoints unless a new system version is explicitly evaluated.

## Human expert evaluation

After automatic experiments are frozen, sample 150-200 answers stratified by task family and difficulty. Use 2-3 independent biomedical reviewers. Randomize/blind system identity. Reviewers score factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness on fixed 1-5 rubrics, plus a binary research-starting-point item. Preserve raw ratings and report inter-rater agreement before adjudication.

This is an evaluation of biomedical **research assistance**, not autonomous clinical decision making.

## Statistical analysis

For paired continuous per-case scores:
- report paired mean difference with 95% paired-bootstrap CI using 10,000 resamples.

For paired binary exact-correct outcomes:
- use exact McNemar testing.

For multiple pre-specified pairwise hypotheses:
- use Holm-Bonferroni family-wise error correction.

Report effect sizes and confidence intervals in addition to p-values. If oracle coverage differs materially, also report a common-case comparison.

## Reproducibility record

Every reported run must preserve:
- Git commit SHA;
- benchmark version, seed, fingerprint, and selected split/difficulty;
- task IDs/signatures;
- oracle mode (live or frozen snapshot) and snapshot file hash when used;
- system/ablation configuration;
- model/provider/exact model identifier and prompt version when applicable;
- result limits/retry policy;
- tool-step ceiling and actual tool-call count for agent baselines;
- model input/output/total token usage;
- UTC start/end times;
- per-case oracle outputs, source record IDs, and snapshot hashes;
- per-case predictions and traces;
- aggregate outputs generated from the raw cases.

Full benchmark runs are deterministically sharded and merged only after validating fingerprint, run configuration, shard coverage, and duplicate IDs. Final paper tables/figures must be generated from saved artifacts rather than manually transcribed.

## Freeze criteria

The architecture is frozen only when:
- offline unit/mocked integration tests pass;
- live source contract tests pass;
- benchmark generation, leakage, task-signature, and fingerprint gates pass;
- frontend strict TypeScript and production build pass;
- preview/API smoke tests pass;
- no known high-severity security issue remains;
- the public test/stress evaluation protocol and primary hypotheses are fixed.

After freeze, any behavior-changing modification creates a new experiment version and requires complete rerun of affected primary comparisons.
