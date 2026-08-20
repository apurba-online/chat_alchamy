# ChatAlchemy Reproducibility Guide

This file defines the minimum procedure for reproducing software checks and paper experiments from Publication Freeze v2.

Historical Freeze v1 (`0b994c97e496d581ef3ae68bdb6503431ea1d664`) remains archived for auditability. Final confirmatory results must use the exact Freeze v2 SHA recorded after the full validation gate passes.

## 1. Record the exact revision

Before running any paper experiment:

```bash
git rev-parse HEAD
```

Every final run must retain:

- exact Git SHA;
- benchmark version, seed, split, difficulty, and fingerprint;
- oracle snapshot hash;
- exact model identifier and prompt/configuration version;
- UTC start/end timestamps;
- per-case prediction, oracle output, source records, and source traces;
- model token usage and tool/API calls where applicable.

## 2. Backend environment

Publication runner environment:

- Python 3.12
- Linux/Ubuntu
- exact versions pinned in `backend/requirements.txt`

```bash
cd ChatAlchemy/backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pip freeze > benchmark/environment-python.txt
```

Retain `environment-python.txt` from the actual confirmatory runner even though direct dependencies are pinned, because it records transitive dependencies as resolved on the experiment date.

## 3. Frontend environment

CI uses Node.js 22.

```bash
cd ChatAlchemy
npm install
npm ls --all > backend/benchmark/environment-node.txt
npm run typecheck
npm run build
```

Retain the frontend lockfile and `environment-node.txt` in the final archive.

## 4. Publication artifact and software validation

```bash
cd ChatAlchemy/backend
PYTHONPATH=. pytest -m 'not live' -q
PYTHONPATH=. python scripts/validate_publication_artifact.py
PYTHONPATH=. pytest -m live -q
```

The live test set includes the strict natural-language regression:

```text
What genes are associated with non-small-cell lung cancer?
```

That request must route to the disease→gene Open Targets workflow and return associated target evidence under normal source availability. A GraphQL/API error must surface as source failure rather than a successful zero-result trace.

## 5. Generate and fingerprint the benchmark

```bash
cd ChatAlchemy/backend
PYTHONPATH=. python scripts/generate_livebiobench.py \
  --n 1500 \
  --seed 1729 \
  --out benchmark/livebiobench-v2.1.json \
  --manifest benchmark/livebiobench-v2.1.manifest.json
```

Expected public partition counts:

- `dev=300`
- `test=900`
- `stress=300`

Record the benchmark SHA-256 fingerprint. Do not change the seed, task families, or entity pools between systems in the confirmatory comparison.

## 6. Create the frozen direct-source oracle snapshot

The confirmatory study compares all systems against the same source state. The recommended path is the manual `ChatAlchemy Frozen Primary Campaign` workflow, which captures and merges ten direct-source oracle shards before running systems.

For manual/local execution, use `scripts/build_oracle_snapshot.py` and `scripts/merge_oracle_snapshots.py`, then retain the resulting `LiveBioOracleSnapshot/v1` file and its hash.

The oracle is an independently executed direct-source procedure, not infallible ground truth. Preserve its coverage, source records, retrieval timestamps, and failures.

## 7. Confirmatory system run

Primary split: `test`, `n=900`.

Every ChatAlchemy shard must use the same frozen oracle snapshot, for example:

```bash
PYTHONPATH=. python scripts/run_live_benchmark.py \
  --full \
  --seed 1729 \
  --split test \
  --oracle-snapshot benchmark/oracle-snapshot.json \
  --out benchmark/results/chatalchemy-test.json
```

The repository primary campaign uses deterministic ten-shard execution and validates shard/fingerprint compatibility before merging.

Run `stress` separately; never pool it into the primary test endpoint.

## 8. Model baselines

Model-based confirmatory comparisons use **GPT-5.6 Sol**.

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5.6-sol
```

Required systems:

```bash
PYTHONPATH=. python scripts/run_model_baseline.py \
  --mode llm_only \
  --model gpt-5.6-sol \
  --seed 1729 --split test \
  --oracle-snapshot benchmark/oracle-snapshot.json \
  --out benchmark/results/llm-only-test.json

PYTHONPATH=. python scripts/run_model_baseline.py \
  --mode same_retrieval_llm \
  --model gpt-5.6-sol \
  --seed 1729 --split test \
  --oracle-snapshot benchmark/oracle-snapshot.json \
  --out benchmark/results/same-retrieval-llm-test.json

PYTHONPATH=. python scripts/run_model_baseline.py \
  --mode unrestricted_tool_agent \
  --model gpt-5.6-sol \
  --seed 1729 --split test \
  --oracle-snapshot benchmark/oracle-snapshot.json \
  --out benchmark/results/unrestricted-tools-test.json
```

The unrestricted same-tools agent uses the pre-specified 40-step ceiling. Retain actual tool calls and model token usage rather than reporting only the ceiling.

## 9. Ablations

Pre-specified variants are:

- full;
- no entity normalization;
- no deterministic cross-source join;
- no evidence-relation/conflict analysis;
- no claim-to-evidence link validator.

Run all variants against the same oracle state:

```bash
PYTHONPATH=. python scripts/run_ablation.py \
  --seed 1729 --split test \
  --oracle-snapshot benchmark/oracle-snapshot.json \
  --out benchmark/results/ablations.json
```

Do not add a post-hoc ablation to the pre-specified primary hypothesis family without labeling it exploratory.

## 10. Counterfactual and failure experiments

```bash
PYTHONPATH=. python scripts/run_counterfactual.py --out benchmark/results/counterfactual.json
PYTHONPATH=. python scripts/run_failure_injection.py --out benchmark/results/failure-injection.json
```

Counterfactual evidence and fault injection operate only inside the local evaluation harness. External biomedical APIs are never modified.

Failure analysis must distinguish:

- genuine successful empty result;
- source/API failure;
- GraphQL execution error inside HTTP 200;
- reasoning/composition error;
- oracle unavailability.

## 11. Entity normalization

Run the pre-specified normalization evaluation using the repository script:

```bash
PYTHONPATH=. python scripts/evaluate_entity_normalization.py \
  --split test \
  --out benchmark/results/entity-normalization.json
```

## 12. External holdout

Create the independent holdout only **after Freeze v2**. The implementation team must not tune against holdout outcomes.

Before evaluation:

```bash
PYTHONPATH=. python scripts/freeze_external_holdout.py <private-holdout-file>
```

Record count, schema, freeze timestamp, and SHA-256 fingerprint. Evaluate the holdout once on the immutable Freeze v2 method.

## 13. Statistical comparison

Use saved per-case results, not manually copied aggregate values.

Required reporting:

- paired mean differences;
- 95% paired-bootstrap confidence intervals with 10,000 resamples;
- exact McNemar tests for paired binary exact-correct outcomes;
- Holm-Bonferroni correction over the pre-specified comparison family;
- effect sizes with confidence intervals;
- common-case analysis if oracle coverage differs materially.

Use the repository statistics/table-generation scripts. The analysis must refuse paired significance comparisons when benchmark fingerprints or oracle-state identities differ.

## 14. Human expert evaluation

Follow `backend/benchmark/EXPERT_EVALUATION.md` and `expert_eval_template.csv`.

- sample 150–200 outputs with declared stratification;
- blind system identity;
- randomize response order;
- obtain 2–3 independent biomedical reviewers;
- retain unadjudicated individual ratings;
- report inter-rater agreement before adjudication.

Do not substitute automated model ratings for the planned human evaluation without changing the study description and claims.

## 15. Evidence-relation annotation

If evidence-relation/conflict classification remains a central quantitative claim, complete the dedicated independent annotation set using `conflict_annotation_template.csv` and report macro-F1, per-class metrics, confusion counts, and inter-rater agreement.

If this annotation is not completed, treat evidence-relation labeling as a supporting product capability rather than a validated central contribution.

## 16. Temporal runs

Temporal analysis is optional strengthening evidence. At every real later time point, reuse the same benchmark fingerprint/case IDs and immutable system version while creating a new direct-source oracle snapshot.

Do not interpret an API outage as semantic temporal change.

## 17. Generate paper tables

The full manual primary campaign automatically merges shards and invokes `scripts/generate_paper_tables.py`.

Every final table must be reproducible from saved machine-generated artifacts. Do not manually enter console values into the manuscript.

## 18. Final archive

The final paper release should contain or reference:

- exact Freeze v2 Git SHA/tag;
- benchmark version, seed, manifest, and fingerprint;
- direct-source oracle snapshot and hash;
- source code and test suite;
- pinned direct dependencies and resolved Python/Node environment records;
- exact model identifiers and prompt/configuration versions;
- per-case ChatAlchemy/baseline/ablation results;
- oracle outputs, source records, and retrieval timestamps;
- statistical output files;
- entity-normalization/failure/counterfactual artifacts;
- external holdout fingerprint, without exposing private content if inappropriate;
- expert-evaluation protocol and anonymized ratings where permitted;
- manuscript table/figure generation scripts;
- production release candidate SHA/deployment metadata when the application is referenced in the paper.

Do not present a result as reproduced if only aggregate numbers are retained without the underlying per-case artifact.
