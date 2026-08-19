from __future__ import annotations
from collections.abc import Iterable


def set_f1(predicted: Iterable[str], expected: Iterable[str]) -> float:
    p, e = {str(x).casefold() for x in predicted}, {str(x).casefold() for x in expected}
    if not p and not e: return 1.0
    if not p or not e: return 0.0
    tp = len(p & e)
    precision, recall = tp / len(p), tp / len(e)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def grounded_obedience_score(outputs: list[bool]) -> float:
    return sum(outputs) / len(outputs) if outputs else 0.0


def parametric_memory_intrusion_rate(intrusions: list[bool]) -> float:
    return sum(intrusions) / len(intrusions) if intrusions else 0.0
