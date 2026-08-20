# ChatAlchemy Production Readiness

Status: productization branch in validation

Branch: `agent/chatalchemy-production-ready`

The frozen publication method remains separate at `paper-v1-freeze-2026-08-19` / `0b994c97e496d581ef3ae68bdb6503431ea1d664`. Product changes must not silently change the confirmatory paper method or its benchmark results.

## Product definition

ChatAlchemy is an evidence-first biomedical research workspace. It is designed to turn natural-language research questions and user-provided datasets/documents into auditable workflows over live biomedical sources.

It is not a diagnostic, prescribing, or clinical decision-support system.

## Core application capabilities

- Research chat with one backend planner for typed evidence operations and general model synthesis.
- Live query-time evidence from:
  - RxNorm/RxNav
  - DailyMed
  - Drugs@FDA/openFDA
  - ClinicalTrials.gov
  - ChEMBL
  - Open Targets
  - PubChem
- Entity normalization before selected cross-source workflows.
- Deterministic cross-source joins/intersections.
- Claim-level evidence support verification.
- Context-aware evidence-relation/conflict analysis.
- Per-source execution traces including failures and latency.
- Source record links and retrieval timestamps.
- Exportable JSON evidence reports.
- CSV/XLS/XLSX data analysis.
- Candidate-drug list × live-source joins.
- PDF/TXT document analysis.
- Gene/disease extraction, live evidence analysis, enrichment, and gene–disease–drug networks.
- Document-analysis → research-chat continuation.
- XLSX result export and network PNG export.
- Local saved research sessions and local dataset persistence.
- Light/dark responsive interface.

## Product architecture

### Research workspace

The product uses one coherent workspace with three views:

1. **Workspace** — task-oriented entry points and system state.
2. **Research chat** — natural-language interface to typed live evidence workflows and model synthesis.
3. **Document lab** — uploaded literature → extracted entities → live evidence → network → research chat.

The UI should never require a user to understand which backend endpoint to choose. Non-local research questions pass through the same backend planner.

### Evidence-first result model

Evidence-backed responses expose:

- routed operation;
- supported claim count;
- evidence records;
- source links and record IDs;
- retrieval timestamps;
- source execution traces;
- source failures;
- evidence relations/conflicts;
- exportable evidence JSON.

General model synthesis is visually distinguished from live evidence-backed answers.

## Data and privacy boundaries

- OpenAI credentials are server-side only.
- No bundled pharmaceutical knowledge base is used for pharmaceutical claims.
- CSV data is parsed in the browser.
- Excel files are parsed by the backend and returned to the browser; workspace rows are then stored in browser IndexedDB.
- Saved chats are stored locally in the browser.
- PDF/TXT document bytes are processed by the backend. Extracted document text can be sent to the configured server-side model for research synthesis.
- The interface explicitly warns users not to upload protected health information.
- API responses are configured `Cache-Control: no-store`.

## Application security controls implemented in code

- `OPENAI_API_KEY` never sent to browser code.
- Upload size bounds:
  - tabular files: 15 MB;
  - documents: 25 MB.
- Public JSON request bounds for questions, conversations, user evidence, titles, document text, and biomedical analysis payloads.
- Source clients have timeouts, retries, and retry handling for transient 429/5xx responses.
- Frontend requests use explicit timeouts and fail visibly rather than silently substituting unsupported biomedical answers.
- Security headers configured in `vercel.json`:
  - Content-Security-Policy;
  - X-Content-Type-Options;
  - X-Frame-Options;
  - Referrer-Policy;
  - Permissions-Policy;
  - Cross-Origin-Opener-Policy.

## Platform controls required before public launch

These are deployment/account controls rather than application-method changes.

- [ ] Confirm `OPENAI_API_KEY` and `OPENAI_MODEL` are configured for Production and Preview.
- [ ] Set a Vercel Spend Management budget/alert appropriate for expected public traffic.
- [ ] Enable platform-level abuse/rate controls for `/api/query`, `/api/chat`, `/api/title`, and biomedical model-backed routes when supported by the active Vercel plan.
- [ ] Enable production observability/log review and define an error-response process.
- [ ] Confirm custom-domain/DNS/HTTPS configuration if a custom domain is used.
- [ ] Confirm production environment contains no development-only secrets or browser-exposed provider keys.

## Validation gates before promotion

### Software

- [ ] Backend unit/mocked tests green.
- [ ] Planner regression tests green, including natural disease→gene phrasing.
- [ ] Strict TypeScript check green.
- [ ] Production frontend build green.
- [ ] Production dependency audit green.
- [ ] Live source contract tests green.
- [ ] Model credential smoke green with configured production model.

### Preview end-to-end

Run these against the exact deployment candidate:

1. `/api/health` reports healthy system and configured model.
2. General model synthesis works.
3. `What genes are associated with non-small-cell lung cancer?` routes to disease→gene evidence rather than treating grammatical words as gene symbols.
4. RxNorm identity query returns provenance.
5. DailyMed label query returns evidence table.
6. FDA approval query returns evidence table.
7. ClinicalTrials.gov query handles phase/status/disease filters.
8. ChEMBL target query works.
9. Cross-source target/FDA/trial query works.
10. PubChem compound query works.
11. CSV upload, filtering, table, chart, and clearing work.
12. Excel upload works.
13. Candidate drug list can be combined with live evidence.
14. PDF/TXT upload → extraction → evidence analysis → network works.
15. Continue from Document Lab into Research Chat works.
16. Evidence drawer shows links/traces/claim verification.
17. Evidence JSON export contains route, claims, evidence, traces, conflicts, warnings, and timestamps.
18. Dark mode and mobile layout remain usable.
19. No browser console error or secret exposure.
20. Source failure is surfaced as a warning/failure trace rather than an invented result.

### Deployment

- [ ] Preview candidate is immutable and recorded by deployment ID/commit SHA.
- [ ] Promote the tested preview artifact rather than rebuilding different code for production when possible.
- [ ] Verify production `/api/health` after promotion.
- [ ] Verify production smoke queries.
- [ ] Keep the prior production deployment available for immediate rollback.

## Research/product alignment

The research contribution and application should reinforce each other:

- **Research contribution:** structured live evidence state, normalized deterministic composition, failure-aware provenance, conflict handling, and claim verification under changing biomedical APIs.
- **Product value:** researchers can inspect and export the evidence path instead of receiving an opaque generated answer.

The product should not compete primarily on the number of available tools. New sources/features should be added only when they improve a real research workflow or the evaluation story.

## Features deliberately not required for the first production research release

These can be added when there is a demonstrated need:

- user accounts and cloud-synchronized projects;
- organization/workspace permissions;
- shared team projects;
- server-side long-term document storage;
- billing/subscriptions;
- autonomous long-running experimentation;
- clinical decision support.

Adding these too early would increase privacy, security, and operational burden without strengthening the core research claim.

## High-value next features after first release

1. **Evidence report export** — implemented as JSON in the productization branch; later add a manuscript-friendly PDF/Markdown report if useful.
2. **Two-entity comparison workspace** — compare drugs, targets, or diseases against the same selected sources and filters.
3. **Source freshness panel** — summarize retrieval timestamps and failed/unavailable sources across a research session.
4. **Literature retrieval connector** — PubMed/Europe PMC only if live literature search becomes part of the formal research question; uploaded-paper analysis already covers document-grounded exploration.
5. **Shareable immutable research session** — only after deciding how to handle authentication, privacy, and persistent server storage.

## Launch definition

For the first public research release, **production-ready** means:

- all required application features above are present;
- no provider secret is exposed client-side;
- typed evidence and general model synthesis are clearly distinguished;
- evidence-backed results are auditable and exportable;
- failures are visible;
- request/file sizes are bounded;
- security headers are active;
- Preview end-to-end validation passes;
- platform spend/abuse controls are configured;
- the exact tested preview artifact is promoted with a rollback target available.

It does **not** mean the system has clinical validation. The application remains a biomedical research and evidence-exploration tool.
