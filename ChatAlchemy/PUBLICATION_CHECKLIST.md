# Publication Readiness Checklist

This checklist defines the evidence required before describing ChatAlchemy as publication-ready.

## Method freeze
- [x] Architecture frozen at commit `0b994c97e496d581ef3ae68bdb6503431ea1d664`.
- [x] Planner/tool schemas frozen for the confirmatory study.
- [x] Benchmark version and seed frozen (`LiveBioEvidenceBench-v2.1`, seed `1729`).
- [x] Test/stress entity pools frozen.
- [x] Primary outcomes and statistical tests frozen in `PUBLICATION_PROTOCOL.md`.
- [ ] No tuning performed on the external holdout after it is created.

## Software quality
- [x] Offline unit/mocked integration tests pass.
- [x] Benchmark leakage/determinism tests pass.
- [x] Publication artifact CI gate passes.
- [x] Frontend strict TypeScript check passes.
- [x] Production frontend build passes.
- [x] Live source contract tests pass.
- [x] Frozen-ID live benchmark smoke passes.
- [x] No client-side secret or bundled pharmaceutical corpus.

## Main experiments
- [ ] Full ChatAlchemy run on frozen test split.
- [ ] LLM-only baseline on identical test cases.
- [ ] Same-retrieval LLM baseline on identical test cases.
- [ ] Unrestricted tool-agent baseline where technically comparable.
- [ ] Full component ablation study.
- [ ] Common-case analysis for all paired comparisons.
- [ ] Oracle coverage reported for every system/run.

## Reliability experiments
- [ ] Conflict evaluation set independently annotated, if conflict classification is retained as a central quantitative claim.
- [ ] Conflict macro-F1 reported with per-class metrics, if applicable.
- [ ] Counterfactual GOS/PMIR experiment completed.
- [ ] Failure-injection experiment completed.
- [ ] Abstention and unsafe-fallback rates reported.
- [ ] Source failure cases separated from reasoning errors.

## Temporal evaluation — optional strengthening evidence
- [ ] T0 frozen run retained.
- [ ] Later repeated runs completed on identical case IDs, if temporal claims are included.
- [ ] Genuine source-state changes separated from API/schema outages, if temporal claims are included.
- [ ] Temporal adaptation accuracy reported on changed-oracle cases, if temporal claims are included.

Temporal evaluation does **not** block the accelerated main submission. If later measurements are unavailable, strong temporal-adaptation claims must be omitted rather than inferred.

## External validity
- [ ] Author-independent holdout created after method freeze.
- [ ] Holdout fingerprint recorded before evaluation.
- [ ] Holdout evaluated once without tuning.
- [ ] Biomedical document subset evaluated separately from templated live-API benchmark, if included as a manuscript claim.

## Human evaluation
- [ ] 150-200 responses selected with stratification across task families/systems.
- [ ] System identities blinded and response order randomized.
- [ ] 2-3 biomedical reviewers score independently.
- [ ] Inter-rater agreement calculated.
- [ ] Adjudication, if used, reported separately from raw reviewer agreement.

## Statistical reporting
- [ ] 95% paired-bootstrap CIs reported for paired score differences.
- [ ] Exact McNemar test used for paired binary exact-correct comparisons.
- [ ] Holm-Bonferroni applied to the pre-specified comparison family.
- [ ] Effect sizes reported with p-values.
- [ ] Missing/oracle-unavailable cases not silently treated as failures or successes.
- [ ] Test and stress results reported separately.

## Efficiency
- [ ] p50 and p95 wall-clock latency reported.
- [ ] Source latency separated from end-to-end latency.
- [ ] API calls per case reported.
- [ ] Model token usage and cost reported for model-based systems.

## Reproducibility artifact
- [ ] Exact git SHA recorded for every paper table.
- [ ] Model identifiers and prompt versions recorded.
- [ ] Benchmark/version/seed included in artifacts.
- [ ] Raw per-case predictions and oracle outputs retained.
- [ ] Paper tables generated programmatically from result files.
- [ ] README contains exact reproduction commands.
- [ ] Environment/dependency versions archived with final artifact.
- [x] Manuscript shell created from the frozen implementation/protocol; numerical Results remain artifact-gated.

## Claims discipline
- [x] No claim that ChatAlchemy is the first multi-tool biomedical agent.
- [x] No clinical-safety or treatment recommendation claim.
- [x] No conflict-resolution novelty claim stronger than experiments support.
- [x] Product UI features not presented as scientific contributions.
- [x] Planned limitations explicitly cover templated language, public-source coverage, dynamic-source availability, and absence of clinical validation.

## Accelerated submission rule

**Ready for the main submission** requires the automated primary/baseline/ablation/statistical campaign, external-validity evidence or an explicitly narrowed external-validity claim, blinded expert evaluation, and the final reproducibility/manuscript audit. Temporal T1/T2 do not block submission; temporal claims are included only if real later measurements exist.
