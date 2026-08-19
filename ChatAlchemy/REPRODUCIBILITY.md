# ChatAlchemy Reproducibility Guide

This file describes the minimum procedure for reproducing software checks and paper experiments from a frozen ChatAlchemy commit.

## 1. Record the exact revision

Before running any paper experiment, record:

```bash
git rev-parse HEAD
```

All result files should also contain the git SHA, benchmark version, seed, split, model identifier, prompt version, and UTC timestamps.

## 2. Backend environment

Recommended paper environment:

- Python 3.12
- Linux/Ubuntu runner

```bash
cd ChatAlchemy/backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pip freeze > benchmark/environment-python.txt
```

The requirements file intentionally specifies supported version ranges for deployment. For the final paper archive, retain `environment-python.txt` from the exact experimental runner so the resolved versions are reproducible.

## 3. Frontend environment

Recommended CI environment: Node.js 22.

```bash
cd ChatAlchemy
npm install
npm ls --all > backend/benchmark/environment-node.txt
npm run typecheck
npm run build
```

For the final archival release, generate and retain a fresh dependency lock from the frozen codebase rather than restoring an obsolete historical lockfile.

## 4. Publication artifact validation

```bash
cd ChatAlchemy/backend
PYTHONPATH=. pytest -m 'not live' -q
PYTHONPATH=. python scripts/validate_publication_artifact.py
```

This checks benchmark invariants, required experimental components, and browser-secret regressions.

## 5. Generate the benchmark

```bash
cd ChatAlchemy/backend
PYTHONPATH=. python scripts/generate_livebiobench.py \
  --n 1500 \
  --seed 1729 \
  --out benchmark/livebiobench-v2.1.json
```

Record the printed benchmark manifest and SHA-256 fingerprint. Do not change the benchmark seed or entity partitions between systems in a primary comparison.

## 6. Run ChatAlchemy

Use the frozen test split for the primary paper result. Development decisions must use only the development split.

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py \
  --n 1500 \
  --seed 1729 \
  --split test \
  --out benchmark/results/chatalchemy-test.json
```

Run `stress` separately; do not pool it into the primary test score.

## 7. Model baselines

Model-based baselines require a server/runner credential. Never put a model key in the browser or repository.

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=<exact-model-id>

PYTHONPATH=. python scripts/run_model_baseline.py \
  --mode llm_only \
  --n 1500 --seed 1729 --split test \
  --out benchmark/results/llm-only-test.json

PYTHONPATH=. python scripts/run_model_baseline.py \
  --mode same_retrieval_llm \
  --n 1500 --seed 1729 --split test \
  --out benchmark/results/same-retrieval-llm-test.json
```

Use the same exact model identifier and prompt version for all comparisons where the experimental question requires model parity.

## 8. Ablations

```bash
PYTHONPATH=. python scripts/run_ablation.py \
  --n 1500 --seed 1729 \
  --out benchmark/results/ablations.json
```

Pre-specified variants are defined by the script. Do not add a post-hoc ablation to the primary hypothesis family without identifying it as exploratory.

## 9. Counterfactual and failure experiments

```bash
PYTHONPATH=. python scripts/run_counterfactual.py
PYTHONPATH=. python scripts/run_failure_injection.py
```

Counterfactual evidence is injected only in the local evaluation harness. External biomedical APIs are never modified.

## 10. Temporal runs

At every scheduled timepoint, use the same benchmark version, seed, case IDs, and frozen system commit unless the paper explicitly studies a software update.

Save each run separately, for example:

```text
benchmark/results/temporal/T0.json
benchmark/results/temporal/T1.json
benchmark/results/temporal/T2.json
```

Compare them with `scripts/compare_temporal_runs.py`. Preserve source errors separately from genuine oracle-state changes.

## 11. External holdout

Create the independent holdout only after method freeze. Before evaluation, record the holdout metadata/fingerprint with:

```bash
PYTHONPATH=. python scripts/freeze_external_holdout.py <private-holdout-file>
```

The implementation team should not inspect or tune against holdout answers. Evaluate once after freeze.

## 12. Statistical comparison

Use saved per-case results. Primary comparisons must be paired on common oracle-available case IDs. Report paired bootstrap confidence intervals and exact McNemar tests where applicable, with Holm-Bonferroni correction for the pre-specified hypothesis family.

Use the repository result/statistics scripts rather than manually copying values into the manuscript.

## 13. Human evaluation

Follow `backend/benchmark/EXPERT_EVALUATION.md` and `expert_eval_template.csv`. Randomize and blind system identity before reviewers see answers. Preserve unadjudicated individual ratings for agreement analysis.

## 14. Final archive

The release used for a paper should contain or reference:

- exact git commit/tag;
- benchmark version, seed, manifest and fingerprint;
- source code and test suite;
- resolved Python and Node environment records;
- model identifiers and prompt versions;
- per-case system results;
- independent-oracle outputs and retrieval timestamps;
- statistical output files;
- temporal run artifacts;
- external holdout fingerprint (not necessarily private holdout content);
- expert-evaluation protocol and anonymized ratings where permitted;
- manuscript table/figure generation scripts.

Do not present a result as reproduced if only aggregate numbers, rather than the underlying per-case artifact, are available.
