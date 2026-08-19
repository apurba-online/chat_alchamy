# ChatAlchemy publication implementation

This branch is the publication-oriented implementation of ChatAlchemy-Live.

## Scientific focus

The system treats biomedical facts as live, typed evidence rather than a bundled pharmaceutical corpus. It supports live source federation, entity normalization, deterministic cross-source joins, contextual conflict analysis, claim verification, temporal evaluation, counterfactual grounding protocols, and reproducible statistical analysis.

## Live sources

- RxNorm/RxNav
- DailyMed
- Drugs@FDA/openFDA
- ClinicalTrials.gov API v2
- ChEMBL
- Open Targets
- PubChem
- g:Profiler for enrichment

## Security

Model credentials are server-side only. Do not create a `VITE_OPENAI_API_KEY`. The historical bundled TTD pharmaceutical CSV is intentionally not part of the research knowledge layer.

## Tests

```bash
cd ChatAlchemy
python -m pip install -r backend/requirements.txt pytest pytest-asyncio
PYTHONPATH=backend pytest -q backend/tests -m 'not live'
```

Live contract tests are opt-in:

```bash
RUN_LIVE_TESTS=1 PYTHONPATH=backend pytest -q backend/tests -m live
```

## LiveBioEvidenceBench

Generate the 1,500-case benchmark specification:

```bash
python backend/scripts/generate_benchmark.py --output /tmp/livebioevidencebench.yaml
```

The generator creates 300 single-source, 350 cross-source, 250 context/conflict, 250 user-evidence, 200 temporal, and 150 counterfactual/robustness cases. Expected answers are not stored permanently; the oracle is executed against the current live source state.

## Ablations

```bash
PYTHONPATH=backend python backend/scripts/run_ablation.py --cases backend/benchmark/live_cases.yaml --output ablation_results.json
```

Configured ablations include no normalization, no deterministic joins, no conflict analysis, and no claim verifier.

## Temporal study

```bash
PYTHONPATH=backend python backend/scripts/run_temporal_eval.py --cases /tmp/livebioevidencebench.yaml --output temporal_run.json
```

Repeat this command at predeclared timepoints. Each run stores a source-state hash, record IDs, timestamp, and system result IDs.

## Counterfactual study

```bash
python backend/scripts/run_counterfactual_eval.py --cases /tmp/livebioevidencebench.yaml --output counterfactual_protocol.json
```

Counterfactual evidence is created only in memory for evaluation. Upstream biomedical APIs are never modified.

## Statistical analysis

`backend/chatalchemy/experiments/statistics.py` provides paired bootstrap confidence intervals, exact McNemar testing, and Holm-Bonferroni correction. `metrics.py` includes set-F1, Grounded Obedience Score, and Parametric Memory Intrusion Rate helpers.

## Biological analysis

The research layer does not cluster genes by name prefixes. Gene clustering uses evidence-derived association profiles. Over-representation testing uses a hypergeometric test with Benjamini-Hochberg correction; the product integration also has a live g:Profiler adapter.

## Important status

This branch implements the research architecture and reproducibility harness. Publication-scale *results* still require running the live 1,500-case benchmark, external baselines/models, repeated temporal timepoints, and blinded expert evaluation. Those measurements must not be claimed before they are actually run.
