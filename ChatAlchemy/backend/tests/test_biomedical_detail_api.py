import httpx
import pytest
from fastapi import HTTPException

import chatalchemy.app as app_module


@pytest.mark.parametrize(
    "identifier",
    [
        "EFO_0009058",
        "MONDO_0007179",
        "OTAR_0000014",
        "Orphanet_2314",
        "HP_0012531",
        "NCIT_C12345",
        "DOID_1234",
    ],
)
def test_biomedical_detail_api_accepts_supported_ontology_ids(identifier):
    assert app_module.BIOMEDICAL_ID_RE.fullmatch(identifier)


@pytest.mark.parametrize("identifier", ["CHEMBL123", "bad id", "../../etc/passwd", ""])
def test_biomedical_detail_api_rejects_non_disease_ids(identifier):
    assert not app_module.BIOMEDICAL_ID_RE.fullmatch(identifier)


class MissingPubChemSource:
    async def compound(self, name):
        request = httpx.Request("GET", f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}")
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("not found", request=request, response=response)


class FakeEngine:
    sources = {"pubchem": MissingPubChemSource()}


@pytest.mark.asyncio
async def test_missing_pubchem_record_is_not_an_internal_server_error(monkeypatch):
    monkeypatch.setattr(app_module, "engine", FakeEngine())

    with pytest.raises(HTTPException) as exc_info:
        await app_module.biomedical_compound_details("IANALUMAB")

    assert exc_info.value.status_code == 404
    assert "No PubChem structure record" in str(exc_info.value.detail)
