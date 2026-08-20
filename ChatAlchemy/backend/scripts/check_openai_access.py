from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx

API_BASE = "https://api.openai.com/v1"
DEFAULT_CANDIDATES = [
    "gpt-5.6-luna",
    "gpt-5.4-mini",
    "gpt-5-mini",
    "gpt-5.1-2025-11-13",
]


def _safe_error(response: httpx.Response) -> dict[str, Any]:
    error_type = None
    error_code = None
    try:
        payload = response.json()
        err = payload.get("error") or {}
        error_type = err.get("type")
        error_code = err.get("code")
    except Exception:
        pass
    return {
        "http_status": response.status_code,
        "error_type": error_type,
        "error_code": error_code,
    }


async def probe(candidates: list[str]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=45) as client:
        listed_models: set[str] = set()
        model_list_status = None
        model_list_error = None
        try:
            response = await client.get(f"{API_BASE}/models", headers=headers)
            model_list_status = response.status_code
            if response.is_success:
                listed_models = {
                    str(item.get("id"))
                    for item in (response.json().get("data") or [])
                    if item.get("id")
                }
            else:
                model_list_error = _safe_error(response)
        except Exception as exc:
            model_list_error = {"exception_type": type(exc).__name__}

        for model in candidates:
            row: dict[str, Any] = {
                "requested_model": model,
                "listed_for_project": model in listed_models,
                "response_ok": False,
            }
            try:
                response = await client.post(
                    f"{API_BASE}/responses",
                    headers=headers,
                    json={
                        "model": model,
                        "input": "Reply with exactly OK.",
                        "max_output_tokens": 16,
                    },
                )
                row["http_status"] = response.status_code
                if response.is_success:
                    payload = response.json()
                    row["response_ok"] = True
                    row["returned_model"] = payload.get("model")
                    usage = payload.get("usage") or {}
                    row["usage"] = {
                        "input_tokens": int(usage.get("input_tokens") or 0),
                        "output_tokens": int(usage.get("output_tokens") or 0),
                        "total_tokens": int(usage.get("total_tokens") or 0),
                    }
                else:
                    row.update(_safe_error(response))
            except Exception as exc:
                row["exception_type"] = type(exc).__name__
            results.append(row)

    return {
        "schema": "ChatAlchemyOpenAIAccessProbe/v2",
        "models_endpoint": {
            "http_status": model_list_status,
            "error": model_list_error,
            "listed_model_count": len(listed_models),
            "listed_model_ids": sorted(listed_models),
        },
        "candidates": results,
        "successful_models": [row["requested_model"] for row in results if row.get("response_ok")],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Probe OpenAI model access without writing or printing the API key.")
    parser.add_argument("--model", action="append", dest="models", help="Candidate model ID; repeat as needed")
    parser.add_argument("--out", default="benchmark/openai-access-probe.json")
    args = parser.parse_args()
    result = await probe(args.models or DEFAULT_CANDIDATES)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["successful_models"]:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
