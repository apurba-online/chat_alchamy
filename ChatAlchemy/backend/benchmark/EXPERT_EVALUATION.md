# Blinded expert evaluation protocol

Use this only after system configurations are frozen. Target 150-200 stratified questions and 2-3 independent biomedical reviewers.

1. Randomize system answer order and replace system names with blinded IDs.
2. Give reviewers the question, answer, and the evidence links shown to the system. Do not expose implementation names.
3. Reviewers score each answer from 1-5 for factual correctness, evidence grounding, completeness, appropriate uncertainty, and scientific usefulness.
4. Reviewers also answer a binary question: `Useful as a starting point for further research?`
5. Do not resolve disagreements during initial scoring. Calculate inter-rater agreement first.
6. Preserve the raw ratings. Report aggregate results with confidence intervals and agreement statistics.

This is a research-assistance evaluation, not an evaluation of autonomous clinical decision making.
