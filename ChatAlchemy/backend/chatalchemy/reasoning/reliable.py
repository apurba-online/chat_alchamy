from __future__ import annotations

from .engine import ChatAlchemyEngine as _BaseChatAlchemyEngine


class ChatAlchemyEngine(_BaseChatAlchemyEngine):
    """Public engine with failure-aware answer semantics.

    The underlying execution engine deliberately keeps source exceptions inside
    `SourceTrace` objects so callers can inspect partial execution. That is useful
    for research auditing, but it also means a branch can receive `rows=[]` after
    a failed source call. Without this final guard, a failed source can therefore
    be worded as "0 results" or "no records", which incorrectly turns an outage
    into a biomedical absence claim.

    This wrapper leaves successful queries unchanged and qualifies any response
    containing failed source traces before it reaches the API, benchmark harness,
    or other public callers importing `chatalchemy.reasoning.ChatAlchemyEngine`.
    """

    async def answer(self, *args, **kwargs):
        response = await super().answer(*args, **kwargs)
        failed = [trace for trace in response.traces if not trace.ok]
        if not failed:
            return response

        failed_sources = list(dict.fromkeys(trace.source for trace in failed))
        source_text = ", ".join(failed_sources)
        warning = (
            f"Incomplete live evidence: {source_text} failed. "
            "Missing records from this request must not be interpreted as evidence of absence."
        )
        warnings = list(dict.fromkeys([*response.warnings, warning]))

        # Any failed required source makes a deterministic intersection unsafe to
        # assert, even if other sources returned records. Keep provenance/evidence
        # available for inspection, but remove the final claim/table result.
        if response.plan.final_operation == "intersection" or response.plan.intent == "cross_source":
            return response.model_copy(
                update={
                    "answer": (
                        f"I could not complete the cross-source evidence operation because **{source_text}** failed. "
                        "The available records are retained in the evidence trace, but no complete intersection or "
                        "absence conclusion can be established from this request."
                    ),
                    "claims": [],
                    "table": None,
                    "supported_claim_rate": 0.0,
                    "warnings": warnings,
                }
            )

        # If the failed request produced no evidence-backed claim, replace any
        # automatically constructed zero/no-record wording with an explicit
        # unavailable result. This covers the single-source structured routes.
        if not response.claims:
            return response.model_copy(
                update={
                    "answer": (
                        f"I could not complete the live biomedical query because **{source_text}** failed. "
                        "No conclusion about the absence of records can be drawn from this request."
                    ),
                    "table": None,
                    "supported_claim_rate": 0.0,
                    "warnings": warnings,
                }
            )

        # Some multi-call workflows can retain valid evidence from successful
        # calls even when another call fails. Preserve those records but clearly
        # mark the output as partial and remove final claims that might otherwise
        # overstate completeness.
        return response.model_copy(
            update={
                "answer": (
                    f"**Partial result:** one or more live source calls failed ({source_text}). "
                    "Returned records are incomplete, and missing records must not be interpreted as absence.\n\n"
                    + response.answer
                ),
                "claims": [],
                "supported_claim_rate": 0.0,
                "warnings": warnings,
            }
        )
