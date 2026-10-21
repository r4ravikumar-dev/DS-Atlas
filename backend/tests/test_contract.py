"""OpenAPI contract: the committed spec (consumed by the frontend type generator) must match the running app."""
import json
from pathlib import Path


def test_openapi_matches_committed_contract():
    from app.main import app
    committed = Path(__file__).resolve().parents[1] / "openapi.json"
    live = app.openapi()
    assert committed.exists(), "run: python scripts/manage.py openapi openapi.json"
    old = json.loads(committed.read_text())
    assert set(old["paths"]) == set(live["paths"]), "API paths changed — regenerate openapi.json and frontend types (npm run api:types)"
    assert old["components"]["schemas"].keys() == live["components"]["schemas"].keys()


def test_every_route_documents_error_envelope():
    from app.main import app
    spec = app.openapi()
    for path, ops in spec["paths"].items():
        if not path.startswith("/api/v1") or path.endswith(("/health", "/ready", "/meta")):
            continue
        for method, op in ops.items():
            assert "422" in op["responses"], f"{method.upper()} {path} lacks a documented validation response"
