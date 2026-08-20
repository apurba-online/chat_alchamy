# ChatAlchemy

ChatAlchemy is an **evidence-first biomedical research workspace** for auditable reasoning over live biomedical databases. It combines a typed query planner, entity normalization, deterministic cross-source operations, claim verification, source traces, and a server-side language model for conversational synthesis when a typed evidence workflow does not apply.

ChatAlchemy does **not** maintain a bundled pharmaceutical knowledge base or expose provider credentials to the browser.

> Research use only. ChatAlchemy is not a diagnostic, prescribing, or clinical decision-support system.

## What the application does

The production research workspace has three connected modes:

1. **Workspace** — start a task such as disease→genes, target→therapies, trials, drug evidence, compound lookup, or general biomedical research.
2. **Research Chat** — run natural-language questions through one backend planner and inspect evidence, claim support, source failures, conflicts, and retrieval traces.
3. **Document Lab** — upload PDF/TXT research documents, extract explicit genes/disease context, connect them to live Open Targets evidence, visualize gene–disease–drug networks, and continue the analysis in chat.

It also supports CSV/XLS/XLSX analysis and deterministic joins between candidate drug lists and live FDA/trial/target evidence.

## Current live sources

- RxNorm / RxNav — canonical drug identity
- DailyMed — SPL label records
- Drugs@FDA through openFDA — FDA application records
- ClinicalTrials.gov API v2 — phases, statuses, conditions, interventions
- ChEMBL web services — drug-target/mechanism relationships
- Open Targets Platform — gene, disease, association, and clinical-candidate evidence
- PubChem PUG REST — compound identifiers and chemical properties

## Core method

Natural-language questions are converted into a typed `QueryPlan`. Source adapters query live APIs at request time and normalize returned records into a common `EvidenceItem` representation. ChatAlchemy then performs deterministic operations such as filtering, counting, or cross-source intersection when appropriate, assesses evidence relations/conflicts, and verifies whether final structured claims are supported by retrieved evidence.

General explanatory questions may use the configured server-side model, but the interface visually distinguishes model synthesis from evidence-backed database results.

## Research-oriented properties

- no bundled pharmaceutical corpus
- source-level routing is explicit and testable
- every evidence item can retain source, record ID, URL, qualifiers, and retrieval time
- deterministic cross-source operations are preferred over model-memory joins
- contextual differences can be separated from true conflicts
- source failures are surfaced rather than silently replaced with memorized facts
- evidence-backed responses can be exported as `ChatAlchemyEvidenceReport/v1` JSON
- live benchmark oracle contracts depend on current source APIs rather than a frozen downloaded pharmaceutical database

## Production application controls

- OpenAI/API credentials are server-side only
- bounded upload and JSON request sizes
- frontend request timeouts
- transient-source retry handling
- security/privacy response headers on Vercel
- API no-store caching policy
- explicit research-use/privacy notices
- local browser chat and dataset persistence for the public research release

See [`ChatAlchemy/PRODUCTION_READINESS.md`](ChatAlchemy/PRODUCTION_READINESS.md) for launch gates, preview validation, privacy boundaries, platform controls, and rollback requirements.

## Run locally

Backend setup and tests are documented in [`ChatAlchemy/backend/README.md`](ChatAlchemy/backend/README.md).

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

Server-side model configuration:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5.6-sol"
```

If the frontend and backend are hosted separately, set `VITE_API_URL` to the backend origin. Vercel deployments normally use same-origin `/api/*` routes.

## Publication method separation

The productization branch is not the frozen confirmatory paper method. The immutable paper method remains pinned at:

- branch: `paper-v1-freeze-2026-08-19`
- commit: `0b994c97e496d581ef3ae68bdb6503431ea1d664`
- benchmark: `LiveBioEvidenceBench-v2.1`
- seed: `1729`

Product/UI changes must not silently replace frozen confirmatory results.
