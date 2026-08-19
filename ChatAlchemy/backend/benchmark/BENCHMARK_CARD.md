# LiveBioEvidenceBench-v2 Benchmark Card

## Purpose

LiveBioEvidenceBench evaluates biomedical agents that must answer structured questions using evidence retrieved from live online biomedical databases. It is designed to measure correctness, grounding, source selection, cross-source composition, and robustness to changing source state.

## Scope

Task families include drug identity, DailyMed labels, FDA application records, clinical trials, drug-target mechanisms, Open Targets gene evidence, PubChem compound properties, cross-source intersections, and user-provided candidate lists combined with live evidence.

The benchmark is not a clinical decision-support benchmark and must not be interpreted as demonstrating clinical safety.

## Dynamic ground truth

Ground truth is computed at evaluation time by an independent live oracle. The oracle is separated from ChatAlchemy's planner, generator, conflict module, and verifier. Because source state can change, benchmark artifacts must record retrieval timestamps and oracle coverage for every run.

## Splits

- `dev`: iterative development only.
- `test`: primary frozen evaluation.
- `stress`: out-of-development entity pool and harder/less common conditions; reported separately.

Entity pools are intentionally disjoint across the three splits. Aliases map only to canonical entities within the same split.

## Leakage controls

The benchmark validator and test suite enforce:
- unique case IDs;
- deterministic generation for a fixed version/seed;
- disjoint canonical drug, target, condition, and gene pools across splits;
- split metadata on every case;
- explicit benchmark version and manifest fingerprint.

Paraphrase templates may share semantic task structure across splits. Therefore claims of linguistic generalization should not be made from this benchmark alone. The intended generalization test is entity/source composition, not unseen natural-language task discovery.

## Metrics

Primary metric: mean task score on `test`.

Structured outputs are evaluated with exact scalar match, set F1, or record-field accuracy depending on the task. Reliability metrics include supported-claim rate, oracle coverage, execution success, attribution measures, and abstention behavior. Counterfactual experiments additionally report GOS and PMIR.

## Source outages

A failed oracle call is not scored as an incorrect system answer. Oracle coverage must be reported. Comparisons should additionally report common-case results when systems were evaluated under meaningfully different source availability.

## Temporal use

For temporal evaluation, reuse identical benchmark case IDs at each time point. Do not regenerate a new benchmark seed between time points. Distinguish source outages/schema failures from genuine changes in source-supported answers.

## Limitations

- The benchmark uses templated task families rather than unrestricted biomedical questions.
- It emphasizes public structured biomedical sources and does not cover private clinical records.
- Database coverage is heterogeneous; absence of a returned record is not necessarily biological or regulatory absence.
- Live-source evaluation reduces static-answer staleness but increases dependence on source uptime and schema stability.
- The benchmark does not establish clinical utility or patient-level safety.

## Reproducibility

Default generation:

```bash
cd ChatAlchemy/backend
PYTHONPATH=. python scripts/generate_livebiobench.py --n 1500 --seed 1729 --out benchmark/livebiobench-v2.json
```

Any paper result must report benchmark version, seed, split, git SHA, run timestamps, and oracle coverage.
