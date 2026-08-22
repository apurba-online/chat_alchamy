# ChatAlchemy Publication Manuscript - Final Freeze v3 Audit

Scientific method: `paper-v3-freeze-2026-08-20` at immutable SHA `f13c3aa8e887b2ddece4badcd29987104ea39c64`.

This publication-side record documents the final manuscript integration after completion of the automatable Freeze v3 evaluation program. It does not modify or move the scientific freeze.

## Integrated evidence

- Confirmatory test: 900 attempted; frozen oracle available for 655/900 (72.78%); ChatAlchemy mean task score 99.88% on covered cases; 100% scorable prediction coverage on covered cases.
- Pairwise identical-case comparisons: +41.28 pp vs LLM-only (n=218), +1.34 pp vs same-retrieval LLM (n=234), +39.91 pp vs unrestricted same-tools (n=126), all significant after Holm adjustment.
- Separate stress split: 300 attempted; 219/300 oracle-covered; 100.00% mean task score and 100% routing accuracy on covered cases; provenance F1 0.9157; p50 545 ms; p95 5.41 s; 6.58 structured API calls per attempted case.
- Live RxNorm normalization: 32/32 exact expected canonical identities; no-normalization control 0/32.
- Seven-source fault injection: 100% qualification/abstention and 0% unsupported-claim cases across tested conditions.
- Counterfactual grounding: 120 balanced synthetic reversals; evidence-constrained GOS 1.000, PMIR 0.000, 120/120 exact-required, 0/120 forbidden intrusions; question-only GOS 0.000 and PMIR 0.050.

## Manuscript changes after final audit

- Updated Abstract, Experimental Design, Results, Discussion, and Conclusion to include the completed stress, source-failure, and counterfactual results.
- Expanded Related Work with current peer-reviewed biomedical RAG/research-agent literature, including BiomedRAG (JBI 2025), BRAD (Bioinformatics 2025), and DeepEvidence (Nature Machine Intelligence 2026), while retaining MedRAG/MIRAGE, GeneGPT, TxAgent, SciToolAgent, BioMedAgent, BioResearcher, and BioMedArena.
- Retained the full system-architecture and researcher-workflow figures to balance the application and evaluation contributions.
- Explicitly limited the 120-case counterfactual result to controlled synthetic evidence obedience; it is not presented as real-world biomedical truthfulness, clinical validity, or general hallucination freedom.
- Explicitly reports that the blinded expert study and author-independent external holdout remain pending real external participants and are not fabricated.
- Explicitly retains the lack of a user-centered usability study as a limitation.

## Interpretation boundaries

The 99.88% confirmatory score applies only to the 655 oracle-covered test cases. Trial-dependent cases unavailable under the frozen ClinicalTrials.gov HTTP 403 state are not treated as biomedical negatives. Stress results are reported separately from the primary endpoint. Provenance-link validation verifies record linkage rather than semantic entailment or clinical truth. LiveBioEvidenceBench v2.1 evaluates a declared structured task grammar and does not establish unrestricted natural-language generalization.

## Remaining submission-specific work

1. Confirm final author list/order, affiliations, and ORCIDs.
2. Select the exact IEEE venue and apply its page limit, reference policy, and single/double-blind requirements.
3. Human-dependent expert ratings and genuinely author-independent holdout questions remain pending external participants.
4. Public production promotion remains separately blocked until Vercel account-level spend/budget and global Firewall/WAF abuse controls are manually confirmed.

The current generic IEEE conference manuscript compiles to 8 pages including references. All numerical manuscript claims in this final audit derive from completed frozen artifacts; no values are invented or imputed.
