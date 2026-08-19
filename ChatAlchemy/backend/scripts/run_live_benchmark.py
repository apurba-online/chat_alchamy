from __future__ import annotations

import asyncio
import json
from pathlib import Path
from statistics import mean

import yaml

from chatalchemy.reasoning import ChatAlchemyEngine


async def main() -> None:
    cases = yaml.safe_load(Path("benchmark/live_cases.yaml").read_text())["cases"]
    engine = ChatAlchemyEngine(); rows = []
    try:
        for case in cases:
            response = await engine.answer(case["question"], max_results=10)
            traces = response.traces; successful_sources = {t.source for t in traces if t.ok}; required_sources = set(case["required_sources"])
            routing_ok = response.plan.intent == case["intent"]; execution_ok = required_sources.issubset(successful_sources); latency = sum(t.latency_ms for t in traces)
            rows.append({"id": case["id"], "question": case["question"], "answer": response.answer, "intent": response.plan.intent, "expected_intent": case["intent"], "routing_ok": routing_ok, "execution_ok": execution_ok, "required_sources": sorted(required_sources), "successful_sources": sorted(successful_sources), "supported_claim_rate": response.supported_claim_rate, "evidence_count": len(response.evidence), "conflict_count": sum(1 for c in response.conflicts if c.relation == "conflict"), "source_latency_ms": latency, "warnings": response.warnings, "traces": [t.model_dump() for t in traces]})
    finally:
        await engine.close()
    summary = {"n": len(rows), "routing_accuracy": mean(float(r["routing_ok"]) for r in rows), "live_execution_success": mean(float(r["execution_ok"]) for r in rows), "mean_supported_claim_rate": mean(r["supported_claim_rate"] for r in rows), "mean_source_latency_ms": mean(r["source_latency_ms"] for r in rows)}
    payload = {"summary": summary, "cases": rows}; Path("live_benchmark_results.json").write_text(json.dumps(payload, indent=2)); print(json.dumps(payload, indent=2))
    if summary["routing_accuracy"] < 1.0: raise SystemExit("Typed planner failed at least one benchmark routing contract.")
    if summary["live_execution_success"] < 0.8: raise SystemExit("Too many required live-source executions failed.")

if __name__ == "__main__":
    asyncio.run(main())
