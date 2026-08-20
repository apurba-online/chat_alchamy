from fastapi.testclient import TestClient

from chatalchemy.app import MAX_DATA_UPLOAD_BYTES, MAX_DOCUMENT_UPLOAD_BYTES, app


def test_health_exposes_release_operational_limits_and_request_id():
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-Request-ID": "release-check-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "release-check-123"
    payload = response.json()
    assert payload["direct_upload_limit_bytes"] == 4 * 1024 * 1024
    assert payload["instance_concurrency_limit"] >= 1
    assert payload["research_use_only"] is True


def test_invalid_request_id_is_replaced_not_reflected():
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-Request-ID": "bad request id with spaces"})

    request_id = response.headers["X-Request-ID"]
    assert request_id != "bad request id with spaces"
    assert len(request_id) == 32


def test_direct_upload_limits_stay_below_vercel_function_payload_ceiling():
    assert MAX_DATA_UPLOAD_BYTES == 4 * 1024 * 1024
    assert MAX_DOCUMENT_UPLOAD_BYTES == 4 * 1024 * 1024
    assert MAX_DATA_UPLOAD_BYTES < int(4.5 * 1024 * 1024)
    assert MAX_DOCUMENT_UPLOAD_BYTES < int(4.5 * 1024 * 1024)
