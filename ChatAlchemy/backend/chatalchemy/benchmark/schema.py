from __future__ import annotations
from pydantic import BaseModel,Field
from typing import Any
class BenchmarkCase(BaseModel):
    id:str
    question:str
    intent:str
    oracle:dict[str,Any]
    required_sources:list[str]=Field(default_factory=list)
    tags:list[str]=Field(default_factory=list)
