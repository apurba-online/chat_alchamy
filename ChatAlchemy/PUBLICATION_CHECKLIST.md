# Publication Readiness Checklist

This checklist defines the evidence required before describing ChatAlchemy as publication-ready.

## Method versioning

- [x] Historical Freeze v1 preserved at `0b994c97e496d581ef3ae68bdb6503431ea1d664`.
- [x] Freeze v1 defects documented before final confirmatory results were locked.
- [x] Benchmark version/seed remain fixed (`LiveBioEvidenceBench-v2.1`, seed `1729`).
- [x] Public split definitions remain fixed (`dev=300`, `test=900`, `stress=300`).
- [x] Primary endpoint and statistical family are fixed in `PUBLICATION_PROTOCOL.md`.
- [ ] Publication Freeze v2 created from the fully validated corrected method.
- [ ] Exact Freeze v2 SHA recorded in paper/reproducibility files.
- [ ] Confirmatory workflows pinned to the exact Freeze v2 SHA.
- [ ] No tuning performed on `test`, `stress`, or the external holdout after Freeze v2.

## Pre-freeze software correctness

- [x] Disease→gene natural-language routing regression covered.
- [x] Open Targets disease resolution handles punctuation/hyphen variants.
- [x] Open Targets HTTP-200 GraphQL errors are surfaced as failures.
- [x] Open Targets association ordering uses the current schema contract.
- [x] Complete openFDA fallback failure is not converted into a successful empty result.
- [x] Complete ChEMBL mechanism-service failure is not converted into a successful empty result.
- [x] Python dependencies pinned.
- [x] Full primary publication campaign restored as manual-only.
- [x] Confirmatory campaign default model aligned to GPT-5.6 Sol.
- [x] Deployment SHA/branch/environment exposed in `/api/health`.
- [ ] Current offline unit/mocked integration tests green.
- [ ] Publication artifact/security gate green.
- [ ] Benchmark determinism/leakage/signature/fingerprint gates green.
- [ ] Strict frontend TypeScript check green.
- [ ] Production frontend build green.
- [ ] Production dependency audit green.
- [ ] Live source contract tests green.
- [ ] Model credential smoke green.

## Confirmatory automated experiments

All paired systems must use the same frozen oracle snapshot.

- [ ] Frozen direct-source oracle snapshot captured and hashed.
- [ ] ChatAlchemy-full on `test` (`n=900`).
- [ ] LLM-only baseline on identical cases.
- [ ] Same-retrieval LLM baseline on identical cases.
- [ ] Unrestricted same-tools LLM agent on identical cases.
- [ ] Full component ablation study.
- [ ] Common-case analysis for paired comparisons with different coverage.
- [ ] Oracle coverage reported for every system/run.
- [ ] `stress` (`n=300`) run and reported separately.
- [ ] Entity-normalization experiment completed.
- [ ] Failure-injection experiment completed.
- [ ] Counterfactual grounding experiment completed.

## Evidence-link and relation claims

- [x] Current verifier is described as claim-to-evidence link validation, not general semantic entailment verification.
- [ ] Claim-producing rate reported.
- [ ] Valid evidence-link rate reported conditional on claim-producing cases.
- [ ] Fully linked claim-case rate reported.
- [ ] If conflict/evidence-relation performance is a central claim, dedicated manual annotation completed.
- [ ] If retained, conflict macro-F1/per-class metrics and inter-rater agreement reported.

## External validity

- [ ] Author-independent private holdout created after Freeze v2.
- [ ] Holdout contains approximately 200–300 natural questions within declared scope.
- [ ] Holdout fingerprint recorded before evaluation.
- [ ] Holdout evaluated once without tuning.
- [ ] Biomedical document subset evaluated separately if document-grounded scientific claims are retained.

## Human expert evaluation

- [ ] 150–200 responses sampled with task/system stratification.
- [ ] System identities blinded and response order randomized.
- [ ] 2–3 biomedical reviewers score independently.
- [ ] Inter-rater agreement calculated before adjudication.
- [ ] Raw reviewer scores retained.
- [ ] Adjudication, if used, reported separately.

## Statistical reporting

- [ ] 95% paired-bootstrap confidence intervals reported for paired score differences.
- [ ] Exact McNemar test used for paired binary exact-correct comparisons.
- [ ] Holm-Bonferroni applied to the pre-specified comparison family.
- [ ] Effect sizes reported with p-values.
- [ ] Missing/oracle-unavailable cases not silently treated as failures or successes.
- [ ] `test` and `stress` results reported separately.

## Efficiency

- [ ] p50 and p95 end-to-end wall-clock latency reported.
- [ ] Source latency separated from end-to-end latency.
- [ ] API/tool calls per case reported.
- [ ] Model input/output/total tokens reported.
- [ ] Model cost reported using the recorded experiment-time pricing.

## Reproducibility artifact

- [ ] Exact Git SHA recorded for every paper table.
- [ ] Exact model identifier and prompt/configuration version recorded.
- [ ] Benchmark version/seed/fingerprint included in artifacts.
- [ ] Frozen oracle snapshot hash retained.
- [ ] Raw per-case predictions, oracle outputs, traces, and source records retained.
- [ ] Paper tables generated programmatically from result files.
- [ ] README contains clean-environment reproduction commands.
- [x] Backend dependency versions pinned.
- [ ] Frontend lockfile/version information archived with final artifact.
- [ ] Final study manifest archived.

## Claims discipline

- [x] No claim that ChatAlchemy is the first multi-tool biomedical agent.
- [x] No clinical-safety, diagnosis, or treatment-recommendation claim.
- [x] Product UI features are not presented as scientific contributions.
- [x] Public benchmark is acknowledged as templated/controlled.
- [x] Direct-source oracle is not described as infallible or perfectly independent ground truth.
- [x] Current evidence-link validator is not described as semantic truth verification.
- [ ] Final limitations match the actual completed experiments.

## Manuscript completion

- [ ] Related Work written from current primary sources.
- [ ] No `[...AUTOFILL]` or placeholder result tokens remain.
- [ ] Abstract values generated from frozen artifacts.
- [ ] Every Results table traces to saved artifacts.
- [ ] Discussion reflects measured effects only.
- [ ] Conclusion written after final results and proportionate to them.
- [ ] Final references and supplementary/reproducibility materials complete.

## Submission rule

ChatAlchemy is **ready for submission** only when Publication Freeze v2 is immutable, the primary/baseline/ablation campaign is complete, external-validity evidence is completed or claims are explicitly narrowed, required human evaluation is complete, final statistics are generated from frozen artifacts, and the manuscript/reproducibility audit has no unresolved critical item.

Temporal T1/T2 evaluation is optional strengthening evidence. If later measurements are unavailable, temporal-adaptation claims must be omitted rather than inferred.
