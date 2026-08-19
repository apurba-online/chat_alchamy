from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

BENCHMARK_VERSION = "LiveBioEvidenceBench-v2.1"
SPLIT_RATIOS = {"dev": 0.20, "test": 0.60, "stress": 0.20}


@dataclass(frozen=True)
class EntityPool:
    drugs: tuple[str, ...]
    aliases: tuple[tuple[str, str], ...]
    compounds: tuple[str, ...]
    targets: tuple[str, ...]
    conditions: tuple[str, ...]
    genes: tuple[str, ...]


ENTITY_POOLS: dict[str, EntityPool] = {
    "dev": EntityPool(
        drugs=(
            "pembrolizumab", "osimertinib", "acetaminophen", "trastuzumab",
            "nivolumab", "afatinib", "erlotinib", "cetuximab",
        ),
        aliases=(
            ("Keytruda", "pembrolizumab"), ("Tagrisso", "osimertinib"),
            ("Tylenol", "acetaminophen"), ("Herceptin", "trastuzumab"),
            ("Opdivo", "nivolumab"), ("Gilotrif", "afatinib"),
            ("Tarceva", "erlotinib"), ("Erbitux", "cetuximab"),
        ),
        compounds=(
            "osimertinib", "acetaminophen", "afatinib", "erlotinib",
            "ibuprofen", "aspirin", "metformin", "atorvastatin",
        ),
        targets=("EGFR", "ERBB2", "PDCD1", "VEGFA"),
        conditions=(
            "non-small-cell lung cancer", "breast cancer", "melanoma", "multiple myeloma",
        ),
        genes=("EGFR", "ERBB2", "PDCD1", "TP53", "BRCA1", "BRCA2"),
    ),
    "test": EntityPool(
        drugs=(
            "gefitinib", "panitumumab", "imatinib", "rituximab", "bevacizumab",
            "atezolizumab", "durvalumab", "crizotinib", "lorlatinib", "dabrafenib",
            "vemurafenib", "olaparib",
        ),
        aliases=(
            ("Iressa", "gefitinib"), ("Vectibix", "panitumumab"),
            ("Gleevec", "imatinib"), ("Rituxan", "rituximab"),
            ("Avastin", "bevacizumab"), ("Tecentriq", "atezolizumab"),
            ("Imfinzi", "durvalumab"), ("Xalkori", "crizotinib"),
            ("Lorbrena", "lorlatinib"), ("Tafinlar", "dabrafenib"),
            ("Zelboraf", "vemurafenib"), ("Lynparza", "olaparib"),
        ),
        compounds=(
            "gefitinib", "imatinib", "crizotinib", "lorlatinib", "dabrafenib",
            "vemurafenib", "olaparib", "rucaparib", "niraparib", "ceritinib",
            "brigatinib", "tramadol",
        ),
        targets=("ALK", "BRAF", "MET", "KRAS", "PARP1", "ESR1", "VEGFR2", "KIT", "ABL1", "CD20", "BTK", "JAK2"),
        conditions=(
            "colorectal cancer", "head and neck squamous cell carcinoma", "ovarian cancer",
            "renal cell carcinoma", "urothelial carcinoma", "hepatocellular carcinoma",
            "diffuse large B-cell lymphoma", "acute myeloid leukemia",
            "chronic lymphocytic leukemia", "prostate cancer",
        ),
        genes=("ALK", "BRAF", "MET", "KRAS", "PARP1", "ESR1", "PTEN", "PIK3CA", "KIT", "ABL1", "MS4A1", "KDR"),
    ),
    "stress": EntityPool(
        drugs=(
            "trametinib", "selpercatinib", "capmatinib", "tepotinib", "sotorasib",
            "adagrasib", "amivantamab", "lapatinib", "pertuzumab", "palbociclib",
            "alpelisib", "everolimus",
        ),
        aliases=(
            ("Mekinist", "trametinib"), ("Retevmo", "selpercatinib"),
            ("Tabrecta", "capmatinib"), ("Tepmetko", "tepotinib"),
            ("Lumakras", "sotorasib"), ("Krazati", "adagrasib"),
            ("Rybrevant", "amivantamab"), ("Tykerb", "lapatinib"),
            ("Perjeta", "pertuzumab"), ("Ibrance", "palbociclib"),
            ("Piqray", "alpelisib"), ("Afinitor", "everolimus"),
        ),
        compounds=(
            "trametinib", "selpercatinib", "capmatinib", "tepotinib", "sotorasib",
            "adagrasib", "lapatinib", "palbociclib", "alpelisib", "everolimus",
            "tofacitinib", "pemigatinib",
        ),
        targets=("RET", "ROS1", "PIK3CA", "CDK4", "CDK6", "FGFR2", "FGFR3", "MTOR"),
        conditions=(
            "pancreatic adenocarcinoma", "gastric cancer", "endometrial cancer", "glioblastoma",
            "thyroid cancer", "cholangiocarcinoma", "mesothelioma", "soft tissue sarcoma",
            "small-cell lung cancer", "cervical cancer",
        ),
        genes=("RET", "ROS1", "PIK3CA", "CDK4", "CDK6", "FGFR2", "FGFR3", "MTOR", "TSC1", "TSC2"),
    ),
}

STATUSES = ("recruiting", "completed", "active, not recruiting")
STATUS_CANONICAL = {
    "recruiting": "RECRUITING",
    "completed": "COMPLETED",
    "active, not recruiting": "ACTIVE_NOT_RECRUITING",
}
PHASES = ("Phase 1", "Phase 2", "Phase 3")
PHASE_CANONICAL = {"Phase 1": "PHASE1", "Phase 2": "PHASE2", "Phase 3": "PHASE3"}


@dataclass(frozen=True)
class FamilySpec:
    templates: tuple[str, ...]
    operation: str
    sources: tuple[str, ...]
    output_kind: str
    difficulty: str


FAMILY_SPECS: dict[str, FamilySpec] = {
    "identity": FamilySpec(
        (
            "What is the generic identity of {drug}?",
            "Resolve {drug} to its canonical generic drug identity.",
            "Which generic ingredient does {drug} correspond to?",
            "What generic name does RxNorm assign to {drug}?",
            "Identify the RxCUI-linked generic ingredient for {drug}.",
            "Using RxNorm, resolve {drug} to a generic ingredient.",
            "Give the canonical RxNorm identity for {drug}.",
            "What is the canonical drug identity of {drug} in RxNorm?",
        ),
        "identity", ("rxnorm",), "scalar", "easy",
    ),
    "label": FamilySpec(
        (
            "What DailyMed label records are available for {drug}?",
            "List the current DailyMed SPL records for {drug}.",
            "Find DailyMed drug label records for {drug}.",
            "Show the live DailyMed labels associated with {drug}.",
            "Which SPL label records does DailyMed return for {drug}?",
            "Retrieve DailyMed label records for {drug}.",
            "What current drug label records are listed in DailyMed for {drug}?",
            "List SPL records from DailyMed for {drug}.",
        ),
        "label", ("dailymed",), "set", "easy",
    ),
    "approval": FamilySpec(
        (
            "What FDA application information is available for {drug}?",
            "List Drugs@FDA application records associated with {drug}.",
            "Which FDA application records mention {drug}?",
            "Find FDA application records for {drug}.",
            "Show live Drugs@FDA records associated with {drug}.",
            "What approval records does FDA data return for {drug}?",
            "Retrieve the FDA application records linked to {drug}.",
            "Which Drugs@FDA applications are associated with {drug}?",
        ),
        "approval", ("openfda",), "set", "easy",
    ),
    "trials": FamilySpec(
        (
            "List {phase_text} trials involving {drug} for {condition}.",
            "Find {phase_text} ClinicalTrials.gov studies using {drug} in {condition}.",
            "Which {phase_text} trials of {drug} are registered for {condition}?",
            "Show {phase_text} clinical trials involving {drug} for {condition}.",
            "What {phase_text} ClinicalTrials.gov trials use {drug} in {condition}?",
            "Retrieve {phase_text} trials of {drug} for {condition}.",
            "Which registered {phase_text} studies involve {drug} in {condition}?",
            "List ClinicalTrials.gov {phase_text} studies involving {drug} for {condition}.",
        ),
        "trials", ("clinicaltrials",), "set", "medium",
    ),
    "target": FamilySpec(
        (
            "Which drugs target {target}?",
            "List drug candidates with ChEMBL mechanisms linked to {target}.",
            "What drugs have mechanisms targeting {target}?",
            "Which ChEMBL drugs target {target}?",
            "List {target} inhibitors with ChEMBL mechanism evidence.",
            "Find drugs with a ChEMBL mechanism targeting {target}.",
            "What drug candidates are linked to target {target} in ChEMBL?",
            "Retrieve ChEMBL drug mechanisms for target {target}.",
            "Which molecules have ChEMBL mechanism records for target {target}?",
            "Show drug mechanisms associated with target {target} in ChEMBL.",
        ),
        "target_drugs", ("chembl",), "set", "easy",
    ),
    "cross": FamilySpec(
        (
            "Which FDA-approved drugs targeting {target} also have {status_text} {phase_text} trials for {condition}?",
            "Intersect {target}-targeting FDA drug records with {status_text} {phase_text} trials in {condition}.",
            "Find {target} drugs with FDA application evidence and {status_text} {phase_text} ClinicalTrials.gov studies for {condition}.",
            "Which drugs targeting {target} have FDA records and {status_text} {phase_text} trials for {condition}?",
            "Among FDA-recorded drugs targeting {target}, which have {status_text} {phase_text} trials in {condition}?",
            "Cross-check {target}-targeting drugs against FDA records and {status_text} {phase_text} trials for {condition}.",
            "Return the intersection of FDA-recorded {target} drugs and {status_text} {phase_text} ClinicalTrials.gov studies in {condition}.",
            "Which {target}-targeting drug candidates satisfy both FDA-record and {status_text} {phase_text} trial constraints for {condition}?",
        ),
        "cross_source", ("chembl", "openfda", "clinicaltrials"), "set", "hard",
    ),
    "gene": FamilySpec(
        (
            "What diseases and known drugs are associated with gene {gene} in Open Targets?",
            "Use Open Targets to list disease associations and known drugs for gene {gene}.",
            "What live Open Targets evidence connects gene {gene} to diseases or drugs?",
            "Show disease and drug evidence for gene {gene} from Open Targets.",
            "Which diseases and known drugs does Open Targets associate with gene {gene}?",
            "Retrieve Open Targets evidence for gene {gene}.",
            "What disease associations and clinical drug candidates are linked to gene {gene} in Open Targets?",
            "Summarize live Open Targets disease and drug records for gene {gene}.",
        ),
        "gene", ("opentargets",), "set", "medium",
    ),
    "compound": FamilySpec(
        (
            "What are the PubChem compound properties of {compound}?",
            "Give the PubChem CID, canonical SMILES, and IUPAC name for {compound}.",
            "Look up {compound} in PubChem and return its compound properties.",
            "What canonical SMILES and IUPAC name does PubChem report for {compound}?",
            "Retrieve the PubChem compound record for {compound}.",
            "Show PubChem CID and compound properties for {compound}.",
            "Using PubChem, return the CID, SMILES, and IUPAC name of {compound}.",
            "What chemical structure identifiers does PubChem provide for {compound}?",
        ),
        "compound", ("pubchem",), "record", "easy",
    ),
    "user_approval": FamilySpec(
        (
            "Which drugs in my uploaded list have FDA application records?",
            "Check my uploaded drug candidates against Drugs@FDA/openFDA.",
            "From my uploaded list, which drugs have FDA application evidence?",
            "Cross-check my uploaded drug list with FDA application records.",
            "Which uploaded candidates appear in Drugs@FDA records?",
            "Use FDA records to filter the drugs in my uploaded list.",
            "Return uploaded drugs that have Drugs@FDA application records.",
            "Which candidates from my uploaded data have FDA records?",
        ),
        "approval", ("openfda",), "set", "medium",
    ),
    "user_trials": FamilySpec(
        (
            "Which drugs in my uploaded list have {status_text} {phase_text} trials for {condition}?",
            "Check my uploaded candidates for {status_text} {phase_text} ClinicalTrials.gov studies in {condition}.",
            "Filter my uploaded drugs to those with {status_text} {phase_text} trials for {condition}.",
            "Which uploaded candidates are in {status_text} {phase_text} trials for {condition}?",
            "Cross-check my uploaded list against {status_text} {phase_text} ClinicalTrials.gov studies in {condition}.",
            "Return uploaded drugs with {status_text} {phase_text} trial evidence for {condition}.",
            "Which drugs from my uploaded data have {status_text} {phase_text} trials in {condition}?",
            "Use ClinicalTrials.gov to filter my uploaded candidates for {status_text} {phase_text} studies in {condition}.",
        ),
        "trials", ("clinicaltrials",), "set", "hard",
    ),
    "user_target": FamilySpec(
        (
            "Which drugs in my uploaded list target {target}?",
            "Intersect my uploaded candidate drugs with ChEMBL mechanisms for {target}.",
            "Which uploaded drugs have ChEMBL mechanism evidence targeting {target}?",
            "Filter my uploaded drug list to candidates that target {target}.",
            "Cross-check my uploaded drugs against ChEMBL target {target} mechanisms.",
            "Return uploaded candidates linked to target {target} in ChEMBL.",
            "Which drugs from my uploaded data have mechanisms targeting {target}?",
            "Use ChEMBL to identify uploaded drugs that target {target}.",
            "Which uploaded candidates have mechanism records for target {target}?",
            "Filter my uploaded candidate set using ChEMBL target {target} evidence.",
        ),
        "target_drugs", ("chembl",), "set", "medium",
    ),
}


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
    split: str = "dev"
    difficulty: str = "easy"
    template_id: str = ""
    primary_entity: str = ""
    primary_entity_type: str = ""
    task_signature: str = ""


def split_sizes(n: int) -> dict[str, int]:
    if n < 1:
        raise ValueError("benchmark size must be positive")
    dev = round(n * SPLIT_RATIOS["dev"])
    test = round(n * SPLIT_RATIOS["test"])
    stress = n - dev - test
    return {"dev": dev, "test": test, "stress": stress}


def _primary(family: str, params: dict[str, Any]) -> tuple[str, str]:
    if family == "identity":
        return str(params["identity_generic"]), "drug"
    if family in {"label", "approval", "trials"}:
        return str(params["drug"]), "drug"
    if family == "compound":
        return str(params["compound"]), "drug"
    if family in {"target", "cross", "user_target"}:
        return str(params["target"]), "target"
    if family == "gene":
        return str(params["gene"]), "gene"
    if family in {"user_approval", "user_trials"}:
        return str(params["candidates"][0]), "drug"
    return "", "unknown"


def _draw_params(rng: random.Random, pool: EntityPool, family: str) -> dict[str, Any]:
    alias, generic = rng.choice(pool.aliases)
    drug = alias if family == "identity" else rng.choice(pool.drugs)
    phase_text = rng.choice(PHASES)
    status_text = rng.choice(STATUSES)
    return {
        "drug": drug,
        "identity_generic": generic,
        "compound": rng.choice(pool.compounds),
        "target": rng.choice(pool.targets),
        "condition": rng.choice(pool.conditions),
        "gene": rng.choice(pool.genes),
        "status": STATUS_CANONICAL[status_text],
        "phase": PHASE_CANONICAL[phase_text],
        "status_text": status_text,
        "phase_text": phase_text,
        "candidates": rng.sample(list(pool.drugs), k=3),
    }


def _task_signature(family: str, question: str, params: dict[str, Any]) -> str:
    context: dict[str, Any] = {"family": family, "question": question}
    if family.startswith("user_"):
        context["candidates"] = sorted(str(x).lower() for x in params.get("candidates", []))
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_cases(n: int = 1500, seed: int = 1729) -> list[BenchmarkCase]:
    rng = random.Random(seed)
    sizes = split_sizes(n)
    families = list(FAMILY_SPECS)
    seen_signatures: set[str] = set()
    cases: list[BenchmarkCase] = []
    global_index = 0

    for split in ("dev", "test", "stress"):
        pool = ENTITY_POOLS[split]
        for local_index in range(sizes[split]):
            family = families[local_index % len(families)]
            spec = FAMILY_SPECS[family]
            question = ""
            params: dict[str, Any] = {}
            template_index = 0
            signature = ""
            for _ in range(2000):
                params = _draw_params(rng, pool, family)
                template_index = rng.randrange(len(spec.templates))
                question = spec.templates[template_index].format(**params)
                signature = _task_signature(family, question, params)
                if signature not in seen_signatures:
                    break
            else:
                raise RuntimeError(f"could not generate a unique benchmark task for {split}/{family}")

            seen_signatures.add(signature)
            global_index += 1
            primary_entity, primary_type = _primary(family, params)
            cases.append(
                BenchmarkCase(
                    id=f"livebio-{global_index:04d}",
                    family=family,
                    question=question,
                    oracle="independent_live_api_oracle",
                    sources=list(spec.sources),
                    expected_operation=spec.operation,
                    params=params,
                    output_kind=spec.output_kind,
                    split=split,
                    difficulty=spec.difficulty,
                    template_id=f"{family}-{template_index + 1}",
                    primary_entity=primary_entity,
                    primary_entity_type=primary_type,
                    task_signature=signature,
                )
            )
    return cases


def _case_entities(case: BenchmarkCase) -> dict[str, set[str]]:
    params = case.params
    drugs = {str(x).lower() for x in params.get("candidates", [])}
    if case.family == "identity":
        drugs.add(str(params.get("identity_generic", "")).lower())
        drugs.add(str(params.get("drug", "")).lower())
    elif params.get("drug"):
        drugs.add(str(params["drug"]).lower())
    if params.get("compound"):
        drugs.add(str(params["compound"]).lower())
    return {
        "drug": {x for x in drugs if x},
        "target": {str(params.get("target", "")).upper()} - {""},
        "gene": {str(params.get("gene", "")).upper()} - {""},
        "condition": {str(params.get("condition", "")).lower()} - {""},
    }


def validate_cases(cases: list[BenchmarkCase]) -> dict[str, Any]:
    if not cases:
        raise ValueError("benchmark is empty")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("benchmark case IDs are not unique")
    if len({case.task_signature for case in cases}) != len(cases):
        raise ValueError("benchmark task signatures are not unique")

    expected_sizes = split_sizes(len(cases))
    observed_sizes = Counter(case.split for case in cases)
    if dict(observed_sizes) != expected_sizes:
        raise ValueError(f"split sizes do not match protocol: {dict(observed_sizes)} != {expected_sizes}")

    for split in expected_sizes:
        counts = Counter(case.family for case in cases if case.split == split)
        if counts and max(counts.values()) - min(counts.values()) > 1:
            raise ValueError(f"family imbalance in {split}: {dict(counts)}")

    actual: dict[str, dict[str, set[str]]] = {
        split: {kind: set() for kind in ("drug", "target", "gene", "condition")}
        for split in expected_sizes
    }
    for case in cases:
        if case.family not in FAMILY_SPECS:
            raise ValueError(f"unknown family {case.family}")
        if case.difficulty not in {"easy", "medium", "hard"}:
            raise ValueError(f"invalid difficulty {case.difficulty}")
        for kind, values in _case_entities(case).items():
            actual[case.split][kind].update(values)

    for kind in ("drug", "target", "gene", "condition"):
        splits = list(expected_sizes)
        for i, a in enumerate(splits):
            for b in splits[i + 1:]:
                overlap = actual[a][kind] & actual[b][kind]
                if overlap:
                    raise ValueError(f"{kind} entity leakage between {a} and {b}: {sorted(overlap)}")

    return benchmark_manifest(cases)


def benchmark_fingerprint(cases: list[BenchmarkCase]) -> str:
    canonical = [asdict(case) for case in sorted(cases, key=lambda c: c.id)]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def benchmark_manifest(cases: list[BenchmarkCase]) -> dict[str, Any]:
    return {
        "schema": BENCHMARK_VERSION,
        "case_count": len(cases),
        "surface_question_count": len({case.question for case in cases}),
        "task_signature_count": len({case.task_signature for case in cases}),
        "fingerprint_sha256": benchmark_fingerprint(cases),
        "split_counts": dict(Counter(case.split for case in cases)),
        "family_counts": dict(Counter(case.family for case in cases)),
        "difficulty_counts": dict(Counter(case.difficulty for case in cases)),
        "source_counts": dict(Counter(source for case in cases for source in case.sources)),
        "entity_partitioning": "entity-disjoint across dev/test/stress for drugs, targets, genes, and conditions",
        "oracle": "independent live API oracle; answers are recomputed at evaluation time",
    }


def as_jsonable(cases: Iterable[BenchmarkCase]):
    return [asdict(case) for case in cases]
