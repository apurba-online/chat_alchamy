import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vercel_configuration_is_release_safe():
    config = json.loads((ROOT / "vercel.json").read_text())

    ignore_command = config.get("ignoreCommand")
    assert isinstance(ignore_command, str) and ignore_command
    # Vercel's root-level schema currently limits ignoreCommand to 256 chars.
    assert len(ignore_command) <= 256
    assert ignore_command == "bash scripts/vercel-ignore.sh"
    assert (ROOT / "scripts" / "vercel-ignore.sh").exists()

    function_config = (config.get("functions") or {}).get("api/**/*.py") or {}
    assert function_config.get("maxDuration") == 60
    assert "backend/tests" in str(function_config.get("excludeFiles"))

    header_sets = config.get("headers") or []
    global_headers = next(item for item in header_sets if item.get("source") == "/(.*)")
    headers = {item["key"]: item["value"] for item in global_headers["headers"]}
    assert "Content-Security-Policy" in headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"

    api_headers = next(item for item in header_sets if item.get("source") == "/api/(.*)")
    api = {item["key"]: item["value"] for item in api_headers["headers"]}
    assert "no-store" in api.get("Cache-Control", "")
