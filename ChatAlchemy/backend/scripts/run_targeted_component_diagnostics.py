from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable

from chatalchemy.evaluation import FaultInjectedSource
from chatalchemy.generation import verify_claims
from chatalchemy.models import Claim, EvidenceItem, SourceTrace
from chatalchemy.reasoning import ChatAlchemyEngine


DESIGN_LABEL = "secondary_posthoc_component_diagnostics"


class TraceableFixtureSource:
    name = "Fixture"

    async def close(self):
        return None

    async def traced(self, operation: str, awaitable: Awaitable[list[Any]]):
        start = time.perf_counter()
        try:
            rows = await awaitable
            return rows, SourceTrace(
                source=self.name,
                operation=operation,
                ok=True,
                latency_ms=(time.perf_counter() - start) * 1000,
                result_count=len(rows),
            )
        except Exception as exc:
            return [], SourceTrace(
                source=self.name,
                operation=operation,
                ok=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                result_count=0,
                error=f"{type(exc).__name__}: {exc}",
            )


def ev(subject: str, predicate: str, value: Any, source: str, record_id: str, **qualifiers: Any):
    return EvidenceItem.build(
        subject=subject,
        predicate=predicate,
        value=value,
        source=source,
        source_record_id=record_id,
        qualifiers=qualifiers,
    )


class RxNormFixture(TraceableFixtureSource):
    name = "RxNorm"

    async def resolve(self, drug: str):
        return [ev(drug, "canonical_drug_identity", "acetaminophen", self.name, "161", rxcui="161")]


class DailyMedFixture(TraceableFixtureSource):
    name = "DailyMed"

    async def label_records(self, drug: str, max_results: int = 20):
        return [ev(drug, "label_record", "acetaminophen label", self.name, "spl-1", published_date="2026-01-01", spl_version="1")]


class OpenFDAFixture(TraceableFixtureSource):
    name = "Drugs@FDA/openFDA"

    async def approval_records(self, drug: str, max_results: int = 20):
        return [ev(drug, "fda_application", "NDA000001", self.name, "NDA000001", sponsor="Fixture", brand_names=[drug])]


class ClinicalTrialsFixture(TraceableFixtureSource):
    name = "ClinicalTrials.gov"

    async def search_trials(self, drug: str | None, condition: str | None, phase: str | None, status: str | None, max_results: int = 20):
        return [
            ev(
                drug or "candidate",
                "clinical_trial",
                "NCT00000001",
                self.name,
                "NCT00000001",
                title="Fixture Phase 3 study",
                phases=[phase or "PHASE3"],
                status=status or "RECRUITING",
                conditions=[condition or "condition"],
            )
        ]


class ChEMBLFixture(TraceableFixtureSource):
    name = "ChEMBL"

    async def target_drugs(self, target: str, max_results: int = 20):
        return [ev(target, "target_drug", "gefitinib", self.name, "CHEMBL939", molecule_chembl_id="CHEMBL939", mechanism="fixture", action_type="INHIBITOR")]


class OpenTargetsFixture(TraceableFixtureSource):
    name = "Open Targets"

    async def gene_details(self, gene: str, max_results: int = 20):
        return [
            ev(gene, "gene_identity", gene, self.name, "ENSG00000146648", ensembl_id="ENSG00000146648"),
            ev(gene, "gene_disease_association", "non-small-cell lung cancer", self.name, "EFO_0003060", score=0.9, efo_id="EFO_0003060"),
            ev(gene, "known_drug", "gefitinib", self.name, "CHEMBL939", max_clinical_stage=4, chembl_id="CHEMBL939"),
        ]

    async def disease_genes(self, disease: str, max_results: int = 20):
        return [ev(disease, "disease_gene", "EGFR", self.name, "ENSG00000146648", gene_name="epidermal growth factor receptor", ensembl_id="ENSG00000146648", score=0.9)]


class PubChemFixture(TraceableFixtureSource):
    name = "PubChem"

    async def compound(self, name: str):
        return [ev(name, "compound_properties", {"cid": 123, "canonical_smiles": "CC", "iupac_name": "fixture"}, self.name, "123")]


FAILURE_ROUTES = [
    ("rxnorm", "resolve", "What is the generic identity of Tylenol?", RxNormFixture),
    ("dailymed", "label_records", "What DailyMed label records are available for acetaminophen?", DailyMedFixture),
    ("openfda", "approval_records", "What FDA application information is available for pembrolizumab?", OpenFDAFixture),
    ("clinicaltrials", "search_trials", "List Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.", ClinicalTrialsFixture),
    ("chembl", "target_drugs", "Which drugs target EGFR?", ChEMBLFixture),
    ("opentargets", "gene_details", "What diseases and known drugs are associated with gene EGFR in Open Targets?", OpenTargetsFixture),
    ("opentargets", "disease_genes", "What genes are associated with non-small-cell lung cancer?", OpenTargetsFixture),
    ("pubchem", "compound", "What are the PubChem compound properties of gefitinib?", PubChemFixture),
]


async def failure_semantics_diagnostic():
    rows: list[dict[str, Any]] = []
    for source_key, method, question, factory in FAILURE_ROUTES:
        for mode in ("exception", "empty"):
            fixture = factory()
            injected = FaultInjectedSource(fixture, fail_methods={method}, mode=mode)
            engine = ChatAlchemyEngine(sources={source_key: injected})
            try:
                response = await engine.answer(question)
            finally:
                await engine.close()

            failed_trace = any(not trace.ok for trace in response.traces)
            failure_warning = any(
                "must not be interpreted as evidence of absence" in warning.lower()
                or "failed during" in warning.lower()
                for warning in response.warnings
            )
            qualified_absence = (
                "no conclusion about the absence" in response.answer.lower()
                or "no complete intersection or absence conclusion" in response.answer.lower()
            )
            rows.append(
                {
                    "source": source_key,
                    "operation": method,
                    "mode": mode,
                    "intent": response.plan.intent,
                    "trace_failed": failed_trace,
                    "failure_warning": failure_warning,
                    "qualified_absence": qualified_absence,
                    "claim_count": len(response.claims),
                    "supported_claim_rate": response.supported_claim_rate,
                    "warnings": response.warnings,
                    "answer": response.answer,
                }
            )

    # Cross-source intersection is separately checked because a failed required
    # source must invalidate the complete intersection, even when other sources
    # return evidence.
    cross_sources = {
        "chembl": ChEMBLFixture(),
        "openfda": OpenFDAFixture(),
        "clinicaltrials": ClinicalTrialsFixture(),
    }
    question = "Which drugs targeting EGFR have FDA application records and recruiting Phase 3 trials for non-small-cell lung cancer?"
    for failed_key, method in (("chembl", "target_drugs"), ("openfda", "approval_records"), ("clinicaltrials", "search_trials")):
        sources = dict(cross_sources)
        sources[failed_key] = FaultInjectedSource(sources[failed_key], fail_methods={method}, mode="exception")
        engine = ChatAlchemyEngine(
            sources=sources,
            use_normalization=False,
            use_deterministic_join=True,
        )
        try:
            response = await engine.answer(question)
        finally:
            await engine.close()
        rows.append(
            {
                "source": failed_key,
                "operation": method,
                "mode": "exception_cross_source",
                "intent": response.plan.intent,
                "trace_failed": any(not trace.ok for trace in response.traces),
                "failure_warning": any("must not be interpreted as evidence of absence" in w.lower() for w in response.warnings),
                "qualified_absence": "no complete intersection or absence conclusion" in response.answer.lower(),
                "claim_count": len(response.claims),
                "table_present": response.table is not None,
                "supported_claim_rate": response.supported_claim_rate,
                "warnings": response.warnings,
                "answer": response.answer,
            }
        )

    exception_rows = [r for r in rows if r["mode"].startswith("exception")]
    empty_rows = [r for r in rows if r["mode"] == "empty"]
    summary = {
        "n_total": len(rows),
        "n_exception": len(exception_rows),
        "n_valid_empty": len(empty_rows),
        "exception_failure_trace_rate": statistics.mean(bool(r["trace_failed"]) for r in exception_rows),
        "exception_failure_warning_rate": statistics.mean(bool(r["failure_warning"]) for r in exception_rows),
        "exception_qualified_absence_rate": statistics.mean(bool(r["qualified_absence"]) for r in exception_rows),
        "exception_no_claim_rate": statistics.mean(int(r["claim_count"]) == 0 for r in exception_rows),
        "valid_empty_not_misclassified_as_failure_rate": statistics.mean((not r["trace_failed"]) and (not r["failure_warning"]) for r in empty_rows),
    }
    return {"summary": summary, "cases": rows}


@dataclass(frozen=True)
class JoinScenario:
    candidates: tuple[str, ...]
    fda: frozenset[str]
    trials: frozenset[str]


class ScenarioChEMBL(TraceableFixtureSource):
    name = "ChEMBL"

    def __init__(self, scenario: JoinScenario):
        self.scenario = scenario

    async def target_drugs(self, target: str, max_results: int = 20):
        return [
            ev(target, "target_drug", drug, self.name, f"CHEMBL-{drug}", molecule_chembl_id=f"CHEMBL-{drug}", mechanism="fixture", action_type="INHIBITOR")
            for drug in self.scenario.candidates[:max_results]
        ]


class ScenarioFDA(TraceableFixtureSource):
    name = "Drugs@FDA/openFDA"

    def __init__(self, scenario: JoinScenario):
        self.scenario = scenario

    async def approval_records(self, drug: str, max_results: int = 20):
        if drug not in self.scenario.fda:
            return []
        return [ev(drug, "fda_application", f"NDA-{drug}", self.name, f"NDA-{drug}")]


class ScenarioTrials(TraceableFixtureSource):
    name = "ClinicalTrials.gov"

    def __init__(self, scenario: JoinScenario):
        self.scenario = scenario

    async def search_trials(self, drug: str | None, condition: str | None, phase: str | None, status: str | None, max_results: int = 20):
        if not drug or drug not in self.scenario.trials:
            return []
        return [ev(drug, "clinical_trial", f"NCT-{drug}", self.name, f"NCT-{drug}", phases=[phase or "PHASE3"], status=status or "RECRUITING", conditions=[condition or "condition"])]


def set_scores(pred: set[str], gold: set[str]):
    if not pred and not gold:
        return 1.0, 1.0, 1.0
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else (1.0 if not pred else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def prediction_from_table(response) -> set[str]:
    if response.table is None:
        return set()
    return {str(row[0]) for row in response.table.rows}


async def join_diagnostic(n_cases: int, seed: int):
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    question = "Which drugs targeting EGFR have FDA application records and recruiting Phase 3 trials for non-small-cell lung cancer?"

    for case_index in range(n_cases):
        candidates = tuple(f"drug{case_index:03d}_{j}" for j in range(8))
        # Each case deliberately contains at least one true intersection member,
        # one FDA-only distractor, and one trial-only distractor. Remaining
        # candidates vary deterministically from the fixed seed.
        fda = {candidates[0], candidates[1]}
        trials = {candidates[0], candidates[2]}
        for drug in candidates[3:]:
            state = rng.randrange(4)
            if state in {1, 3}:
                fda.add(drug)
            if state in {2, 3}:
                trials.add(drug)
        scenario = JoinScenario(candidates=candidates, fda=frozenset(fda), trials=frozenset(trials))
        sources_full = {
            "chembl": ScenarioChEMBL(scenario),
            "openfda": ScenarioFDA(scenario),
            "clinicaltrials": ScenarioTrials(scenario),
        }
        sources_ablate = {
            "chembl": ScenarioChEMBL(scenario),
            "openfda": ScenarioFDA(scenario),
            "clinicaltrials": ScenarioTrials(scenario),
        }
        full = ChatAlchemyEngine(sources=sources_full, use_normalization=False, use_deterministic_join=True)
        no_join = ChatAlchemyEngine(sources=sources_ablate, use_normalization=False, use_deterministic_join=False)
        try:
            full_response, ablated_response = await asyncio.gather(full.answer(question), no_join.answer(question))
        finally:
            await asyncio.gather(full.close(), no_join.close())

        gold = set(fda & trials)
        full_pred = prediction_from_table(full_response)
        ablated_pred = prediction_from_table(ablated_response)
        full_p, full_r, full_f1 = set_scores(full_pred, gold)
        abl_p, abl_r, abl_f1 = set_scores(ablated_pred, gold)
        rows.append(
            {
                "id": f"join-{case_index:03d}",
                "candidate_count": len(candidates),
                "gold": sorted(gold),
                "fda_only_or_both": sorted(fda),
                "trial_only_or_both": sorted(trials),
                "full_prediction": sorted(full_pred),
                "no_join_prediction": sorted(ablated_pred),
                "full_exact": full_pred == gold,
                "no_join_exact": ablated_pred == gold,
                "full_precision": full_p,
                "full_recall": full_r,
                "full_f1": full_f1,
                "no_join_precision": abl_p,
                "no_join_recall": abl_r,
                "no_join_f1": abl_f1,
                "no_join_false_positives": len(ablated_pred - gold),
            }
        )

    summary = {
        "n": len(rows),
        "full_exact_set_accuracy": statistics.mean(bool(r["full_exact"]) for r in rows),
        "no_join_exact_set_accuracy": statistics.mean(bool(r["no_join_exact"]) for r in rows),
        "full_mean_precision": statistics.mean(float(r["full_precision"]) for r in rows),
        "full_mean_recall": statistics.mean(float(r["full_recall"]) for r in rows),
        "full_mean_f1": statistics.mean(float(r["full_f1"]) for r in rows),
        "no_join_mean_precision": statistics.mean(float(r["no_join_precision"]) for r in rows),
        "no_join_mean_recall": statistics.mean(float(r["no_join_recall"]) for r in rows),
        "no_join_mean_f1": statistics.mean(float(r["no_join_f1"]) for r in rows),
        "paired_mean_f1_gain_full_minus_no_join": statistics.mean(float(r["full_f1"]) - float(r["no_join_f1"]) for r in rows),
        "no_join_mean_false_positives": statistics.mean(int(r["no_join_false_positives"]) for r in rows),
    }
    return {"summary": summary, "cases": rows}


def link_validation_diagnostic(n_pairs: int):
    evidence = [
        ev("drug-a", "record", "A", "Fixture", "A"),
        ev("drug-b", "record", "B", "Fixture", "B"),
    ]
    claims: list[Claim] = []
    expected: list[bool] = []
    for i in range(n_pairs):
        claims.append(Claim(text=f"valid-{i}", support_ids=[evidence[i % len(evidence)].id]))
        expected.append(True)
        claims.append(Claim(text=f"corrupt-{i}", support_ids=[f"ev_missing_{i:04d}"]))
        expected.append(False)
    verified, _ = verify_claims(claims, evidence)
    valid_idx = [i for i, value in enumerate(expected) if value]
    bad_idx = [i for i, value in enumerate(expected) if not value]
    return {
        "summary": {
            "n_claims": len(claims),
            "n_valid": len(valid_idx),
            "n_corrupted": len(bad_idx),
            "valid_link_accept_rate": statistics.mean(bool(verified[i].supported) for i in valid_idx),
            "corrupted_link_reject_rate": statistics.mean(not bool(verified[i].supported) for i in bad_idx),
        }
    }


async def main():
    parser = argparse.ArgumentParser(description="Run deterministic targeted diagnostics for ChatAlchemy component invariants.")
    parser.add_argument("--join-cases", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/targeted-component-diagnostics.json")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    failure, join = await asyncio.gather(
        failure_semantics_diagnostic(),
        join_diagnostic(args.join_cases, args.seed),
    )
    links = link_validation_diagnostic(100)
    result = {
        "schema": "ChatAlchemyTargetedComponentDiagnostics/v1",
        "design_label": DESIGN_LABEL,
        "interpretation": (
            "These diagnostics were executed after inspection of the primary ablation results. "
            "They are secondary component-invariant diagnostics, not replacements for the frozen confirmatory endpoint."
        ),
        "method": {
            "base_publication_freeze": "f13c3aa8e887b2ddece4badcd29987104ea39c64",
            "diagnostic_commit": os.getenv("GITHUB_SHA"),
            "seed": args.seed,
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "uses_llm": False,
            "uses_live_biomedical_api": False,
        },
        "failure_semantics": failure,
        "deterministic_join": join,
        "evidence_link_validation": links,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "design_label": result["design_label"],
        "failure_semantics": failure["summary"],
        "deterministic_join": join["summary"],
        "evidence_link_validation": links["summary"],
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
