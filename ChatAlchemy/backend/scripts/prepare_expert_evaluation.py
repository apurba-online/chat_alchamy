from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

RATING_COLUMNS = [
    "factual_correctness_1_5",
    "evidence_grounding_1_5",
    "completeness_1_5",
    "appropriate_uncertainty_1_5",
    "research_usefulness_1_5",
    "acceptable_research_start_yes_no",
    "reviewer_notes",
]


def _load_system(spec: str) -> dict[str, Any]:
    if "=" not in spec:
        raise SystemExit("--system must use LABEL=path.json")
    label, raw_path = spec.split("=", 1)
    payload = json.loads(Path(raw_path).read_text())
    if "systems" in payload:
        raise SystemExit("Pass a single-system result file to the expert packet generator")
    return {"label": label, "payload": payload}


def _render_response(row: dict[str, Any]) -> str:
    if row.get("answer_text"):
        return str(row["answer_text"])
    if row.get("model_output"):
        return json.dumps(row["model_output"], ensure_ascii=False, sort_keys=True)
    value = row.get("prediction")
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value) if value else "No matching records returned."
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value) if value is not None else "No answer returned."


def _provenance(row: dict[str, Any]) -> str:
    records = row.get("agent_source_records") or []
    pairs = []
    for item in records:
        source = str(item.get("source") or "")
        record = item.get("record")
        if source and record is not None:
            pairs.append(f"{source}:{record}")
    if pairs:
        return "; ".join(sorted(set(pairs)))
    if row.get("evidence_count") is not None:
        return f"retrieved_evidence_count={row.get('evidence_count')}"
    return "No explicit provenance supplied."


def _sample_common_case_ids(systems: list[dict], n_cases: int, seed: int) -> list[str]:
    maps = [
        {str(row["id"]): row for row in system["payload"].get("cases", []) if row.get("id") is not None}
        for system in systems
    ]
    common = set(maps[0])
    for mapping in maps[1:]:
        common &= set(mapping)
    if not common:
        raise SystemExit("No common case IDs exist across the supplied systems")

    first = maps[0]
    by_family: dict[str, list[str]] = defaultdict(list)
    for case_id in sorted(common):
        by_family[str(first[case_id].get("family") or "unknown")].append(case_id)

    rng = random.Random(seed)
    for ids in by_family.values():
        rng.shuffle(ids)
    selected: list[str] = []
    families = sorted(by_family)
    while len(selected) < min(n_cases, len(common)):
        progressed = False
        for family in families:
            if by_family[family] and len(selected) < n_cases:
                selected.append(by_family[family].pop())
                progressed = True
        if not progressed:
            break
    rng.shuffle(selected)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a blinded, reproducible expert-evaluation packet from matched result files.")
    parser.add_argument("--system", action="append", required=True, help="LABEL=path.json; repeat for each system")
    parser.add_argument("--cases", type=int, default=50, help="Number of matched questions; total responses = cases x systems")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--packet", default="benchmark/expert_eval_packet.csv")
    parser.add_argument("--key", default="benchmark/expert_eval_blinding_key.json")
    args = parser.parse_args()

    systems = [_load_system(spec) for spec in args.system]
    if len(systems) < 2:
        raise SystemExit("At least two systems are required for blinded comparison")

    rng = random.Random(args.seed)
    labels = [system["label"] for system in systems]
    shuffled = labels[:]
    rng.shuffle(shuffled)
    code_by_label = {label: chr(ord("A") + index) for index, label in enumerate(shuffled)}
    case_ids = _sample_common_case_ids(systems, args.cases, args.seed)
    maps = {
        system["label"]: {str(row["id"]): row for row in system["payload"].get("cases", [])}
        for system in systems
    }

    packet_rows = []
    item_index = 0
    for case_id in case_ids:
        labels_for_case = labels[:]
        rng.shuffle(labels_for_case)
        for label in labels_for_case:
            row = maps[label][case_id]
            item_index += 1
            packet_rows.append({
                "evaluation_item_id": f"eval-{item_index:04d}",
                "question_id": case_id,
                "family": row.get("family"),
                "question": row.get("question"),
                "system_code": code_by_label[label],
                "response": _render_response(row),
                "provenance_summary": _provenance(row),
                **{column: "" for column in RATING_COLUMNS},
            })

    packet_path = Path(args.packet)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(packet_rows[0])
    with packet_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(packet_rows)

    key = {
        "schema": "ChatAlchemyExpertEvalBlindingKey/v1",
        "seed": args.seed,
        "question_count": len(case_ids),
        "response_count": len(packet_rows),
        "selected_question_ids": case_ids,
        "system_code_map": {code_by_label[label]: label for label in labels},
        "instruction": "Keep this key hidden from raters until all independent scores are locked.",
    }
    key_path = Path(args.key)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key, indent=2) + "\n")
    print(json.dumps({k: key[k] for k in ("question_count", "response_count", "selected_question_ids")}, indent=2))


if __name__ == "__main__":
    main()
