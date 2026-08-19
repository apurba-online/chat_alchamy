from __future__ import annotations
import asyncio,time
from typing import Any
import httpx
from ..models import SourceTrace
class LiveSource:
    name="source";base_url=""
    def __init__(self,client:httpx.AsyncClient|None=None,timeout:float=20.0):
        self._owns_client=client is None;self.client=client or httpx.AsyncClient(timeout=timeout,headers={"User-Agent":"ChatAlchemy-Live/1.0","Cache-Control":"no-cache"},follow_redirects=True)
    async def close(self):
        if self._owns_client: await self.client.aclose()
    async def _get(self,url:str,*,params:dict[str,Any]|None=None,attempts:int=3)->dict[str,Any]:
        last=None
        for attempt in range(attempts):
            try:
                r=await self.client.get(url,params=params)
                if r.status_code==429 and attempt<attempts-1:await asyncio.sleep(0.5*(2**attempt));continue
                r.raise_for_status();return r.json()
            except Exception as exc:
                last=exc
                if attempt<attempts-1:await asyncio.sleep(0.3*(2**attempt))
        assert last is not None;raise last
    async def _post_json(self,url:str,payload:dict[str,Any],attempts:int=3)->dict[str,Any]:
        last=None
        for attempt in range(attempts):
            try:
                r=await self.client.post(url,json=payload)
                if r.status_code==429 and attempt<attempts-1:await asyncio.sleep(0.5*(2**attempt));continue
                r.raise_for_status();return r.json()
            except Exception as exc:
                last=exc
                if attempt<attempts-1:await asyncio.sleep(0.3*(2**attempt))
        assert last is not None;raise last
    async def traced(self,operation:str,coro):
        started=time.perf_counter()
        try:
            result=await coro;count=len(result) if isinstance(result,list) else int(bool(result));return result,SourceTrace(source=self.name,operation=operation,ok=True,latency_ms=(time.perf_counter()-started)*1000,result_count=count)
        except Exception as exc:return [],SourceTrace(source=self.name,operation=operation,ok=False,latency_ms=(time.perf_counter()-started)*1000,error=str(exc))
