# LiveBioEvidenceBench

LiveBioEvidenceBench is an executable, time-aware benchmark for ChatAlchemy. Benchmark cases do not store permanent factual answers. Each case stores a question, structured parameters, required source family, and expected operation. At evaluation time an independent `LiveOracle` executes the authoritative source adapters directly, while ChatAlchemy executes the same question through its planner/reasoning stack.

## Generate the 1,500-case publication benchmark

```bash
PYTHONPATH=. python scripts/generate_livebiobench.py --n 1500 --seed 1729 --out benchmark/livebiobench.json
```

## Run a live smoke evaluation

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py --n 24 --seed 1729 --out benchmark/results-smoke.json
```

## Run publication scale

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py --full --seed 1729 --out benchmark/results-full.json
```

Every run stores the independent oracle output, agent output, source record identifiers, retrieval times, and a SHA-256 hash of the oracle source snapshot. This allows temporal drift experiments to compare the same benchmark at later dates without pretending that a stale answer remains ground truth.
