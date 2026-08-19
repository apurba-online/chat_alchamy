from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chatalchemy.benchmark import EvaluationOracle, generate_cases, score_value, select_cases, validate_cases
from chatalchemy.evaluation import UnrestrictedToolAgent
from chatalchemy.llm import LLMClient
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction as chatalchemy_prediction
from scripts.run_live_benchmark import user_evidence

PROMPT_VERSION = "model-baseline-v4"
PUBLIC_BENCHMARK_N = 1500


def _schema(case) -> dict[str, Any]:
    if case.output_kind == "scalar":
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {"value": {"type": ["string", "null"]}},
            "required": ["value"],
        }
    if case.output_kind == "record":
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "cid": {"type": ["string", "null"]},
                "canonical_smiles": {"type": ["string", "null"]},
                "iupac_name": {"type": ["string", "null"]},
            },
            "required": ["cid", "canonical_smiles", "iupac_name"],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
        "required": ["items"],
    }


def _prediction(case, payload: dict[str, Any]):
    if case.output_kind == "scalar":
        value = payload.get("value")
        return str(value).lower() if value is not None else None
    if case.output_kind == "record":
        return {
            "cid": str(payload.get("cid") or ""),
            "canonical_smiles": payload.get("canonical_smiles"),
            "iupac_name": payload.get("iupac_name"),
        }
    return sorted({str(item).strip().lower() for item in payload.get("items", []) if str(item).strip()})


def _task_format(case) -> str:
    if case.family == "label":
        return "Return DailyMed SPL set IDs only."
    if case.family == "approval":
        return "Return Drugs@FDA/openFDA application numbers only."
    if case.family == "trials":
        return "Return NCT identifiers only."
    if case.family == "target":
        return "Return drug or molecule names only."
    if case.family == "gene":
        return "Return entries formatted as gene_disease_association:<disease> or known_drug:<drug>."
    if case.family in {"cross", "user_approval", "user_trials", "user_target"}:
        return "Return qualifying drug names only."
    if case.family == "identity":
        return "Return the canonical generic ingredient name."
    if case.family == "compound":
        return "Return PubChem CID, canonical SMILES, and IUPAC name."
    return "Return the requested structured answer."


def _evidence_payload(response) -> list[dict[str, Any]]:
    return [
        {
            "subject": item.subject,
            "predicate": item.predicate,
            "value": item.value,
            "qualifiers": item.qualifiers,
            "source": item.source,
            "source_record_id": item.source_record_id,
            "retrieved_at": item.retrieved_at,
        }
        for item in response.evidence
    ]


def _add_usage(total: dict[str, int], usage: dict[str, int]) -> None:
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        total[key] = total.get(key, 0) + int(usage.get(key, 0))


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = [float(row["task_score"]) for row in rows if row.get("task_score") is not None]
    full = [float(row["chatalchemy_task_score"]) for row in rows if row.get("chatalchemy_task_score") is not None]
    paired = [
        (float(row["chatalchemy_task_score"]), float(row["task_score"]))
        for row in rows
        if row.get("chatalchemy_task_score") is not None and row.get("task_score") is not None
    ]
    return {
        "n": len(rows),
        "oracle_coverage": statistics.mean(bool(row["oracle_available"]) for row in rows) if rows else 0.0,
        "baseline_mean_task_score": statistics.mean(baseline) if baseline else None,
        "chatalchemy_mean_task_score": statistics.mean(full) if full else None,
        "paired_n": len(paired),
        "paired_mean_chatalchemy_minus_baseline": statistics.mean(a - b for a, b in paired) if paired else None,
        "median_baseline_latency_ms": statistics.median(float(row["baseline_latency_ms"]) for row in rows) if rows else 0.0,
        "model_error_rate": statistics.mean(bool(row.get("model_error")) for row in rows) if rows else 0.0,
        "retrieval_error_rate": statistics.mean(bool(row.get("retrieval_error")) for row in rows) if rows else 0.0,
        "mean_model_input_tokens": statistics.mean(int(row["model_usage"].get("input_tokens", 0)) for row in rows) if rows else 0.0,
        "mean_model_output_tokens": statistics.mean(int(row["model_usage"].get("output_tokens", 0)) for row in rows) if rows else 0.0,
        "mean_model_total_tokens": statistics.mean(int(row["model_usage"].get("total_tokens", 0)) for row in rows) if rows else 0.0,
        "mean_tool_calls": statistics.mean(int(row.get("tool_call_count", 0)) for row in rows) if rows else 0.0,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["llm_only", "same_retrieval_llm", "unrestricted_tool_agent"], required=True)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--split", choices=["dev", "test", "stress", "all"], default="test")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard", "all"], default="all")
    parser.add_argument("--limit", type=int, default=150, help="0 means all selected frozen benchmark cases")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--max-tool-steps", type=int, default=40, help="Generous ceiling matched to the order of work in ChatAlchemy's hardest cross-source path")
    parser.add_argument("--oracle-snapshot", default=None)
    parser.add_argument("--out", default="benchmark/model-baseline.json")
    args = parser.parse_args()

    os.environ["OPENAI_MODEL"] = args.model
    llm = LLMClient()
    if not llm.available:
        raise SystemExit("OPENAI_API_KEY must be configured on the runner; no browser credential is supported")

    all_cases = generate_cases(PUBLIC_BENCHMARK_N, args.seed)
    manifest = validate_cases(all_cases)
    cases = select_cases(
        all_cases,
        split=args.split,
        difficulty=args.difficulty,
        limit=None if args.limit == 0 else args.limit,
        num_shards=args.num_shards,
        shard_index=args.shard_index,
    )
    if not cases:
        raise SystemExit("No cases matched the requested filters")

    oracle = EvaluationOracle(
        benchmark_fingerprint=manifest["fingerprint_sha256"],
        snapshot_path=args.oracle_snapshot,
    )
    engine = ChatAlchemyEngine()
    tool_source_engine = ChatAlchemyEngine() if args.mode == "unrestricted_tool_agent" else None
    tool_agent = (
        UnrestrictedToolAgent(llm, tool_source_engine.sources, max_steps=args.max_tool_steps, max_results=args.max_results)
        if tool_source_engine is not None
        else None
    )
    rows: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            case_started = time.perf_counter()
            gold, oracle_error = await oracle.get(case)

            retrieval_error = None
            full_response = None
            try:
                full_response = await engine.answer(
                    case.question,
                    max_results=args.max_results,
                    user_evidence=user_evidence(case),
                )
            except Exception as exc:
                retrieval_error = f"{type(exc).__name__}: {exc}"

            full_pred = chatalchemy_prediction(case, full_response) if full_response is not None else None
            full_score = score_value(gold.kind, full_pred, gold.value) if gold is not None and full_pred is not None else None

            evidence = None
            tool_trace: list[dict[str, Any]] = []
            usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            if args.mode == "same_retrieval_llm":
                evidence = _evidence_payload(full_response) if full_response is not None else []
            elif args.mode == "unrestricted_tool_agent":
                assert tool_agent is not None
                try:
                    retrieval = await tool_agent.retrieve(
                        case.question,
                        uploaded_candidates=case.params.get("candidates") if case.family.startswith("user_") else None,
                    )
                    evidence = UnrestrictedToolAgent._evidence_payload(retrieval["evidence"])
                    tool_trace = retrieval["trace"]
                    _add_usage(usage, retrieval["usage"])
                except Exception as exc:
                    retrieval_error = f"{type(exc).__name__}: {exc}"
                    evidence = []

            instructions = (
                "You are being evaluated on biomedical evidence reasoning. "
                "Return only the requested JSON fields. Do not explain your answer. "
                + _task_format(case)
            )
            if args.mode in {"same_retrieval_llm", "unrestricted_tool_agent"}:
                instructions += " Use only the supplied retrieved evidence and uploaded candidates; do not invent source records."

            model_input = {
                "question": case.question,
                "output_kind": case.output_kind,
                "uploaded_candidates": case.params.get("candidates") if case.family.startswith("user_") else None,
                "evidence": evidence,
            }
            model_error = None
            raw_output: dict[str, Any] = {}
            model_started = time.perf_counter()
            try:
                raw_output = await llm.json(
                    instructions,
                    json.dumps(model_input, default=str),
                    "benchmark_answer",
                    _schema(case),
                )
                _add_usage(usage, llm.last_usage)
            except Exception as exc:
                model_error = f"{type(exc).__name__}: {exc}"
            baseline_latency = (time.perf_counter() - model_started) * 1000

            pred = _prediction(case, raw_output) if not model_error else None
            score = score_value(gold.kind, pred, gold.value) if gold is not None and pred is not None else None
            rows.append(
                {
                    "id": case.id,
                    "task_signature": case.task_signature,
                    "split": case.split,
                    "difficulty": case.difficulty,
                    "family": case.family,
                    "question": case.question,
                    "task_score": score,
                    "chatalchemy_task_score": full_score,
                    "oracle_available": gold is not None,
                    "oracle_error": oracle_error,
                    "oracle": gold.value if gold is not None else None,
                    "prediction": pred,
                    "chatalchemy_prediction": full_pred,
                    "model_output": raw_output,
                    "model_error": model_error,
                    "retrieval_error": retrieval_error,
                    "evidence_count": len(evidence or []),
                    "tool_call_count": sum(not step.get("decision", {}).get("done", False) and step.get("decision", {}).get("tool") != "none" for step in tool_trace),
                    "tool_trace": tool_trace,
                    "model_usage": usage,
                    "baseline_latency_ms": baseline_latency,
                    "total_case_latency_ms": (time.perf_counter() - case_started) * 1000,
                }
            )
    finally:
        await oracle.close()
        await llm.close()
        await engine.close()
        if tool_source_engine is not None:
            await tool_source_engine.close()

    finished = datetime.now(timezone.utc)
    by_family = {
        family: _aggregate([row for row in rows if row["family"] == family])
        for family in sorted({row["family"] for row in rows})
    }
    result = {
        "schema": "ChatAlchemyModelBaselineRun/v4",
        "run": {
            "mode": args.mode,
            "model": args.model,
            "prompt_version": PROMPT_VERSION,
            "seed": args.seed,
            "split_filter": args.split,
            "difficulty_filter": args.difficulty,
            "limit": args.limit,
            "num_shards": args.num_shards,
            "shard_index": args.shard_index,
            "max_results": args.max_results,
            "max_tool_steps": args.max_tool_steps if args.mode == "unrestricted_tool_agent" else 0,
            "started_at_utc": started.isoformat(),
            "finished_at_utc": finished.isoformat(),
            "git_sha": os.getenv("GITHUB_SHA"),
            **oracle.metadata(),
        },
        "benchmark": {**manifest, "seed": args.seed},
        "summary": _aggregate(rows),
        "by_family": by_family,
        "cases": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "summary": result["summary"], "by_family": by_family}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
