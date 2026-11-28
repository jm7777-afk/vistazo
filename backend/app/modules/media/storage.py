"""Adaptador de almacenamiento persistente en Supabase Storage con fallback local seguro."""

from __future__ import annotations

from pathlib import Path

import httpx

from app.core.config import get_settings
from app.modules.media.service import get_local_media_root


def is_supabase_storage_configured() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def save_media_bytes(storage_key: str, content: bytes, mime_type: str) -> str:
    """Guarda bytes en Supabase Storage si está configurado, o en disco local."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{storage_key.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": mime_type,
            "x-upsert": "true",
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, headers=headers, content=content)
                resp.raise_for_status()
            return "supabase"
        except Exception:
            # Si Supabase Storage falla temporalmente, guarda respaldo local
            pass

    target = get_local_media_root() / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return "local"


def load_media_bytes(storage_key: str) -> bytes | None:
    """Lee bytes desde Supabase Storage o desde almacenamiento local."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{storage_key.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            pass

    local_path: Path = get_local_media_root() / storage_key
    if local_path.exists():
        return local_path.read_bytes()
    return None
