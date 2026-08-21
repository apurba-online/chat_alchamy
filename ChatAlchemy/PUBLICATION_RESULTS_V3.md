# Publication Freeze v3 - authoritative results record

This file records completed scientific results for the ChatAlchemy publication. It is intentionally stored on a publication-results branch created from the immutable Publication Freeze v3 commit. It does **not** modify or move the frozen method.

## Immutable scientific method

- Freeze branch: `paper-v3-freeze-2026-08-20`
- Method SHA: `f13c3aa8e887b2ddece4badcd29987104ea39c64`
- Benchmark: `LiveBioEvidenceBench-v2.1`
- Seed: `1729`
- Confirmatory GitHub Actions run: `32394142757`
- Confirmatory test split: 900 cases
- Stress split: 300 cases, evaluated separately from the primary endpoint

## Confirmatory test

The frozen direct-source oracle was available for 655/900 cases (72.78%). ChatAlchemy achieved a mean task score of 99.88% on those 655 oracle-covered cases, with 654/655 perfect scores and 100% routing accuracy. Mean provenance-record F1 was approximately 0.915. Median end-to-end latency was approximately 543 ms and p95 latency was 15.87 s. Mean structured API usage was 7.18 calls per attempted case.

All 245 oracle-unavailable test cases were trial-dependent and were unavailable because ClinicalTrials.gov returned HTTP 403 during frozen oracle capture. These cases are not scored as biomedical negatives.

### Paired common-case comparisons

- ChatAlchemy vs LLM-only: n=218, +41.28 percentage points, 95% paired-bootstrap CI 35.61 to 47.15 pp, Holm-adjusted p approximately 1.44e-34.
- ChatAlchemy vs same-retrieval LLM: n=234, +1.34 pp, 95% CI 0.26 to 2.73 pp, Holm-adjusted p=0.03125.
- ChatAlchemy vs unrestricted same-tools agent: n=126, +39.91 pp, 95% CI 31.31 to 48.57 pp, Holm-adjusted p approximately 8.88e-16.

The model baselines experienced substantial HTTP 429/provider-side failures. Their conditional task scores are therefore reported together with execution-success denominators and paired common-case analyses.

## Ablations

Four pre-specified ablations were evaluated on the 655 oracle-covered cases. None produced a statistically significant answer-score decrement after Holm correction. The benchmark is near ceiling on the covered subset, and all trial-dependent hard cases were unavailable, limiting end-to-end ablation sensitivity.

## Separate entity-disjoint stress evaluation

The stress campaign used the same immutable method with a distinct frozen oracle snapshot. It is reported independently from the 900-case primary test.

- Attempted: 300
- Oracle-covered: 219/300 (73.00%)
- Mean task score on covered cases: 100.00%
- Routing accuracy: 100.00%
- Mean provenance-record F1: 0.9157
- Supported-claim rate conditional on claim production: 100.00%
- Median end-to-end latency: 545 ms
- p95 end-to-end latency: 5.41 s
- Mean structured API calls: 6.58 per attempted case

Coverage was 138/138 for easy, 81/108 for medium, and 0/54 for hard stress cases. The 81 unavailable stress cases were concentrated in ClinicalTrials.gov-dependent families under the same HTTP 403 source-access limitation. The 100% stress score is therefore conditional on oracle-covered cases and supports robustness to new benchmark entities within the declared structured task families, not unrestricted natural-language generalization.

## Entity-normalization evaluation

A separate live RxNorm evaluation tested 32 brand-name aliases spanning the benchmark entity pools.

- Resolution rate: 32/32 (100%)
- Exact expected canonical generic identity: 32/32 (100%)
- No-normalization exact control: 0/32 (0%)
- Median normalization latency: 204 ms

This targeted evaluation supplies direct component-level evidence for normalization despite the saturated aggregate ablation result.

## Controlled source-failure injection

Both `exception` and `empty` fault modes were executed at the local adapter boundary for all seven supported sources: RxNorm, DailyMed, openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem.

Across every injected condition:

- qualification-or-abstention rate: 100%
- unsupported-claim case rate: 0%

For exception-mode injection, the failed-source trace was visible in 100% of tested cases for every source. Empty-result injection intentionally produces no exception trace and therefore had a 0% failure-trace rate; it tests false-zero handling, and the system still qualified or abstained rather than asserting unsupported biomedical absence.

Where a frozen oracle was available, paired task-score degradation under source removal was 100 percentage points for RxNorm, DailyMed, openFDA, Open Targets, and PubChem. For ChEMBL the control mean was 99.2%, injected mean was 47.0%, and paired degradation was 52.2 pp over 100 covered pairs, reflecting outputs partly recoverable through other evidence paths. ClinicalTrials.gov task-score degradation was not estimable because the frozen oracle had zero coverage for the selected trial-dependent cases.

## Counterfactual grounding

The pre-specified 120-case counterfactual grounding suite completed successfully using GPT-5.6 Sol with prompt version `counterfactual-v2` and seed 1729. The suite contains four balanced synthetic reversal families (30 cases each): mechanism, regulatory status, target relation, and trial status. These are controlled evaluation records and do not modify external biomedical sources.

- Evidence-constrained mean grounding-on-source (GOS): 1.000
- Question-only mean GOS: 0.000
- Mean GOS gain: +1.000
- Evidence-constrained mean parametric-memory intrusion rate (PMIR): 0.000
- Question-only mean PMIR: 0.050
- Mean PMIR reduction: 0.050
- Evidence-constrained exact-required rate: 120/120 (100%)
- Evidence-constrained forbidden-intrusion rate: 0/120 (0%)

All 120 evidence-constrained responses matched the synthetic record exactly and none used a forbidden outside-knowledge label. The question-only arm returned many empty/unknown answers under the intentionally strict one-token controlled prompt and had a 5% overall forbidden-intrusion rate, concentrated in the regulatory-reversal family (20%). These diagnostics measure compliance with provided counterfactual evidence under a synthetic controlled setting; they are not a measure of real-world biomedical truthfulness or clinical validity.

## Human-dependent studies

The blinded expert-review packet, blinding key, external-holdout author instructions, and holdout schema have been generated. They are preparation artifacts only. No expert ratings are fabricated, and no supposedly independent external questions are self-authored by the implementation team. These studies remain pending real external participants.

## Interpretation boundaries

- Scores are conditional on frozen-oracle coverage and must always be accompanied by denominators.
- Live-source/API outages are separated from biomedical answer errors.
- Stress results are separate from the confirmatory primary endpoint.
- LiveBioEvidenceBench-v2.1 is a controlled structured benchmark introduced for this study; it does not establish unrestricted natural-language generalization or clinical safety.
- Claim-to-evidence validation establishes provenance linkage, not general semantic entailment or clinical truth.
- ChatAlchemy is evaluated as biomedical research assistance, not diagnosis, prescribing, or autonomous clinical decision support.

## Production boundary

The validated production release candidate remains the immutable scientific version at `f13c3aa8e887b2ddece4badcd29987104ea39c64`. Public production promotion is separately blocked until Vercel account-level spend/budget settings and global Firewall/WAF abuse controls are manually confirmed. Frontend-only production hotfixes after the freeze are outside the scientific evaluation.