"""Private file storage (docs/04 §7).

Paths: {society_id}/{kind}/{yyyy}/{mm}/{uuid}.{ext}. The local backend is for development and
tests; the Supabase backend calls the Storage REST API with the service-role key, which never
leaves the backend.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

import httpx

from app.config import get_settings


@dataclass(frozen=True)
class StoredFile:
    path: str
    sha256: str
    size_bytes: int


class Storage(Protocol):
    async def put(self, path: str, data: bytes, mime: str) -> None: ...

    async def get(self, path: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    async def put(self, path: str, data: bytes, mime: str) -> None:
        target = self.root / path
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, data)

    async def get(self, path: str) -> bytes:
        return await asyncio.to_thread((self.root / path).read_bytes)


class SupabaseStorage:
    # Endpoint per the Supabase Storage REST API; verify against current docs on first deploy.
    def __init__(self, url: str, service_key: str, bucket: str) -> None:
        self.base = f"{url.rstrip('/')}/storage/v1/object/{bucket}"
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}

    async def put(self, path: str, data: bytes, mime: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base}/{path}",
                content=data,
                headers={**self.headers, "Content-Type": mime, "x-upsert": "false"},
            )
            response.raise_for_status()

    async def get(self, path: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base}/{path}", headers=self.headers)
            response.raise_for_status()
            return response.content


def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Supabase storage needs SUPABASE_URL and the service-role key")
        return SupabaseStorage(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        )
    return LocalStorage(settings.local_storage_dir)


async def store(society_id: UUID, kind: str, ext: str, data: bytes, mime: str) -> StoredFile:
    now = datetime.now(UTC)
    path = f"{society_id}/{kind}/{now:%Y}/{now:%m}/{uuid4()}.{ext}"
    await get_storage().put(path, data, mime)
    return StoredFile(path=path, sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
