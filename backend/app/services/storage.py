"""Object storage for raw snapshots and exports.

* `local` (default): files under STORAGE_DIR. Used in development and by single-host deployments.
* `supabase`: a private Supabase Storage bucket, so the API functions and the background worker on Vercel share files.
  Calls use the service-role key from server-side settings only; downloads are short-lived signed URLs issued after the
  API has authorized the administrator, with `download=` forcing an attachment (stored content is never rendered inline).
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi.responses import FileResponse, RedirectResponse, Response

from ..core.config import get_settings

INERT = "application/octet-stream"


class StorageError(RuntimeError):
    pass


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
        return self.put(key, src.read_bytes())

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()

    def download_response(self, key: str, filename: str, media_type: str = INERT, headers: dict[str, str] | None = None) -> Response:
        return FileResponse(self._path(key), filename=filename, media_type=media_type, headers=headers)


class SupabaseStorage:
    """Private Supabase Storage bucket over its HTTP API (same endpoints as the official storage clients)."""

    def __init__(self, url: str, key: str, bucket: str, ttl: int = 60, client: httpx.Client | None = None):
        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.ttl = ttl
        self._client = client or httpx.Client(timeout=30)
        self._headers = {"Authorization": f"Bearer {key}", "apikey": key}

    @staticmethod
    def _check_key(key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("invalid storage key")
        return quote(key, safe="/")

    def _obj(self, key: str) -> str:
        return f"{self.base}/object/{self.bucket}/{self._check_key(key)}"

    def _fail(self, what: str, r: httpx.Response) -> StorageError:
        # Response bodies are not echoed: they could contain request details.
        return StorageError(f"Supabase Storage {what} failed (HTTP {r.status_code})")

    def put(self, key: str, data: bytes) -> str:
        # Keys are content-addressed or job-scoped, so an existing object is the same object: do not overwrite.
        r = self._client.post(self._obj(key), content=data, headers={**self._headers, "Content-Type": INERT, "x-upsert": "false"})
        if r.status_code in (200, 201):
            return key
        if r.status_code in (400, 409) and ("exist" in r.text.lower() or "duplicate" in r.text.lower()):
            return key
        raise self._fail("upload", r)

    def put_file(self, key: str, src: Path) -> str:
        return self.put(key, src.read_bytes())

    def read(self, key: str) -> bytes:
        r = self._client.get(self._obj(key), headers=self._headers)
        if r.status_code != 200:
            raise self._fail("download", r)
        return r.content

    def exists(self, key: str) -> bool:
        r = self._client.head(self._obj(key), headers=self._headers)
        if r.status_code == 200:
            return True
        if r.status_code in (400, 404):
            return False
        raise self._fail("lookup", r)

    def delete(self, key: str) -> None:
        r = self._client.request("DELETE", f"{self.base}/object/{self.bucket}", json={"prefixes": [key]}, headers=self._headers)
        if r.status_code not in (200, 404):
            raise self._fail("delete", r)

    def signed_url(self, key: str, filename: str) -> str:
        r = self._client.post(f"{self.base}/object/sign/{self.bucket}/{self._check_key(key)}",
                              json={"expiresIn": self.ttl, "download": filename}, headers=self._headers)
        if r.status_code != 200:
            raise self._fail("signing", r)
        rel = r.json().get("signedURL") or r.json().get("signedUrl")
        if not rel:
            raise StorageError("Supabase Storage signing returned no URL")
        url = rel if rel.startswith("http") else f"{self.base}/{rel.lstrip('/')}"
        return f"{url}&download={quote(filename)}" if "download=" not in url else url

    def download_response(self, key: str, filename: str, media_type: str = INERT, headers: dict[str, str] | None = None) -> Response:
        # The caller has already authorized the request; the link is single-object and expires in `ttl` seconds.
        return RedirectResponse(self.signed_url(key, filename), status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    def ensure_bucket(self) -> str:
        """Create the private bucket if missing (idempotent). Used by `manage.py setup-storage`."""
        r = self._client.get(f"{self.base}/bucket/{self.bucket}", headers=self._headers)
        if r.status_code == 200:
            if r.json().get("public"):
                raise StorageError(f"Bucket '{self.bucket}' is public; make it private in Supabase before use.")
            return "exists"
        r = self._client.post(f"{self.base}/bucket", json={"id": self.bucket, "name": self.bucket, "public": False}, headers=self._headers)
        if r.status_code in (200, 201):
            return "created"
        raise self._fail("bucket creation", r)


_storage: LocalStorage | SupabaseStorage | None = None


def storage() -> LocalStorage | SupabaseStorage:
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_backend == "supabase":
            if not s.supabase_url or not s.supabase_service_role_key:
                raise StorageError("STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
            _storage = SupabaseStorage(s.supabase_url, s.supabase_service_role_key.get_secret_value(), s.supabase_storage_bucket,
                                       s.signed_url_ttl_seconds)
        else:
            _storage = LocalStorage(Path(s.storage_dir) / "objects")
    return _storage
