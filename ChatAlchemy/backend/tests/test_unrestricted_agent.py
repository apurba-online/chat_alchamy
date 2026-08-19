import pytest

from chatalchemy.evaluation import UnrestrictedToolAgent
from chatalchemy.models import EvidenceItem


class FakeLLM:
    def __init__(self):
        self.calls = 0
        self.last_usage = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}

    async def json(self, instructions, input_text, schema_name, schema):
        self.calls += 1
        if self.calls == 1:
            return {
                "done": False,
                "tool": "dailymed",
                "drug": "gefitinib",
                "target": None,
                "condition": None,
                "phase": None,
                "status": None,
                "gene": None,
                "compound": None,
                "reason": "Need a live label record",
            }
        return {
            "done": True,
            "tool": "none",
            "drug": None,
            "target": None,
            "condition": None,
            "phase": None,
            "status": None,
            "gene": None,
            "compound": None,
            "reason": "Enough evidence",
        }


class FakeDailyMed:
    async def label_records(self, drug, max_results=20):
        return [
            EvidenceItem.build(
                subject=drug,
                predicate="dailymed_label_record",
                value="Example label",
                source="DailyMed",
                source_record_id="set-1",
            )
        ]


@pytest.mark.asyncio
async def test_unrestricted_agent_chooses_tools_without_rule_planner():
    llm = FakeLLM()
    agent = UnrestrictedToolAgent(llm, {"dailymed": FakeDailyMed()}, max_steps=3)
    result = await agent.retrieve("Find DailyMed labels for gefitinib")
    assert len(result["evidence"]) == 1
    assert result["evidence"][0].source_record_id == "set-1"
    assert result["trace"][0]["decision"]["tool"] == "dailymed"
    assert result["trace"][-1]["decision"]["done"] is True
    assert result["usage"] == {"input_tokens": 20, "output_tokens": 4, "total_tokens": 24}
