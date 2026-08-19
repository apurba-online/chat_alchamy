from chatalchemy.llm import LLMClient


def test_llm_usage_is_recorded_from_responses_payload():
    client = LLMClient(client=object())
    client._record_usage({"usage": {"input_tokens": 101, "output_tokens": 17, "total_tokens": 118}})
    assert client.last_usage == {"input_tokens": 101, "output_tokens": 17, "total_tokens": 118}


def test_llm_usage_falls_back_to_input_plus_output():
    client = LLMClient(client=object())
    client._record_usage({"usage": {"input_tokens": 9, "output_tokens": 3}})
    assert client.last_usage["total_tokens"] == 12
