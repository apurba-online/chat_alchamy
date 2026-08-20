# ChatAlchemy Production Readiness

Status: release-candidate hardening and exact-preview validation

Branch: `agent/chatalchemy-production-ready`

ChatAlchemy is an evidence-first biomedical research workspace for auditable workflows over live public biomedical sources. It is not a diagnostic, prescribing, or clinical decision-support system.

## Release principle

A production release is not defined by a branch name. It is defined by one exact Git commit deployed to one exact preview URL, validated end-to-end, then promoted with a verified rollback target.

The `/api/health` endpoint exposes the running deployment commit, branch, environment, configured model state, and application version so testers can verify that they are not exercising an older preview.

## Core application capabilities

- Research chat with typed evidence operations plus optional general model synthesis.
- Live query-time evidence from RxNorm/RxNav, DailyMed, Drugs@FDA/openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem.
- Entity normalization for selected cross-source workflows.
- Deterministic cross-source joins/intersections.
- Claim-to-evidence link validation for structured claims.
- Evidence-relation/context/conflict analysis.
- Per-source execution traces containing success/failure, latency, result count, and error text.
- Source record links and retrieval timestamps.
- Exportable evidence JSON.
- CSV/XLS/XLSX data analysis and Excel export.
- Candidate-drug list × live-source joins.
- PDF/TXT document analysis.
- Gene/disease extraction and gene–disease–drug networks.
- Document-analysis → research-chat continuation.
- Local browser research-session persistence.
- Responsive light/dark interface.

## Data and privacy boundaries

- `OPENAI_API_KEY` is server-side only.
- No bundled pharmaceutical knowledge base is used for pharmaceutical claims.
- CSV data is parsed in the browser.
- Excel files are parsed by the backend and returned to the browser.
- Saved chats and workspace rows are stored locally in the browser for this release.
- PDF/TXT bytes are processed by the backend.
- Extracted document text can be sent to the configured server-side model when the user requests model-based research synthesis.
- The interface warns users not to upload protected health information.
- API responses use `Cache-Control: no-store`.

## Application security and reliability controls implemented

- [x] Provider credentials never sent to browser code.
- [x] Tabular upload limit: 15 MB.
- [x] Document upload limit: 25 MB.
- [x] Public JSON request-size/field bounds.
- [x] Frontend request timeouts.
- [x] Retry/backoff handling for transient source failures.
- [x] Security/privacy response headers in `vercel.json`.
- [x] API no-store policy.
- [x] Production dependency audit in CI.
- [x] Strict TypeScript build in CI.
- [x] Backend Python dependency versions pinned.
- [x] OpenAI HTTP/network failures mapped to a clean 503 model-unavailable response.
- [x] Open Targets GraphQL `errors` are treated as failures even with HTTP 200.
- [x] Open Targets association ordering follows the current API contract.
- [x] Complete openFDA fallback failure is not converted to a successful empty result.
- [x] Complete ChEMBL mechanism-service failure is not converted to a successful empty result.
- [x] Exact deployment SHA/branch/environment visible in `/api/health`.
- [x] Natural disease→gene parsing regression covered by tests.
- [x] Exact NSCLC → Open Targets disease→gene live contract included in the release gate.

## Failure semantics

A successful source request with no matching records and a failed source request are different states.

Required behavior:

- successful empty query → `ok=true`, `result_count=0`;
- source/API failure → `ok=false`, error visible in the trace/warnings;
- GraphQL HTTP 200 containing `errors` → failure, not empty success;
- a failed required source must not be presented as a verified biomedical absence.

This distinction is a production launch requirement.

## Platform/account controls required before public launch

These cannot be guaranteed by application code alone:

- [ ] Confirm `OPENAI_API_KEY` and intended `OPENAI_MODEL` are configured in both Production and Preview.
- [ ] Configure Vercel Spend Management budget/alerts appropriate for public traffic.
- [ ] Enable available firewall/rate/abuse controls for `/api/query`, `/api/chat`, `/api/title`, and model-backed biomedical routes.
- [ ] Enable production observability/log review and define who responds to recurring source/model failures.
- [ ] Confirm no development-only secret is present in the production environment.
- [ ] Verify custom domain/DNS/HTTPS if a custom domain is used.

## Software validation gate

All of the following must be green on the exact release-candidate commit:

- [ ] backend unit/mocked integration tests;
- [ ] publication/security artifact gate;
- [ ] benchmark protocol/determinism/leakage gates;
- [ ] planner regression tests;
- [ ] Open Targets GraphQL error regression;
- [ ] source failure-semantics regression;
- [ ] strict TypeScript check;
- [ ] production frontend build;
- [ ] production dependency audit;
- [ ] live source contract tests;
- [ ] strict NSCLC → disease→genes live contract;
- [ ] model credential smoke.

## Exact preview end-to-end matrix

Run against the exact candidate returned by `/api/health`:

1. [ ] `/api/health` returns healthy status and expected commit/model.
2. [ ] General conversational synthesis works.
3. [ ] `What genes are associated with non-small-cell lung cancer?` returns live associated targets (including EGFR in current Open Targets source state) or an explicit source failure, never a silent false zero caused by API/query error.
4. [ ] RxNorm identity lookup returns provenance.
5. [ ] DailyMed label lookup returns provenance.
6. [ ] FDA application lookup returns provenance.
7. [ ] ClinicalTrials.gov phase/status/disease filtering works.
8. [ ] ChEMBL target→drug lookup works.
9. [ ] Cross-source target + FDA + trial workflow works.
10. [ ] PubChem compound lookup works.
11. [ ] CSV upload/filter/table/chart/clear works.
12. [ ] Excel upload works.
13. [ ] Candidate-drug list can be combined with live evidence.
14. [ ] PDF/TXT upload and extraction works.
15. [ ] Document → live evidence → network works.
16. [ ] Continue from Document Lab into Research Chat works.
17. [ ] Evidence drawer shows links, timestamps, traces, and failures/warnings.
18. [ ] Evidence JSON export contains route, evidence, traces, warnings, relations, and timestamps.
19. [ ] Mobile light/dark layouts are usable and browser console is clean.
20. [ ] Deliberate source/model failure is surfaced as unavailable/incomplete, not as an invented or verified-zero answer.

## Deployment and rollback gate

- [ ] Preview candidate is recorded by deployment ID, URL, and Git SHA.
- [ ] Exact preview candidate passes the matrix above.
- [ ] Promote the tested candidate rather than rebuilding different source when the platform allows artifact promotion.
- [ ] Verify production `/api/health` after promotion.
- [ ] Repeat the critical production smoke subset.
- [ ] Record the prior known-good production deployment as the rollback target.
- [ ] Verify rollback procedure before announcing public availability.

## Features deliberately not required for first public research release

- user accounts and cloud-synchronized projects;
- organization/team permissions;
- shared workspaces;
- long-term server-side document storage;
- billing/subscriptions;
- autonomous long-running experimentation;
- clinical decision support.

These would add privacy/security/operational burden without being necessary to validate the core product value.

## Production-ready definition

ChatAlchemy is production-ready when the exact candidate has green CI, the full critical preview matrix passes, source failures cannot masquerade as verified absence, deployment/model identity is visible, platform spend/abuse/observability controls are configured, production smoke checks pass, and a rollback target is verified.

See `RELEASE_AND_PUBLICATION_PLAN.md` for the joint production/publication execution order.
