from __future__ import annotations

import json
import os
import re
import httpx

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class ServerLLM:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    @property
    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    async def complete(self, messages: list[dict[str, str]], *, system: str, temperature: float = 0.0) -> str:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured on the server")
        payload = {"model": self.model, "temperature": temperature, "messages": [{"role": "system", "content": system}, *messages]}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(OPENAI_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    async def extract_biomedical_entities(self, text: str):
        prompt = "Extract biomedical entities from the supplied scientific text. Return ONLY valid JSON with keys summary, genes, diseases, drugs. Do not invent entities not supported by the text."
        content = await self.complete([{"role": "user", "content": text[:50000]}], system=prompt, temperature=0)
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            raise RuntimeError("Model did not return JSON")
        return json.loads(match.group(0))

    async def suggest_questions(self, context: str) -> list[str]:
        content = await self.complete([{"role": "user", "content": context[:20000]}], system="Return ONLY a JSON array of 3 concise pharmaceutical research questions grounded in the provided analysis.", temperature=0.2)
        match = re.search(r"\[.*\]", content, re.S)
        if not match:
            return []
        return [str(x) for x in json.loads(match.group(0))[:3]]
