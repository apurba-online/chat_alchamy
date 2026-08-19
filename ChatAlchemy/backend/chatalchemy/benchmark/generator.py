from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

DRUGS = [
    "pembrolizumab",
    "osimertinib",
    "gefitinib",
    "erlotinib",
    "acetaminophen",
    "trastuzumab",
    "nivolumab",
    "afatinib",
    "cetuximab",
    "panitumumab",
]
COMPOUNDS = [
    "osimertinib",
    "gefitinib",
    "erlotinib",
    "acetaminophen",
    "afatinib",
]
TARGETS = ["EGFR", "ALK", "BRAF", "ERBB2", "MET", "KRAS", "PDCD1", "VEGFA"]
CONDITIONS = [
    "non-small-cell lung cancer",
    "breast cancer",
    "melanoma",
    "colorectal cancer",
    "head and neck cancer",
]
GENES = ["EGFR", "ALK", "BRAF", "ERBB2", "MET", "KRAS", "TP53", "BRCA1", "BRCA2", "PDCD1"]
STATUSES = ["recruiting", "completed", "active, not recruiting"]
STATUS_CANONICAL = {
    "recruiting": "RECRUITING",
    "completed": "COMPLETED",
    "active, not recruiting": "ACTIVE_NOT_RECRUITING",
}
PHASES = ["Phase 1", "Phase 2", "Phase 3"]
PHASE_CANONICAL = {"Phase 1": "PHASE1", "Phase 2": "PHASE2", "Phase 3": "PHASE3"}


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    family: str
    question: str
    oracle: str
    sources: list[str]
    expected_operation: str
    params: dict[str, Any] = field(default_factory=dict)
    output_kind: str = "set"


TEMPLATES: dict[str, tuple[list[str], str, list[str], str]] = {
    "identity": (
        [
            "What is the generic identity of {drug}?",
            "Resolve {drug} to its canonical generic drug identity.",
            "Which generic ingredient does {drug} correspond to?",
        ],
        "identity",
        ["rxnorm"],
        "scalar",
    ),
    "label": (
        [
            "What DailyMed label records are available for {drug}?",
            "List the current DailyMed SPL records for {drug}.",
            "Find DailyMed drug label records for {drug}.",
        ],
        "label",
        ["dailymed"],
        "set",
    ),
    "approval": (
        [
            "What FDA application information is available for {drug}?",
            "List Drugs@FDA application records associated with {drug}.",
            "Which FDA application records mention {drug}?",
        ],
        "approval",
        ["openfda"],
        "set",
    ),
    "trials": (
        [
            "List {phase_text} trials involving {drug} for {condition}.",
            "Find {phase_text} ClinicalTrials.gov studies using {drug} in {condition}.",
            "Which {phase_text} trials of {drug} are registered for {condition}?",
        ],
        "trials",
        ["clinicaltrials"],
        "set",
    ),
    "target": (
        [
            "Which drugs target {target}?",
            "List drug candidates with ChEMBL mechanisms linked to {target}.",
            "What drugs have mechanisms targeting {target}?",
        ],
        "target_drugs",
        ["chembl"],
        "set",
    ),
    "cross": (
        [
            "Which FDA-approved drugs targeting {target} also have {status_text} {phase_text} trials for {condition}?",
            "Intersect {target}-targeting FDA drug records with {status_text} {phase_text} trials in {condition}.",
            "Find {target} drugs with FDA application evidence and {status_text} {phase_text} ClinicalTrials.gov studies for {condition}.",
        ],
        "cross_source",
        ["chembl", "openfda", "clinicaltrials"],
        "set",
    ),
    "gene": (
        [
            "What diseases and known drugs are associated with gene {gene} in Open Targets?",
            "Use Open Targets to list disease associations and known drugs for gene {gene}.",
            "What live Open Targets evidence connects {gene} to diseases or drugs?",
        ],
        "gene",
        ["opentargets"],
        "set",
    ),
    "compound": (
        [
            "What are the PubChem compound properties of {compound}?",
            "Give the PubChem CID, canonical SMILES, and IUPAC name for {compound}.",
            "Look up {compound} in PubChem and return its compound properties.",
        ],
        "compound",
        ["pubchem"],
        "record",
    ),
    "user_approval": (
        [
            "Which drugs in my uploaded list have FDA application records?",
            "Check my uploaded drug candidates against Drugs@FDA/openFDA.",
        ],
        "approval",
        ["openfda"],
        "set",
    ),
    "user_trials": (
        [
            "Which drugs in my uploaded list have {status_text} {phase_text} trials for {condition}?",
            "Check my uploaded candidates for {status_text} {phase_text} ClinicalTrials.gov studies in {condition}.",
        ],
        "trials",
        ["clinicaltrials"],
        "set",
    ),
    "user_target": (
        [
            "Which drugs in my uploaded list target {target}?",
            "Intersect my uploaded candidate drugs with ChEMBL mechanisms for {target}.",
        ],
        "target_drugs",
        ["chembl"],
        "set",
    ),
}


def generate_cases(n: int = 1500, seed: int = 1729) -> list[BenchmarkCase]:
    rng = random.Random(seed)
    families = list(TEMPLATES)
    cases: list[BenchmarkCase] = []
    for i in range(n):
        family = families[i % len(families)]
        templates, operation, sources, output_kind = TEMPLATES[family]
        phase_text = rng.choice(PHASES)
        status_text = rng.choice(STATUSES)
        candidates = rng.sample(DRUGS, k=3)
        params = {
            "drug": rng.choice(DRUGS),
            "compound": rng.choice(COMPOUNDS),
            "target": rng.choice(TARGETS),
            "condition": rng.choice(CONDITIONS),
            "gene": rng.choice(GENES),
            "status": STATUS_CANONICAL[status_text],
            "phase": PHASE_CANONICAL[phase_text],
            "status_text": status_text,
            "phase_text": phase_text,
            "candidates": candidates,
        }
        question = rng.choice(templates).format(**params)
        cases.append(
            BenchmarkCase(
                id=f"livebio-{i + 1:04d}",
                family=family,
                question=question,
                oracle="independent_live_api_oracle",
                sources=sources,
                expected_operation=operation,
                params=params,
                output_kind=output_kind,
            )
        )
    return cases


def as_jsonable(cases: Iterable[BenchmarkCase]):
    return [asdict(case) for case in cases]
