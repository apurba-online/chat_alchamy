from __future__ import annotations
from typing import Any
def normalize_scalar(v:Any)->str:return " ".join(str(v or "").strip().lower().split())
def set_f1(pred:list[Any],gold:list[Any])->float:
    p={normalize_scalar(x) for x in pred if normalize_scalar(x)};g={normalize_scalar(x) for x in gold if normalize_scalar(x)}
    if not p and not g:return 1.0
    if not p or not g:return 0.0
    tp=len(p&g);precision=tp/len(p);recall=tp/len(g);return 2*precision*recall/(precision+recall) if precision+recall else 0.0
def record_score(pred:dict[str,Any],gold:dict[str,Any])->float:
    keys=set(gold);return sum(normalize_scalar(pred.get(k))==normalize_scalar(gold.get(k)) for k in keys)/len(keys) if keys else 1.0
def score_value(kind:str,pred:Any,gold:Any)->float:
    if kind=="scalar":return float(normalize_scalar(pred)==normalize_scalar(gold))
    if kind=="set":return set_f1(list(pred or []),list(gold or []))
    if kind=="record":return record_score(dict(pred or {}),dict(gold or {}))
    return 0.0
def grounded_obedience_score(expected:list[str],answer_tokens:list[str])->float:
    req={normalize_scalar(x) for x in expected};ans={normalize_scalar(x) for x in answer_tokens};return len(req&ans)/len(req) if req else 1.0
def parametric_memory_intrusion_rate(forbidden:list[str],answer_tokens:list[str])->float:
    bad={normalize_scalar(x) for x in forbidden};ans={normalize_scalar(x) for x in answer_tokens};return len(bad&ans)/len(bad) if bad else 0.0
