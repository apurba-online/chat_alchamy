import pytest

from chatalchemy.benchmark import LiveOracle


def _study(nct: str, *, phase: str = "PHASE3", status: str = "RECRUITING") -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct},
            "designModule": {"phases": [phase]},
            "statusModule": {"overallStatus": status},
        }
    }


class CapturingOracle(LiveOracle):
    def __init__(self):
        self.client = None
        self.calls = []

    async def _get(self, url, params=None, attempts=3):
        self.calls.append(dict(params or {}))
        if (params or {}).get("pageToken") == "NEXT":
            return {"studies": [_study("NCT0002")]}
        return {"studies": [_study("NCT0001")], "nextPageToken": "NEXT"}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_direct_oracle_applies_phase_status_before_pagination():
    oracle = CapturingOracle()
    values, records = await oracle._trials(
        "pembrolizumab",
        "non-small-cell lung cancer",
        "PHASE3",
        "RECRUITING",
        limit=2,
    )

    assert values == ["NCT0001", "NCT0002"]
    assert [record["record"] for record in records] == values
    assert oracle.calls[0]["filter.overallStatus"] == "RECRUITING"
    assert oracle.calls[0]["filter.advanced"] == "AREA[Phase]PHASE3"
    assert oracle.calls[1]["pageToken"] == "NEXT"


class BroadOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, url, params=None, attempts=3):
        return {
            "studies": [
                _study("NCT-P2", phase="PHASE2"),
                _study("NCT-DONE", status="COMPLETED"),
                _study("NCT-OK"),
            ]
        }

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_direct_oracle_rechecks_trial_phase_and_status_locally():
    oracle = BroadOracle()
    values, _ = await oracle._trials(
        "pembrolizumab",
        "non-small-cell lung cancer",
        "PHASE3",
        "RECRUITING",
        limit=20,
    )
    assert values == ["NCT-OK"]
