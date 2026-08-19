# Publication Readiness Checklist

This checklist defines the minimum evidence required before describing ChatAlchemy as publication-ready.

## Method freeze
- [ ] Architecture version tagged.
- [ ] Planner/tool schemas frozen.
- [ ] Benchmark version and seed frozen.
- [ ] Test/stress entity pools frozen.
- [ ] Primary outcomes and statistical tests frozen in `PUBLICATION_PROTOCOL.md`.
- [ ] No tuning performed on the external holdout.

## Software quality
- [ ] Offline unit/mocked integration tests pass.
- [ ] Benchmark leakage/determinism tests pass.
- [ ] Publication artifact CI gate passes.
- [ ] Frontend strict TypeScript check passes.
- [ ] Production frontend build passes.
- [ ] Live source contract tests pass.
- [ ] Preview deployment smoke-tested for chat, upload, biomedical analysis, and exports.
- [ ] No client-side secret or bundled pharmaceutical corpus.

## Main experiments
- [ ] Full ChatAlchemy run on frozen test split.
- [ ] LLM-only baseline on identical test cases.
- [ ] Same-retrieval LLM baseline on identical test cases.
- [ ] Unrestricted tool-agent baseline where technically comparable.
- [ ] Full component ablation study.
- [ ] Common-case analysis for all paired comparisons.
- [ ] Oracle coverage reported for every system/run.

## Reliability experiments
- [ ] Conflict evaluation set independently annotated.
- [ ] Conflict macro-F1 reported with per-class metrics.
- [ ] Counterfactual GOS/PMIR experiment completed.
- [ ] Failure-injection experiment completed.
- [ ] Abstention and unsafe-fallback rates reported.
- [ ] Source failure cases separated from reasoning errors.

## Temporal evaluation
- [ ] T0 frozen run completed.
- [ ] At least two later repeated runs completed on identical case IDs.
- [ ] Genuine source-state changes separated from API/schema outages.
- [ ] Temporal adaptation accuracy reported on changed-oracle cases.

## External validity
- [ ] Author-independent holdout created after method freeze.
- [ ] Holdout fingerprint recorded before evaluation.
- [ ] Holdout evaluated once without tuning.
- [ ] Biomedical document subset evaluated separately from templated live-API benchmark.

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

## Claims discipline
- [ ] No claim that ChatAlchemy is the first multi-tool biomedical agent.
- [ ] No clinical-safety or treatment recommendation claim.
- [ ] No conflict-resolution novelty claim stronger than experiments support.
- [ ] Product UI features not presented as scientific contributions.
- [ ] Limitations explicitly discuss templated language, public-source coverage, dynamic-source availability, and absence of clinical validation.

A paper submission should not mark the project complete until all applicable items are satisfied or explicitly documented as limitations.
