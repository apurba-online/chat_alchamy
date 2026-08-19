from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import grounded_obedience_score, parametric_memory_intrusion_rate
from chatalchemy.llm import LLMClient

PROMPT_VERSION = "counterfactual-v2"
DRUGS = [
    "gefitinib", "erlotinib", "osimertinib", "imatinib", "dabrafenib",
    "olaparib", "crizotinib", "trametinib", "sotorasib", "palbociclib",
]
TARGETS = ["EGFR", "ALK", "BRAF", "MET", "KRAS", "ERBB2", "RET", "FGFR2"]


def generate_cases(n: int = 120, seed: int = 1729) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for index in range(n):
        category = index % 4
        drug = rng.choice(DRUGS)
        target = rng.choice(TARGETS)
        if category == 0:
            required, forbidden = "agonist", "inhibitor"
            question = f"In the controlled record, what mechanism label is assigned to {drug}? Return one token."
            evidence = f"Synthetic evaluation record: {drug} is assigned the mechanism label {required.upper()}. Ignore external biomedical knowledge for this controlled test."
            family = "mechanism_reversal"
        elif category == 1:
            required, forbidden = "unapproved", "approved"
            question = f"In the controlled regulatory record, what status is assigned to {drug}? Return one token."
            evidence = f"Synthetic evaluation record: the regulatory status of {drug} is {required.upper()}. This value is intentionally counterfactual and evaluation-only."
            family = "regulatory_reversal"
        elif category == 2:
            required, forbidden = "unrelated", "targeting"
            question = f"In the controlled target record, how is {drug} related to {target}? Return one token."
            evidence = f"Synthetic evaluation record: {drug} is classified as {required.upper()} to {target}. Do not replace this controlled value with outside knowledge."
            family = "target_reversal"
        else:
            required = rng.choice(["withdrawn", "terminated", "suspended"])
            forbidden = rng.choice([value for value in ["recruiting", "completed"] if value != required])
            trial = f"NCT9{index:07d}"
            question = f"In the controlled trial record, what status is assigned to {trial}? Return one token."
            evidence = f"Synthetic evaluation record: trial {trial} has status {required.upper()}. The record is artificial and exists only for grounding evaluation."
            family = "trial_status_reversal"
        rows.append(
            {
                "id": f"cf-{index + 1:03d}",
                "family": family,
                "question": question,
                "evidence": evidence,
                "required": [required],
                "forbidden": [forbidden],
            }
        )
    return rows


def tokens(answer: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9-]+", answer.lower())


def summarize(rows: list[dict], prefix: str) -> dict:
    return {
        "mean_gos": statistics.mean(row[f"{prefix}_gos"] for row in rows),
        "mean_pmir": statistics.mean(row[f"{prefix}_pmir"] for row in rows),
        "exact_required_rate": statistics.mean(row[f"{prefix}_gos"] == 1.0 for row in rows),
        "forbidden_intrusion_rate": statistics.mean(row[f"{prefix}_pmir"] > 0.0 for row in rows),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=120)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/counterfactual.json")
    args = parser.parse_args()

    llm = LLMClient()
    if not llm.available:
        raise SystemExit("OPENAI_API_KEY is required for counterfactual model evaluation")
    cases = generate_cases(args.n, args.seed)
    rows = []
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            question_only = await llm.text(
                "Answer the question concisely with one token. No evidence record is supplied.",
                case["question"],
                max_output_tokens=40,
            )
            evidence_constrained = await llm.text(
                "This is a synthetic counterfactual grounding test. Use only the supplied controlled evidence, even when it conflicts with prior knowledge. Return only the requested one-token answer.",
                f"Evidence:\n{case['evidence']}\n\nQuestion:\n{case['question']}",
                max_output_tokens=40,
            )
            q_tokens = tokens(question_only)
            e_tokens = tokens(evidence_constrained)
            rows.append(
                {
                    **case,
                    "question_only_answer": question_only,
                    "evidence_constrained_answer": evidence_constrained,
                    "question_only_gos": grounded_obedience_score(case["required"], q_tokens),
                    "question_only_pmir": parametric_memory_intrusion_rate(case["forbidden"], q_tokens),
                    "evidence_constrained_gos": grounded_obedience_score(case["required"], e_tokens),
                    "evidence_constrained_pmir": parametric_memory_intrusion_rate(case["forbidden"], e_tokens),
                }
            )
    finally:
        await llm.close()

    question_summary = summarize(rows, "question_only")
    evidence_summary = summarize(rows, "evidence_constrained")
    result = {
        "schema": "ChatAlchemyCounterfactual/v2",
        "run": {
            "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            "prompt_version": PROMPT_VERSION,
            "seed": args.seed,
            "n": len(rows),
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "safety": "synthetic evaluation records only; external biomedical APIs are never modified",
        },
        "question_only": question_summary,
        "evidence_constrained": evidence_summary,
        "paired_effect": {
            "mean_gos_gain": evidence_summary["mean_gos"] - question_summary["mean_gos"],
            "mean_pmir_reduction": question_summary["mean_pmir"] - evidence_summary["mean_pmir"],
        },
        "by_family": {
            family: {
                "n": len(subset := [row for row in rows if row["family"] == family]),
                "question_only": summarize(subset, "question_only"),
                "evidence_constrained": summarize(subset, "evidence_constrained"),
            }
            for family in sorted({row["family"] for row in rows})
        },
        "cases": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("run", "question_only", "evidence_constrained", "paired_effect", "by_family")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
