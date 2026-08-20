# Blinded Biomedical Expert Evaluation Protocol

Use this protocol only after the final publication method, benchmark configuration, and automated system outputs are frozen. The expert study evaluates **research-assistance quality**, not diagnosis, treatment recommendation, or autonomous clinical decision making.

## Sampling

Target **150–200 evaluated question/answer instances** sampled after automated results are frozen.

Use pre-declared stratification so the sample is not chosen for favorable examples:

- include every structured task family represented in the compared systems;
- include easy, medium, and hard cases;
- include correct and incorrect automated outcomes where available;
- include source-failure/partial-evidence cases when present;
- balance compared systems within each sampled question whenever feasible.

Record the sampling seed and the IDs of all selected benchmark/holdout cases before reviewer scoring begins.

## Reviewers

Use **2–3 independent reviewers with biomedical research expertise**. Record reviewer role/expertise in aggregate form suitable for the manuscript, but do not expose personal identifiers in the public artifact without permission.

Reviewers must not be members of the implementation team when avoidable. If an author serves as a reviewer, disclose this explicitly and keep at least one independent reviewer.

## Blinding and presentation

1. Replace system names with randomly assigned blinded IDs.
2. Randomize system-answer order independently for each question.
3. Give every reviewer the same question, answer, and evidence/provenance material that is part of the evaluated response.
4. Do not expose implementation names, model names, benchmark correctness labels, automated task scores, or other reviewers' ratings.
5. Preserve the randomization map separately until initial scoring is complete.

## Rating dimensions

Each dimension uses a fixed **1–5 scale**. Review the answer as a biomedical research-assistance response within the evidence available to it.

### Factual correctness

- **1:** Substantially incorrect or misleading; central claims conflict with the provided evidence/source records.
- **2:** Major factual problems that materially limit usefulness.
- **3:** Mixed; core direction is plausible but contains meaningful errors or unsupported specificity.
- **4:** Largely correct with only minor non-central issues.
- **5:** Correct on the evaluated question with no material factual error identified.

### Evidence grounding

- **1:** Claims are largely disconnected from, or contradicted by, the displayed evidence.
- **2:** Weak grounding; important claims lack clear source support.
- **3:** Partially grounded; major claims are supported but linkage is incomplete or ambiguous.
- **4:** Strong grounding with minor provenance/linkage weaknesses.
- **5:** Claims are clearly traceable to appropriate displayed evidence and limitations are respected.

### Completeness

- **1:** Misses most information needed to answer the question.
- **2:** Major omissions.
- **3:** Covers the central answer but misses useful relevant evidence or qualification.
- **4:** Substantially complete with only minor omissions.
- **5:** Appropriately complete for the requested scope without unnecessary padding.

### Appropriate uncertainty

- **1:** Seriously overstates certainty or treats missing/failed evidence as established absence/truth.
- **2:** Important uncertainty or source limitations are omitted.
- **3:** Some uncertainty is handled appropriately but wording could be better calibrated.
- **4:** Well calibrated with minor issues.
- **5:** Clearly distinguishes supported findings, missing evidence, source failure, and unresolved uncertainty.

### Scientific usefulness

- **1:** Not useful or potentially misleading as a research starting point.
- **2:** Limited usefulness; substantial re-checking/reconstruction is required.
- **3:** Moderately useful with important caveats.
- **4:** Useful and reasonably efficient for continuing research.
- **5:** Highly useful as an auditable starting point for further biomedical investigation.

### Binary research-starting-point item

Answer **Yes/No**:

> Would you consider this response useful as a starting point for further biomedical research, assuming important findings are independently verified before consequential use?

## Initial scoring and disagreement

- Review independently.
- Do **not** discuss disagreements before initial ratings are locked.
- Preserve every raw reviewer rating.
- Calculate inter-rater agreement before adjudication.
- Recommended agreement reporting: weighted Cohen's kappa for two reviewers or an appropriate multi-rater agreement statistic for three reviewers; report the chosen statistic and confidence interval where feasible.

## Adjudication

Adjudication is optional and must be reported separately from unadjudicated agreement.

If used:

1. lock the original ratings;
2. identify disagreements using a pre-declared rule (for example, a difference of at least 2 scale points or disagreement on the binary item);
3. allow reviewers to discuss only those cases;
4. store the adjudicated value in a separate field rather than overwriting raw ratings.

## Analysis

For each compared system report, at minimum:

- number of rated instances;
- mean/median score for each 1–5 dimension with uncertainty intervals;
- binary research-starting-point proportion with an uncertainty interval;
- inter-rater agreement;
- paired system comparisons when the same question was rated for multiple systems;
- missing ratings and reasons.

Do not treat ordinal 1–5 scores as evidence of clinical safety. Automated benchmark results and human ratings should be reported as complementary outcomes rather than silently pooled.

## Data retention

Retain:

- frozen selected case IDs;
- sampling/randomization seed;
- blinded answer packet;
- system-ID randomization map;
- raw reviewer ratings;
- adjudicated ratings, if any, in separate columns;
- analysis script/output;
- study dates and the publication method SHA.

No synthetic/model-generated reviewer ratings may be substituted for the real expert study while retaining a claim of human expert evaluation.
