# ChatAlchemy-Live backend

ChatAlchemy-Live performs query-time reasoning over public online pharmaceutical APIs. It intentionally keeps **no local pharmaceutical database, bulk download, or vector index**.

## Live sources

- RxNorm / RxNav: drug identity resolution
- DailyMed v2: current SPL label records
- Drugs@FDA through openFDA: FDA application records
- ClinicalTrials.gov API v2: trial phase/status/condition/intervention
- ChEMBL web services: target/mechanism-linked drug candidates

Every evidence item stores its source, source record ID, source URL, and retrieval timestamp. API responses are used only in memory for the current request.

## Run

```bash
cd ChatAlchemy/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn chatalchemy.app:app --reload --port 8000
```

## Tests

```bash
pytest -m 'not live' -q
pytest -m live -q
PYTHONPATH=. python scripts/run_live_benchmark.py
```

The live benchmark stores questions and execution metadata, not a downloaded pharmaceutical corpus.

## Research design

`Question -> typed planner -> live source routing -> source adapters -> EvidenceItem normalization -> deterministic operations -> context-aware conflict assessment -> claim verification -> provenance-grounded answer`
