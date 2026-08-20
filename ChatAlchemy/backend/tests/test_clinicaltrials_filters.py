import pytest

from chatalchemy.sources.clinicaltrials import ClinicalTrialsSource


def _study(nct: str, *, phase: str = "PHASE3", status: str = "RECRUITING") -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": f"Study {nct}"},
            "designModule": {"phases": [phase]},
            "statusModule": {"overallStatus": status},
            "conditionsModule": {"conditions": ["Non-Small Cell Lung Cancer"]},
            "armsInterventionsModule": {"interventions": [{"name": "pembrolizumab"}]},
        }
    }


class CapturingTrials(ClinicalTrialsSource):
    def __init__(self):
        self._owns_client = False
        self.calls = []

    async def _get(self, url, params=None, attempts=3):
        self.calls.append(dict(params or {}))
        token = (params or {}).get("pageToken")
        if token == "NEXT":
            return {"studies": [_study("NCT0002")]}
        return {"studies": [_study("NCT0001")], "nextPageToken": "NEXT"}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_phase_and_status_are_sent_before_result_truncation():
    source = CapturingTrials()
    rows = await source.search_trials(
        "pembrolizumab",
        "non-small-cell lung cancer",
        "PHASE3",
        "RECRUITING",
        max_results=1,
    )

    assert [row.value for row in rows] == ["NCT0001"]
    params = source.calls[0]
    assert params["query.intr"] == "pembrolizumab"
    assert params["query.cond"] == "non-small-cell lung cancer"
    assert params["filter.overallStatus"] == "RECRUITING"
    assert params["filter.advanced"] == "AREA[Phase]PHASE3"


@pytest.mark.asyncio
async def test_trials_pagination_collects_until_requested_result_limit():
    source = CapturingTrials()
    rows = await source.search_trials(
        "pembrolizumab",
        "non-small-cell lung cancer",
        "PHASE3",
        "RECRUITING",
        max_results=2,
    )

    assert [row.value for row in rows] == ["NCT0001", "NCT0002"]
    assert len(source.calls) == 2
    assert source.calls[1]["pageToken"] == "NEXT"


class LocallyBroadenedTrials(ClinicalTrialsSource):
    def __init__(self):
        self._owns_client = False

    async def _get(self, url, params=None, attempts=3):
        # Even if an upstream filter unexpectedly broadens results, local record
        # validation must prevent a wrong phase/status from being returned.
        return {
            "studies": [
                _study("NCT-WRONG-PHASE", phase="PHASE2", status="RECRUITING"),
                _study("NCT-WRONG-STATUS", phase="PHASE3", status="COMPLETED"),
                _study("NCT-RIGHT", phase="PHASE3", status="RECRUITING"),
            ]
        }

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_trial_filters_are_rechecked_locally():
    source = LocallyBroadenedTrials()
    rows = await source.search_trials(
        "pembrolizumab",
        "non-small-cell lung cancer",
        "PHASE3",
        "RECRUITING",
        max_results=20,
    )
    assert [row.value for row in rows] == ["NCT-RIGHT"]
