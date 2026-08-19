# LiveBioEvidenceBench-v2.1 Benchmark Card

## Purpose

LiveBioEvidenceBench evaluates biomedical agents that must answer structured questions using evidence retrieved from live online biomedical databases. It measures task correctness, source routing, provenance alignment, cross-source composition, user-evidence composition, robustness to source failure, and adaptation to changing source state.

It is not a clinical decision-support benchmark and does not establish clinical safety.

## Public benchmark definition

Default configuration:

- seed: `1729`
- total task specifications: `1500`
- `dev`: `300`
- `test`: `900`
- `stress`: `300`
- independent live oracle: required

Every generated case stores task family, expected operation, required sources, difficulty, template ID, public split, primary entity metadata, parameters, and a SHA-256 **task signature**.

Uploaded-data tasks can share the same natural-language wording while carrying different candidate lists. Consequently, uniqueness is defined over the complete task state rather than surface question text alone.

## Task families

The public benchmark covers:

- RxNorm drug identity normalization;
- DailyMed SPL label records;
- Drugs@FDA/openFDA application records;
- ClinicalTrials.gov trial retrieval with structured filters;
- ChEMBL target-to-drug mechanism evidence;
- Open Targets gene/disease/drug evidence;
- PubChem small-molecule compound properties;
- multi-source target + FDA + clinical-trial intersections;
- uploaded candidate lists intersected with FDA, trial, or target evidence.

The product contains additional biomedical-analysis functionality that is tested as software behavior unless a separate independently verifiable scientific task is defined.

## Dynamic ground truth

Answers are **not** embedded in the benchmark. At evaluation time, `LiveOracle` directly queries public sources independently of ChatAlchemy's planner, final reasoning operations, conflict analysis, and claim verifier.

Each oracle result preserves source record identifiers and retrieval timestamps. Evaluation artifacts can additionally store an oracle snapshot hash. This makes source change and source failure observable rather than silently converting a live benchmark into a static downloaded pharmaceutical database.

## Public partitions and leakage controls

`dev`, `test`, and `stress` use disjoint pools for drugs, targets, genes, and conditions. Brand aliases map only to canonical drugs from the same partition. PubChem tasks use small-molecule names selected for the corresponding partition.

The validator enforces:

- deterministic generation for fixed version/seed;
- exactly 1500 task specifications at the publication configuration;
- unique case IDs;
- unique task signatures;
- 300/900/300 partition sizes;
- near-equal task-family counts within each public partition;
- allowed difficulty labels;
- semantic entity isolation across public partitions;
- reproducible SHA-256 benchmark fingerprint.

Paraphrase structures are shared across splits. Therefore this benchmark is **not** evidence of unseen natural-language task discovery. The main generalization targets are entity, source, and evidence-composition behavior. A private independently authored holdout is required for stronger external generalization claims.

## Difficulty labels

- `easy`: primarily single-source retrieval or identity/record tasks;
- `medium`: filtered retrieval, gene evidence, or user-list composition;
- `hard`: multi-source intersections and user-list trial constraints.

Difficulty is a protocol label based on operation structure, not a post-hoc label derived from observed model accuracy.

## Oracle-state fairness

Two evaluation modes are supported:

1. independent live oracle evaluated in the same iteration as the compared systems; or
2. a fingerprint-matched `LiveBioOracleSnapshot/v1` used by all systems in a paired comparison.

A new oracle snapshot is intentionally created for each temporal timepoint.

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
- provenance record F1 against the independent oracle trace;
- claim-producing rate;
- supported-claim rate conditional on claim-producing cases;
- fully-supported claim-case rate;
- latency and source-call efficiency.

A no-claim case is not treated as evidence of perfect grounding merely because no unsupported claim exists.

## Source outages and invalid items

An unavailable oracle result is not counted as system success or failure. Oracle coverage is always reported. Persistent malformed/incompatible cases can be repaired before benchmark freeze. Post-freeze exclusions must be explicitly reported with reasons and are not silently replaced.

## Temporal use

Temporal evaluation reuses identical benchmark IDs and fingerprint. Source record IDs, retrieval timestamps, and oracle hashes distinguish semantic source changes from transient outages or API schema failures.

## Limitations

- The benchmark is templated and intentionally constrained to auditable structured operations.
- It emphasizes public biomedical databases and does not cover private clinical records.
- Database coverage and terminology differ between sources; absence of a record is not necessarily biological or regulatory absence.
- Live evaluation depends on source uptime and schema stability.
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

Full evaluations may be deterministically sharded. Any paper result must report benchmark version/fingerprint, seed, selected partition/difficulty, Git SHA, oracle mode, timestamps, and oracle coverage.
