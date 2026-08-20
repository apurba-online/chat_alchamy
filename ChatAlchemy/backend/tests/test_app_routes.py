from io import BytesIO

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from chatalchemy.app import _translate_upstream_error, app


def test_health_and_data_routes():
    with TestClient(app) as client:
        health = client.get('/api/health')
        assert health.status_code == 200
        body = health.json()
        assert body['local_pharma_database'] is False
        assert body['research_use_only'] is True
        assert body['version'] == '1.1.0'
        assert len(body['live_sources']) == 7
        assert 'claim-level support verification' in body['capabilities']
        assert isinstance(body['server_llm_configured'], bool)

        parsed = client.post(
            '/api/data/parse',
            files={'file': ('tiny.csv', b'drug,score\na,1\nb,2\n', 'text/csv')},
        )
        assert parsed.status_code == 200
        assert parsed.json()['rows'][1]['drug'] == 'b'

        exported = client.post(
            '/api/data/export_xlsx',
            json={'headers': ['drug', 'score'], 'rows': [['a', 1], ['b', 2]]},
        )
        assert exported.status_code == 200
        workbook = load_workbook(BytesIO(exported.content), read_only=True)
        assert list(workbook.active.values) == [('drug', 'score'), ('a', 1), ('b', 2)]


def test_title_and_biomedical_extract_without_browser_secret():
    with TestClient(app) as client:
        title = client.post('/api/title', json={'text': 'EGFR inhibitors for lung cancer'})
        assert title.status_code == 200 and title.json()['title']
        biomedical = client.post(
            '/api/biomedical/extract',
            json={'text': 'EGFR and TP53 were evaluated in lung cancer.'},
        )
        assert biomedical.status_code == 200 and 'EGFR' in biomedical.json()['genes']


def test_openai_access_failure_is_mapped_to_clean_service_error():
    request = httpx.Request('POST', 'https://api.openai.com/v1/responses')
    response = httpx.Response(403, request=request)
    upstream = httpx.HTTPStatusError('forbidden', request=request, response=response)

    with pytest.raises(HTTPException) as caught:
        _translate_upstream_error(upstream)

    assert caught.value.status_code == 503
    assert 'temporarily unavailable' in str(caught.value.detail).lower()
