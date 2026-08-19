from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from chatalchemy.evidence.conflict import assess_pair
from chatalchemy.models import EvidenceItem

LABELS = ("agreement", "complementary", "context_difference", "conflict")


def _safe_json(value: str) -> dict:
    if not value.strip():
        return {}
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("qualifier JSON must be an object")
    return payload


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x in LABELS and y in LABELS]
    if not pairs:
        return None
    observed = sum(x == y for x, y in pairs) / len(pairs)
    ca = Counter(x for x, _ in pairs)
    cb = Counter(y for _, y in pairs)
    expected = sum((ca[label] / len(pairs)) * (cb[label] / len(pairs)) for label in LABELS)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def classification_report(gold: list[str], pred: list[str]) -> dict:
    rows = {}
    f1s = []
    for label in LABELS:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        fp = sum(g != label and p == label for g, p in zip(gold, pred))
        fn = sum(g == label and p != label for g, p in zip(gold, pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        support = sum(g == label for g in gold)
        rows[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        f1s.append(f1)
    return {
        "accuracy": sum(g == p for g, p in zip(gold, pred)) / len(gold) if gold else 0.0,
        "macro_f1": sum(f1s) / len(f1s),
        "per_class": rows,
        "confusion": {f"{g}->{p}": count for (g, p), count in Counter(zip(gold, pred)).items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--out", default="benchmark/conflict-evaluation.json")
    args = parser.parse_args()

    path = Path(args.annotations)
    records = list(csv.DictReader(path.open(newline="")))
    if not records:
        raise SystemExit("Conflict annotation file has no labeled rows")

    gold: list[str] = []
    pred: list[str] = []
    annotator_a: list[str] = []
    annotator_b: list[str] = []
    cases = []
    for row in records:
        label = (row.get("adjudicated_label") or "").strip()
        if label not in LABELS:
            raise ValueError(f"invalid adjudicated label for {row.get('pair_id')}: {label!r}")
        a = EvidenceItem.build(
            subject=row["subject"], predicate=row["predicate"], value=row["value_a"],
            qualifiers=_safe_json(row.get("qualifiers_a_json") or ""), source=row.get("source_a") or "source_a",
            source_record_id=f"{row.get('pair_id')}:a",
        )
        b = EvidenceItem.build(
            subject=row["subject"], predicate=row["predicate"], value=row["value_b"],
            qualifiers=_safe_json(row.get("qualifiers_b_json") or ""), source=row.get("source_b") or "source_b",
            source_record_id=f"{row.get('pair_id')}:b",
        )
        assessment = assess_pair(a, b)
        gold.append(label)
        pred.append(assessment.relation)
        annotator_a.append((row.get("annotator_a_label") or "").strip())
        annotator_b.append((row.get("annotator_b_label") or "").strip())
        cases.append({
            "pair_id": row.get("pair_id"), "gold": label, "prediction": assessment.relation,
            "reason": assessment.reason,
        })

    report = classification_report(gold, pred)
    result = {
        "schema": "ChatAlchemyConflictEvaluation/v1",
        "n": len(cases),
        "labels": list(LABELS),
        "inter_annotator_cohen_kappa": cohen_kappa(annotator_a, annotator_b),
        **report,
        "cases": cases,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("n", "inter_annotator_cohen_kappa", "accuracy", "macro_f1", "per_class")}, indent=2))


if __name__ == "__main__":
    main()
