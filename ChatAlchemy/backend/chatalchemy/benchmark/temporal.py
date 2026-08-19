from __future__ import annotations

from typing import Any


def _stable(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, default=str)


def compare_runs(earlier: dict[str, Any], later: dict[str, Any]) -> dict[str, Any]:
    before = {row["id"]: row for row in earlier.get("cases", [])}
    after = {row["id"]: row for row in later.get("cases", [])}
    common_ids = sorted(set(before) & set(after))
    comparable = [
        case_id
        for case_id in common_ids
        if before[case_id].get("oracle_available") and after[case_id].get("oracle_available")
    ]
    changed = [case_id for case_id in comparable if _stable(before[case_id].get("oracle")) != _stable(after[case_id].get("oracle"))]
    adapted_scores = [after[case_id].get("task_score") for case_id in changed if after[case_id].get("task_score") is not None]
    stale = [
        case_id
        for case_id in changed
        if _stable(after[case_id].get("prediction")) == _stable(before[case_id].get("oracle"))
    ]
    availability_changed = [
        case_id
        for case_id in common_ids
        if bool(before[case_id].get("oracle_available")) != bool(after[case_id].get("oracle_available"))
    ]
    return {
        "common_cases": len(common_ids),
        "comparable_cases": len(comparable),
        "changed_oracle_cases": len(changed),
        "temporal_adaptation_score": (sum(adapted_scores) / len(adapted_scores)) if adapted_scores else None,
        "stale_prediction_rate": len(stale) / len(changed) if changed else None,
        "availability_changed_cases": len(availability_changed),
        "changed_ids": changed,
        "stale_ids": stale,
        "availability_changed_ids": availability_changed,
    }
