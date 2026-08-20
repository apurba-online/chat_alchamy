# LiveBioEvidenceBench-v2.1 Benchmark Card

## Purpose

LiveBioEvidenceBench evaluates systems that answer structured biomedical questions using evidence retrieved from live online databases. It measures task correctness, source routing, provenance alignment, cross-source composition, user-evidence composition, source-failure behavior, and reproducibility under changing source state.

It is not a clinical decision-support benchmark and does not establish clinical safety.

## Public benchmark definition

Default configuration:

- seed: `1729`
- total task states: `1500`
- `dev`: `300`
- `test`: `900`
- `stress`: `300`
- direct-source evaluation oracle: required

Every generated case stores task family, expected operation, required sources, difficulty, template ID, public split, primary entity metadata, parameters, and a SHA-256 **task signature**.

Uploaded-data tasks can share the same natural-language wording while carrying different candidate lists. Consequently, uniqueness is defined over the complete task state rather than surface question text alone.

## Task families

The public benchmark covers:

- RxNorm drug identity normalization;
- DailyMed SPL label records;
- Drugs@FDA/openFDA application records;
- ClinicalTrials.gov trial retrieval with structured filters;
- ChEMBL target-to-drug mechanism evidence;
- Open Targets gene evidence;
- PubChem small-molecule compound properties;
- multi-source target + FDA + clinical-trial intersections;
- uploaded candidate lists intersected with FDA, trial, or target evidence.

The product contains additional user-facing biomedical-analysis functionality that is tested as software behavior unless a separate independently verifiable scientific task is defined.

## Dynamic evaluation oracle

Answers are **not** embedded in the benchmark definition. At evaluation time, `LiveOracle` directly queries the required public sources and bypasses ChatAlchemy's planner, final deterministic composition path, evidence-relation classifier, and evidence-link validator.

We describe this as an **independently executed direct-source oracle**, not as infallible or perfectly independent ground truth. The oracle necessarily shares the same public APIs, identifiers, and some source-specific conventions as the evaluated system. Accordingly:

- oracle coverage is reported separately;
- source record identifiers and retrieval timestamps are retained;
- snapshot hashes are preserved for paired comparisons;
- a stratified subset of final oracle outputs should be manually audited before submission;
- API/schema outages are separated from system reasoning errors.

## Public partitions and leakage controls

`dev`, `test`, and `stress` use disjoint pools for task-relevant drugs, targets, genes, and conditions. Brand aliases map only to canonical drugs from the same partition. PubChem tasks use small-molecule names selected for the corresponding partition.

The validator enforces:

- deterministic generation for fixed version/seed;
- exactly 1,500 task states at the publication configuration;
- unique case IDs;
- unique task signatures;
- exact 300/900/300 partition sizes;
- near-equal task-family counts within each public partition;
- allowed difficulty labels;
- semantic entity isolation across public partitions;
- reproducible SHA-256 benchmark fingerprint.

Paraphrase structures are shared across public splits. Therefore this benchmark is **not** evidence of unrestricted or unseen natural-language task discovery. The main public generalization targets are entity, source, filter, and evidence-composition behavior. A private independently authored holdout is required for stronger external natural-language generalization claims.

## Difficulty labels

- `easy`: primarily single-source retrieval or identity/record tasks;
- `medium`: filtered retrieval, gene evidence, or user-list composition;
- `hard`: multi-source intersections and user-list trial constraints.

Difficulty is a protocol label based on operation structure, not a post-hoc label derived from observed model accuracy.

## Oracle-state fairness

Two evaluation modes are supported:

1. **same-iteration pairing:** the direct-source oracle is executed once for a case and all compared systems are scored against that same result; or
2. **frozen oracle snapshot:** one fingerprint-matched `LiveBioOracleSnapshot/v1` is used by all systems in a paired comparison.

The confirmatory study uses the frozen-snapshot design. A new oracle snapshot is created only when temporal change is intentionally being measured.

## Primary scoring

Depending on task family, outputs use:

- exact normalized scalar match;
- set F1;
- structured record-field accuracy.

Primary paper endpoint: mean task score on `test`.

Reliability reporting includes:

- oracle coverage;
- source execution success;
- routing accuracy;
- provenance record F1 against the direct-source oracle trace;
- claim-producing rate;
- valid claim-to-evidence link rate conditional on claim-producing cases;
- fully linked claim-case rate;
- latency and source-call efficiency.

The current structured validator checks whether a claim's referenced evidence identifiers exist in the retrieved evidence state. This is **evidence-link validation**, not general semantic entailment verification. A no-claim case is not treated as evidence of perfect grounding merely because no invalid evidence link exists.

## Source outages and false-zero protection

An unavailable oracle result is not counted as system success or failure. Oracle coverage is always reported.

For the evaluated system, a complete source failure is also distinct from a genuine successful zero-result query. Release validation therefore includes regression tests for:

- HTTP/network source failure;
- GraphQL HTTP-200 responses containing execution errors;
- natural disease→gene Open Targets retrieval for non-small-cell lung cancer;
- controlled `exception` and `empty` source-failure injection.

A failed required source must not be presented as verified biomedical absence.

## Invalid-item policy

Persistent malformed or incompatible benchmark items may be repaired before method freeze with a documented version change. Post-freeze exclusions must be explicitly reported with reasons and are not silently replaced.

## Temporal use

Temporal evaluation reuses identical benchmark IDs, task signatures, benchmark fingerprint, and system version while creating a new direct-source oracle snapshot. Source records, retrieval timestamps, and oracle hashes are used to separate semantic source changes from transient outages or schema failures.

## Limitations

- The benchmark is templated and intentionally constrained to auditable structured operations.
- Shared public paraphrase structures do not establish unrestricted natural-language generalization.
- It emphasizes public biomedical databases and does not cover private clinical records.
- Database coverage and terminology differ between sources; absence of a record is not necessarily biological, regulatory, or clinical absence.
- Live evaluation depends on source uptime and schema stability.
- The direct-source oracle is not independent of the underlying APIs and can itself fail or reflect source-specific conventions.
- Public split isolation does not replace a private author-independent holdout.
- The benchmark does not establish diagnostic, therapeutic, or patient-level clinical utility.

## Reproducibility

Generate and validate the publication benchmark:

```bash
cd ChatAlchemy/backend
PYTHONPATH=. python scripts/generate_livebiobench.py \
  --n 1500 \
  --seed 1729 \
  --out benchmark/livebiobench-v2.1.json \
  --manifest benchmark/livebiobench-v2.1.manifest.json
```

Run a frozen-ID live smoke:

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py --limit 8 --seed 1729
```

Full evaluations may be deterministically sharded. Any paper result must report benchmark version/fingerprint, seed, selected partition/difficulty, exact Git SHA, oracle mode/snapshot hash, timestamps, oracle coverage, and the saved per-case artifact from which the aggregate result was generated.
