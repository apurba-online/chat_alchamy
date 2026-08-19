# ChatAlchemy-Live

ChatAlchemy-Live is a research prototype for provenance-grounded reasoning over **live online pharmaceutical databases**. It does not maintain a downloaded pharmaceutical database or vector index.

## Core idea

Natural-language questions are converted into a typed `QueryPlan`. Deterministic adapters query authoritative online APIs at request time, normalize returned records into a common `EvidenceItem` representation, apply exact operations such as filtering/counting/intersection, assess cross-source context and conflicts, and verify that final claims cite retrieved evidence.

### Current live sources

- RxNorm / RxNav — canonical drug identity
- DailyMed — current SPL label records
- Drugs@FDA through openFDA — FDA application records
- ClinicalTrials.gov API v2 — phases, statuses, conditions, interventions
- ChEMBL web services — drug-target/mechanism relationships

## Research-oriented properties

- no bundled drug corpus
- no persistent pharmaceutical source cache
- source-level routing is explicit and testable
- every evidence item keeps source/record/timestamp provenance
- deterministic operations are preferred over LLM arithmetic
- contextual differences are separated from true conflicts
- failed sources are surfaced rather than replaced with memorized facts
- live benchmark gold contracts depend on current APIs, not frozen downloaded records

## Run

See [`ChatAlchemy/backend/README.md`](ChatAlchemy/backend/README.md) for backend setup and tests.

Frontend:

```bash
cd ChatAlchemy
npm install
npm run dev
```

Backend:

```bash
cd ChatAlchemy/backend
pip install -r requirements.txt
uvicorn chatalchemy.app:app --reload --port 8000
```

Set `VITE_API_URL` if the backend is not running on `http://localhost:8000`.
