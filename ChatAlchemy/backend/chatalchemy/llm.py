from __future__ import annotations
import json,os,re
from typing import Any
import httpx
class LLMClient:
    def __init__(self,client:httpx.AsyncClient|None=None):self.api_key=os.getenv("OPENAI_API_KEY");self.model=os.getenv("OPENAI_MODEL","gpt-5-mini");self.client=client or httpx.AsyncClient(timeout=60);self._owns=client is None
    @property
    def available(self):return bool(self.api_key)
    async def close(self):
        if self._owns:await self.client.aclose()
    async def text(self,instructions:str,input_text:str,*,max_output_tokens:int=900)->str:
        if not self.api_key:raise RuntimeError("OPENAI_API_KEY is not configured on the server")
        r=await self.client.post("https://api.openai.com/v1/responses",json={"model":self.model,"instructions":instructions,"input":input_text,"max_output_tokens":max_output_tokens},headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"});r.raise_for_status();data=r.json()
        if data.get("output_text"):return data["output_text"]
        return "\n".join(c["text"] for item in data.get("output") or [] for c in item.get("content") or [] if c.get("type")=="output_text" and c.get("text")).strip()
    async def json(self,instructions:str,input_text:str,schema_name:str,schema:dict[str,Any])->dict[str,Any]:
        if not self.api_key:raise RuntimeError("OPENAI_API_KEY is not configured on the server")
        payload={"model":self.model,"instructions":instructions,"input":input_text,"text":{"format":{"type":"json_schema","name":schema_name,"schema":schema,"strict":True}},"max_output_tokens":1200};r=await self.client.post("https://api.openai.com/v1/responses",json=payload,headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"});r.raise_for_status();data=r.json();text=data.get("output_text")
        if not text:
            for item in data.get("output") or []:
                for c in item.get("content") or []:
                    if c.get("type")=="output_text":text=c.get("text");break
        return json.loads(text or "{}")
def fallback_title(text:str)->str:
    words=[w for w in re.findall(r"[A-Za-z0-9-]+",text) if len(w)>2][:4];return " ".join(words).title() or "New Chat"
