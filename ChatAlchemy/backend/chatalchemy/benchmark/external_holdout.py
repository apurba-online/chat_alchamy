from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .generator import BenchmarkCase, FAMILY_SPECS

REQUIRED_PARAMS: dict[str, tuple[str, ...]] = {
    "identity": ("drug",),
    "label": ("drug",),
    "approval": ("drug",),
    "trials": ("drug", "condition", "phase"),
    "target": ("target",),
    "cross": ("target", "condition", "phase", "status"),
    "gene": ("gene",),
    "compound": ("compound",),
    "user_approval": ("candidates",),
    "user_trials": ("candidates", "condition", "phase", "status"),
    "user_target": ("candidates", "target"),
}


def holdout_fingerprint(raw_items: list[dict[str, Any]]) -> str:
    payload = json.dumps(raw_items, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_external_holdout(path: str | Path) -> tuple[list[BenchmarkCase], dict[str, Any]]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("external holdout must be a non-empty JSON list")
    cases: list[BenchmarkCase] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"holdout item {index} is not an object")
        case_id = str(item.get("id") or f"external-{index + 1:04d}")
        if case_id in seen_ids:
            raise ValueError(f"duplicate holdout ID {case_id}")
        seen_ids.add(case_id)
        family = str(item.get("family") or "")
        if family not in FAMILY_SPECS:
            raise ValueError(f"unsupported holdout family {family!r} for {case_id}")
        question = str(item.get("question") or "").strip()
        if len(question) < 2:
            raise ValueError(f"missing question for {case_id}")
        params = item.get("params")
        if not isinstance(params, dict):
            raise ValueError(f"params must be an object for {case_id}")
        missing = [name for name in REQUIRED_PARAMS[family] if name not in params]
        if missing:
            raise ValueError(f"missing params for {case_id}: {missing}")
        if family.startswith("user_"):
            candidates = params.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise ValueError(f"user holdout case {case_id} requires a non-empty candidates list")
        spec = FAMILY_SPECS[family]
        task_payload = {"id": case_id, "family": family, "question": question, "params": params}
        signature = hashlib.sha256(json.dumps(task_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        cases.append(BenchmarkCase(
            id=case_id,
            family=family,
            question=question,
            oracle="independent_live_api_oracle",
            sources=list(spec.sources),
            expected_operation=spec.operation,
            params=params,
            output_kind=spec.output_kind,
            split="external",
            difficulty=str(item.get("difficulty") or "external"),
            template_id="external-independent",
            primary_entity=str(item.get("primary_entity") or ""),
            primary_entity_type=str(item.get("primary_entity_type") or "unknown"),
            task_signature=signature,
        ))
    manifest = {
        "schema": "ChatAlchemyExternalHoldout/v1",
        "case_count": len(cases),
        "fingerprint_sha256": holdout_fingerprint(raw),
        "independently_authored": True,
        "answers_embedded": False,
    }
    return cases, manifest
