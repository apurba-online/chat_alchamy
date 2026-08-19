# ChatAlchemy-Live paper implementation

## Scientific scope

ChatAlchemy-Live studies provenance-preserving reasoning over live biomedical databases whose records can be distributed, context dependent, conflicting, or time-varying. The website is the demonstration layer; the paper evaluates the evidence engine and dynamic benchmark.

## Implemented research components

1. Typed deterministic planner for reproducible experiments.
2. Live adapters for RxNorm, DailyMed, Drugs@FDA/openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem.
3. Evidence-state objects with record identifiers, source URLs, retrieval timestamps, qualifiers, and stable evidence IDs.
4. Cross-source deterministic intersections rather than asking an LLM to compute joins from raw JSON.
5. Context-aware evidence relation labels: agreement, complementary, context difference, conflict.
6. Claim-level support verification.
7. User-uploaded candidate-drug × live source joins.
8. Biomedical PDF/TXT document extraction through a server-side model, with deterministic fallback when no model key is configured.
9. Open Targets evidence tables and gene–disease–drug networks.
10. Disease-profile gene clustering instead of symbol-prefix clustering.
11. Hypergeometric disease-set enrichment with Benjamini–Hochberg multiple-testing correction.
12. LiveBioEvidenceBench generator (1,500 reproducible cases) and independent live oracle.
13. Time-stamped source snapshots for repeated temporal evaluation.

## Software validation gates

- `python -m pytest -q` from `ChatAlchemy/backend`
- `npm run typecheck` from `ChatAlchemy`
- `npm run build` in CI/Vercel Linux environment
- Vercel preview health endpoint
- live benchmark smoke after preview deployment
- browser E2E for landing, chats, uploads, biomedical analysis, network, and Continue in Chat

## Experiments still requiring external resources

The code supports the experiment pipeline, but publication claims must not be made until the following are actually run and archived: the full 1,500-case live evaluation, model baselines requiring configured API credentials, repeated temporal runs, frozen external holdout, controlled counterfactual GOS/PMIR experiment, and blinded expert review. These are experimental data-collection steps rather than missing application code.
