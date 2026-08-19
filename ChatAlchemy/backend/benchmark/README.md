# LiveBioEvidenceBench

LiveBioEvidenceBench is an executable, time-aware benchmark for ChatAlchemy. Benchmark cases do not store permanent factual answers. Each case stores a question, structured parameters, required source family, and expected operation. The 1,500-case generator uses multiple paraphrases and includes both live-database tasks and uploaded-candidate × live-database joins.

At evaluation time an independent `LiveOracle` calls the authoritative public APIs directly. It intentionally does not import ChatAlchemy's source adapter classes, planner, conflict module, verifier, or answer generator. ChatAlchemy executes the natural-language question through its own reasoning stack. If an authoritative source blocks or fails during a run, the case is retained with `oracle_available=false`; oracle coverage is reported rather than silently dropping the failure.

## Generate the 1,500-case publication benchmark

```bash
PYTHONPATH=. python scripts/generate_livebiobench.py --n 1500 --seed 1729 --out benchmark/livebiobench.json
```

## Run a live smoke evaluation

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py --n 11 --seed 1729 --out benchmark/results-smoke.json
```

## Run publication scale

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py --full --seed 1729 --out benchmark/results-full.json
```

Every run stores independent oracle output, agent output, source record identifiers, retrieval times, source availability, and a stable SHA-256 hash of the oracle state. The stable hash excludes retrieval time, so repeated runs can detect actual evidence changes rather than merely different execution times.

## Compare temporal runs

```bash
PYTHONPATH=. python scripts/compare_temporal_runs.py benchmark/run-t0.json benchmark/run-t1.json --out benchmark/temporal-t0-t1.json
```

The temporal report includes changed oracle cases, temporal adaptation score, stale-prediction rate, and source availability changes.
