# ChatAlchemy

ChatAlchemy is an **evidence-first biomedical research workspace** for auditable reasoning over live biomedical databases. It combines typed query planning, entity normalization, deterministic cross-source operations, provenance/failure traces, evidence-relation analysis, claim-to-evidence link validation, and optional server-side language-model synthesis for questions that do not map to a supported structured evidence workflow.

ChatAlchemy does **not** maintain a bundled pharmaceutical knowledge base and does not expose provider credentials to the browser.

> Research use only. ChatAlchemy is not a diagnostic, prescribing, or clinical decision-support system.

## What the application does

The research workspace has three connected modes:

1. **Workspace** — start tasks such as disease→genes, target→therapies, trials, drug evidence, compound lookup, or general biomedical research.
2. **Research Chat** — run natural-language questions through the backend planner and inspect evidence, source records, warnings, execution traces, and evidence relations.
3. **Document Lab** — upload PDF/TXT research documents, extract genes/disease context, connect them to live evidence, visualize gene–disease–drug networks, and continue the analysis in chat.

It also supports CSV/XLS/XLSX analysis and deterministic joins between user candidate-drug lists and live FDA/trial/target evidence.

## Current live sources

- RxNorm / RxNav — canonical drug identity
- DailyMed — SPL label records
- Drugs@FDA through openFDA — FDA application records
- ClinicalTrials.gov API v2 — phases, statuses, conditions, interventions
- ChEMBL web services — target/mechanism relationships
- Open Targets Platform — target, disease, association, and clinical-candidate evidence
- PubChem PUG REST — compound identifiers and chemical properties

## Core method

Natural-language questions that match a supported structured task are converted into a typed `QueryPlan`. Source adapters query live APIs at request time and normalize returned records into a common `EvidenceItem` representation. ChatAlchemy then performs deterministic operations such as filtering, counting, or cross-source intersection when appropriate.

Every structured evidence response can retain source, record ID/URL, retrieval time, execution status, latency, and warnings. A complete source failure is kept distinct from a genuine successful zero-result query.

General explanatory questions may use the configured server-side model. The interface distinguishes model synthesis from evidence-backed database results.

### Evidence-link validation boundary

The current structured claim validator checks that claim support IDs refer to evidence objects actually present in the retrieved evidence state. It should be interpreted as **claim-to-evidence link validation**, not as a general semantic entailment or clinical-truth verifier.

## Reliability hardening

The current release candidate includes:

- server-side OpenAI/API credentials only;
- bounded upload and JSON request sizes;
- frontend request timeouts;
- transient-source retry handling;
- Open Targets GraphQL-error detection even when HTTP status is 200;
- explicit separation of complete openFDA/ChEMBL source failure from valid empty results;
- security/privacy response headers on Vercel;
- API `Cache-Control: no-store`;
- explicit research-use/privacy notices;
- exact Vercel deployment commit/branch/environment in `/api/health`;
- pinned backend dependencies for reproducible releases;
- local browser chat and dataset persistence for the public research release.

See [`ChatAlchemy/PRODUCTION_READINESS.md`](ChatAlchemy/PRODUCTION_READINESS.md) and [`ChatAlchemy/RELEASE_AND_PUBLICATION_PLAN.md`](ChatAlchemy/RELEASE_AND_PUBLICATION_PLAN.md).

## Run locally

Backend:

```bash
cd ChatAlchemy/backend
pip install -r requirements.txt
uvicorn chatalchemy.app:app --reload --port 8000
```

Frontend:

```bash
cd ChatAlchemy
npm install
npm run dev
```

Server-side model configuration:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5.6-sol"
```

If frontend and backend are hosted separately, set `VITE_API_URL` to the backend origin. Vercel deployments normally use same-origin `/api/*` routes.

## Publication method separation

Historical publication Freeze v1 is retained at:

- branch: `paper-v1-freeze-2026-08-19`
- commit: `0b994c97e496d581ef3ae68bdb6503431ea1d664`
- benchmark: `LiveBioEvidenceBench-v2.1`
- seed: `1729`

Before final confirmatory results were locked, general software/source-contract defects were found and corrected in the release candidate. A new **Publication Freeze v2** will be created only after the full validation gate passes. Final confirmatory results must come from Freeze v2 and must not silently mix code/results from Freeze v1 or later product-only changes.

The full confirmatory campaign is retained as a **manual-only** GitHub Actions workflow so ordinary development pushes do not trigger costly publication experiments or unnecessary notification emails.
