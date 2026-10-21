"""Object storage abstraction. Default: local filesystem under STORAGE_DIR.
Swap `LocalStorage` for an S3-compatible implementation with the same interface in production."""
from __future__ import annotations

from pathlib import Path

from ..core.config import get_settings


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def put(self, key: str, data: bytes) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_bytes(data)
        return key

    def put_file(self, key: str, src: Path) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(src.read_bytes())
        return key

    def path(self, key: str) -> Path:
        return self._path(key)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


_storage: LocalStorage | None = None


def storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(Path(get_settings().storage_dir) / "objects")
    return _storage
