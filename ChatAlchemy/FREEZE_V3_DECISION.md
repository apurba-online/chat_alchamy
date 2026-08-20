# Publication Freeze v3 Decision Record

Date: 2026-08-20

## Why a new freeze is required

Historical publication versions remain immutable:

- Freeze v1: `0b994c97e496d581ef3ae68bdb6503431ea1d664`
- Freeze v2: `8e2ee8f107fa5bcd1ce4fd32fb56ac196755d5af`

Freeze v2 passed the validation available at the time, but the confirmatory paper campaign had **not** been completed. During the subsequent production/publication audit, additional general method and reliability defects were identified before final confirmatory results were locked. They were not answer-specific tuning and affect how absence, latency, source failure, or source filtering would be interpreted across many cases.

The final confirmatory study must therefore use a new immutable **Publication Freeze v3** rather than silently moving Freeze v2.

## General corrections made after Freeze v2

The v3 candidate adds or corrects:

1. openFDA distinction between its documented 404 `No matches found!` response and a real 404/API outage;
2. RxNorm failure propagation when candidate properties or related ingredient resolution are unavailable;
3. failure-aware public response semantics so source failure cannot be worded as biomedical absence;
4. source-error redaction so API keys/request secrets cannot appear in browser-visible traces;
5. direct-source oracle parity for Open Targets, openFDA, RxNorm, ChEMBL, and ClinicalTrials.gov failure/filter semantics;
6. ClinicalTrials.gov phase/status filtering before pagination/truncation, with local record revalidation;
7. bounded spreadsheet parsing and formula-safe XLSX export;
8. bounded public JSON payload content;
9. committed frontend dependency lock and exact `npm ci` release builds;
10. corrected Holm-adjusted p-value reporting;
11. corrected latency accounting that separates oracle time, system wall-clock time, and source time;
12. comparable baseline efficiency/provenance accounting;
13. expanded natural-language regressions for disease→gene, condition-only trials, and subject-first FDA questions.

These changes are considered pre-confirmatory software/method correctness corrections. No final test-set paper result is accepted from a pre-v3 method after these defects were identified.

## Freeze v3 creation gate

Create the immutable v3 branch only after the exact candidate commit has:

- green backend unit/mocked tests;
- green publication/security/dependency gate;
- green benchmark determinism/leakage/task-signature gate;
- green strict TypeScript and production frontend build;
- green production dependency audit;
- green live source contracts;
- green strict NSCLC → Open Targets disease→gene contract;
- green model-credential smoke;
- exact preview deployment verified through `/api/health`;
- critical preview smoke matrix passed with no false-zero source-failure behavior.

The v3 branch must not be moved after creation.

## Confirmatory study after v3

All primary comparisons must use:

- the exact Freeze v3 Git SHA;
- `LiveBioEvidenceBench-v2.1`, seed `1729`;
- one fingerprint-matched frozen direct-source oracle snapshot;
- public `test` (`n=900`) as the primary split;
- `stress` (`n=300`) reported separately;
- GPT-5.6 Sol for model-based confirmatory systems;
- identical frozen oracle state for ChatAlchemy-full, LLM-only, same-retrieval LLM, unrestricted same-tools agent, and ablations.

No behavior-changing correction after inspection of v3 confirmatory results may be folded into the same version. Such a change requires a new disclosed method version and rerun of affected comparisons.

## Human and external evidence

Publication-scale claims still require real data collection after the automated v3 campaign:

- approximately 200–300 independently authored private holdout questions, or explicitly narrowed external-generalization claims;
- 150–200 blinded answer evaluations by 2–3 biomedical reviewers for the planned human-usefulness claims;
- independent evidence-relation annotation only if conflict classification is retained as a central quantitative contribution.

These cannot be fabricated or marked complete merely because the evaluation infrastructure exists.
