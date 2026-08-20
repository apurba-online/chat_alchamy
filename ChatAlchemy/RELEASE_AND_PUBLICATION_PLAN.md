# ChatAlchemy Publication + Production Execution Plan

Status: active release-candidate hardening

This plan keeps the scientific method and the public product aligned without allowing product fixes to silently rewrite confirmatory results.

## Non-negotiable release rules

1. No confirmatory paper result is reported from code that is not tied to an immutable Git commit.
2. No source outage or GraphQL/API failure is allowed to masquerade as a valid zero-result finding.
3. Product UI features are not presented as scientific novelty.
4. Model synthesis is distinguished from structured live-evidence results.
5. The product remains research-use-only and is not described as clinical decision support.
6. Final numerical paper claims come only from saved machine-generated artifacts.
7. Production is promoted only from the exact preview candidate that passed end-to-end validation.

## Track A: Publication readiness

### A0. Pre-freeze correctness pass

Required before creating Publication Freeze v2:

- [x] Preserve historical Freeze v1 (`0b994c97e496d581ef3ae68bdb6503431ea1d664`) for auditability.
- [x] Fix natural-language disease→gene routing in the product candidate.
- [x] Fix Open Targets disease resolution for punctuation/hyphen variants.
- [x] Treat GraphQL `errors` inside HTTP 200 responses as source failures.
- [x] Use the current Open Targets association ordering contract (`score desc`).
- [x] Distinguish complete openFDA request failure from a genuine empty result.
- [x] Distinguish complete ChEMBL mechanism-service failure from a genuine empty result.
- [x] Restore the full primary publication campaign as a manual-only workflow.
- [x] Use GPT-5.6 Sol as the default confirmatory model in the primary campaign.
- [x] Pin Python dependencies used by CI/release evaluation.
- [x] Expose deployment commit/branch/environment in `/api/health`.
- [ ] Current CI completely green after the correctness pass.
- [ ] Current live source contract smoke completely green.
- [ ] Current model credential smoke green.

### A1. Create Publication Freeze v2

After A0 passes:

- [ ] Create immutable branch `paper-v2-freeze-2026-08-20` at the exact validated method commit.
- [ ] Record the full SHA in `PUBLICATION_PROTOCOL.md`, `PAPER_IMPLEMENTATION.md`, `REPRODUCIBILITY.md`, and the manuscript.
- [ ] Document that Freeze v1 was superseded before the final confirmatory campaign because software/source-contract defects were found before final paper results were locked.
- [ ] Pin confirmatory workflow checkout steps to the exact Freeze v2 SHA.
- [ ] Verify benchmark version, seed, split sizes, task signatures, and fingerprint.
- [ ] Do not tune on `test`, `stress`, or the external holdout after Freeze v2.

### A2. Automated confirmatory campaign

Run all paired comparisons against one fingerprint-matched oracle snapshot:

- [ ] Build and retain frozen direct-source oracle snapshot.
- [ ] ChatAlchemy full on public `test` (`n=900`).
- [ ] LLM-only baseline on identical cases.
- [ ] Same-retrieval LLM baseline on identical cases.
- [ ] Unrestricted same-tools LLM agent on identical cases.
- [ ] Full ablation suite: no normalization, no deterministic join, no conflict analysis, no evidence-link validator.
- [ ] Public `stress` split (`n=300`) reported separately.
- [ ] Entity-normalization evaluation.
- [ ] Controlled failure-injection evaluation.
- [ ] Counterfactual grounding evaluation.
- [ ] Save raw per-case predictions, source traces, oracle outputs, model usage, latency, configuration, timestamps, and hashes.
- [ ] Generate paper tables/statistics programmatically.

Required statistics:

- [ ] Paired mean differences and 95% paired-bootstrap confidence intervals.
- [ ] Exact McNemar tests for paired exact-correct comparisons.
- [ ] Holm-Bonferroni correction for the pre-specified comparison family.
- [ ] Effect sizes with confidence intervals.
- [ ] Common-case analysis when oracle coverage differs.
- [ ] p50/p95 latency, source latency, API calls, model tokens, and model cost.

### A3. External validity and human evidence

These cannot be fabricated or replaced by automated self-evaluation:

- [ ] Author-independent private holdout of approximately 200–300 natural biomedical questions created after Freeze v2.
- [ ] Holdout fingerprint recorded before the one-time evaluation.
- [ ] No tuning after holdout inspection.
- [ ] 150–200 blinded responses sampled for expert evaluation.
- [ ] 2–3 biomedical reviewers score independently.
- [ ] Inter-rater agreement reported before adjudication.
- [ ] If conflict classification remains a central quantitative claim, independently annotate a dedicated evidence-pair set and report macro-F1/per-class metrics.

If these data are not completed, narrow the manuscript claims instead of implying that the evaluation exists.

### A4. Claims discipline before submission

- [ ] Describe the verifier accurately as claim-to-evidence link validation unless semantic entailment validation is added and independently evaluated.
- [ ] Describe the oracle as an independently executed direct-source oracle, not as perfectly independent ground truth.
- [ ] Do not claim novelty from merely calling multiple biomedical tools/databases.
- [ ] Focus the research contribution on provenance-preserving live evidence state, deterministic composition, changing-source evaluation, failure visibility, and controlled grounding comparisons.
- [ ] Keep conflict handling as a supporting capability unless the manually annotated evaluation justifies a stronger claim.
- [ ] Explicitly state that the public benchmark is templated and does not establish unrestricted natural-language task discovery.

### A5. Manuscript completion gate

Submission is allowed only when:

- [ ] Related Work is written from current primary sources.
- [ ] Every `[...AUTOFILL]` result placeholder is replaced from frozen artifacts.
- [ ] Abstract reports only verified final values.
- [ ] Results tables map to exact artifact hashes and method SHA.
- [ ] Discussion reflects measured effects rather than intended design.
- [ ] Limitations include public-source coverage, templated language, dynamic API availability, oracle dependence, and absence of clinical validation.
- [ ] Conclusion is proportional to measured evidence.
- [ ] Reproduction commands work from a clean environment.

## Track B: Production readiness

### B0. Application correctness

- [x] Server-side provider credentials only.
- [x] Bounded request and upload sizes.
- [x] API `no-store` policy.
- [x] Security/privacy headers.
- [x] Frontend request timeouts and visible error behavior.
- [x] OpenAI access/network failures translate to a clean service-unavailable response.
- [x] Source traces preserve success/failure and latency.
- [x] Complete openFDA and ChEMBL outages no longer silently become zero results.
- [x] Open Targets GraphQL errors no longer silently become zero results.
- [x] `/api/health` exposes the deployment commit so a tester can prove which code a URL is running.
- [ ] Exact release-candidate CI green.

### B1. Exact preview candidate

- [ ] Deploy the current release candidate to Vercel Preview.
- [ ] Record deployment ID, URL, Git SHA, branch, environment, and model returned by `/api/health`.
- [ ] Do not test an older preview URL after the release candidate changes.

### B2. End-to-end production smoke matrix

Run against the exact candidate:

1. [ ] `/api/health` is healthy and reports the expected SHA/model.
2. [ ] General conversational synthesis works.
3. [ ] `What genes are associated with non-small-cell lung cancer?` returns nonzero Open Targets evidence or a visible source failure, never a false successful zero caused by an API/query error.
4. [ ] RxNorm identity lookup works with provenance.
5. [ ] DailyMed label lookup works with provenance.
6. [ ] FDA application lookup works with provenance.
7. [ ] ClinicalTrials.gov phase/status/disease filtering works.
8. [ ] ChEMBL target→drug lookup works.
9. [ ] Cross-source target + FDA + trial workflow works.
10. [ ] PubChem lookup works.
11. [ ] CSV upload/filter/table/chart/clear works.
12. [ ] Excel upload works.
13. [ ] Uploaded candidate-drug × live-evidence join works.
14. [ ] PDF/TXT extraction works.
15. [ ] Document → live evidence → network works.
16. [ ] Document Lab → Research Chat continuation works.
17. [ ] Evidence drawer exposes source records, traces, warnings, and retrieval timestamps.
18. [ ] Evidence JSON export is complete and parseable.
19. [ ] Mobile light/dark modes remain usable with no console errors.
20. [ ] Deliberate source/model failure is shown as unavailable/incomplete, not as an invented or verified zero-result answer.

### B3. Platform/account controls

These are Vercel/account settings, not code-only tasks:

- [ ] Production and Preview have the intended `OPENAI_API_KEY` and `OPENAI_MODEL`.
- [ ] Spend Management budget/alerts configured.
- [ ] Platform firewall/rate/abuse controls enabled for model-backed public API routes where supported.
- [ ] Production observability/log review enabled and an error-response owner/process defined.
- [ ] Production secrets reviewed for least exposure.
- [ ] Custom domain/DNS/HTTPS verified if used.

### B4. Promotion and rollback

- [ ] Promote the exact tested candidate rather than rebuilding different source when possible.
- [ ] Verify production `/api/health` SHA after promotion.
- [ ] Repeat the critical smoke subset in production.
- [ ] Keep the previous known-good production deployment available.
- [ ] Record rollback deployment ID and rollback procedure.

## Final release definitions

### Publication-ready

ChatAlchemy is publication-ready only when Freeze v2 is immutable, the automated confirmatory/baseline/ablation campaign is complete, external-validity evidence is either completed or explicitly narrowed, expert evaluation is complete for claims that require it, statistics are generated from frozen artifacts, and the manuscript contains no unverified numerical placeholders.

### Production-ready

ChatAlchemy is production-ready only when one exact candidate has green CI, all critical end-to-end workflows pass on that deployment, source failures cannot masquerade as verified absence, deployment/model identity is visible, platform spend/abuse/observability controls are configured, and rollback is verified.
