from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

FAILURE_CATEGORIES = [
    "routing_error",
    "entity_normalization_error",
    "source_retrieval_failure",
    "source_incompleteness",
    "deterministic_composition_error",
    "temporal_mismatch",
    "conflict_classification_error",
    "generation_error",
    "verification_error",
    "oracle_ambiguity",
    "other",
]


def _is_failure(row: dict) -> bool:
    score = row.get("task_score")
    return (
        (score is not None and float(score) < 0.999999)
        or not bool(row.get("execution_ok", True))
        or bool(row.get("oracle_error"))
        or not bool(row.get("routing_correct", True))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample benchmark failures for blinded/manual taxonomy review.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--n", type=int, default=120)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/failure_review.csv")
    args = parser.parse_args()

    payload = json.loads(Path(args.results).read_text())
    failures = [row for row in payload.get("cases", []) if _is_failure(row)]
    if not failures:
        raise SystemExit("No failures found in the supplied result file")

    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in failures:
        by_family[str(row.get("family") or "unknown")].append(row)
    rng = random.Random(args.seed)
    for group in by_family.values():
        rng.shuffle(group)
    selected: list[dict] = []
    families = sorted(by_family)
    while len(selected) < min(args.n, len(failures)):
        progressed = False
        for family in families:
            if by_family[family] and len(selected) < args.n:
                selected.append(by_family[family].pop())
                progressed = True
        if not progressed:
            break
    rng.shuffle(selected)

    fields = [
        "review_id", "case_id", "family", "difficulty", "question", "oracle", "prediction",
        "answer_text", "planned_intent", "expected_operation", "task_score", "execution_ok",
        "oracle_error", "warnings", "source_traces", "reviewer_failure_category",
        "reviewer_severity_1_3", "reviewer_root_cause_notes",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            writer.writerow({
                "review_id": f"failure-{index:04d}",
                "case_id": row.get("id"),
                "family": row.get("family"),
                "difficulty": row.get("difficulty"),
                "question": row.get("question"),
                "oracle": json.dumps(row.get("oracle"), ensure_ascii=False, sort_keys=True),
                "prediction": json.dumps(row.get("prediction"), ensure_ascii=False, sort_keys=True),
                "answer_text": row.get("answer_text") or "",
                "planned_intent": row.get("planned_intent"),
                "expected_operation": row.get("expected_operation"),
                "task_score": row.get("task_score"),
                "execution_ok": row.get("execution_ok"),
                "oracle_error": row.get("oracle_error") or "",
                "warnings": json.dumps(row.get("warnings") or [], ensure_ascii=False),
                "source_traces": json.dumps(row.get("source_traces") or [], ensure_ascii=False),
                "reviewer_failure_category": "",
                "reviewer_severity_1_3": "",
                "reviewer_root_cause_notes": "",
            })

    print(json.dumps({
        "schema": "ChatAlchemyFailureReviewSample/v1",
        "total_failures": len(failures),
        "sampled": len(selected),
        "seed": args.seed,
        "allowed_categories": FAILURE_CATEGORIES,
        "output": str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
