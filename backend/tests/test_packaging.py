"""Deployment packaging: Vercel installs from pyproject.toml, the Docker image from requirements.txt — they must agree."""
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_pyproject_dependencies_match_requirements():
    req = sorted(l.strip() for l in (BACKEND / "requirements.txt").read_text().splitlines() if l.strip() and not l.startswith("#"))
    proj = tomllib.loads((BACKEND / "pyproject.toml").read_text())
    assert sorted(proj["project"]["dependencies"]) == req
    assert proj["tool"]["vercel"]["entrypoint"] == "app.main:app"


def test_storage_defaults_to_tmp_on_vercel(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("STORAGE_DIR", raising=False)
    assert str(Settings().storage_dir).startswith("/tmp/")
