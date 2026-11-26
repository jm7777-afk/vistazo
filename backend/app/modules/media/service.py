"""Servicios multimedia: validación MIME, URLs firmadas, almacenamiento S3/local y FFmpeg."""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ValidationDomainError
from app.modules.media.models import ChallengeMediaAsset, MediaAsset, StudentLibraryItem

ALLOWED_MIME_TO_FORMAT: dict[str, str] = {
    "image/webp": "webp_anim",
    "image/gif": "webp_anim",
    "video/mp4": "mp4_silent",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/svg+xml": "svg",
    "application/pdf": "pdf",
}

MAX_MEDIA_BYTES = 25 * 1024 * 1024  # 25 MB


def get_local_media_root() -> Path:
    root = Path(os.getenv("LOCAL_MEDIA_ROOT", Path(__file__).resolve().parents[3] / "storage_media"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_media_upload(mime_type: str, byte_size: int) -> str:
    """Valida MIME permitido y límite de tamaño devolviendo media_format."""
    fmt = ALLOWED_MIME_TO_FORMAT.get(mime_type.lower().strip())
    if not fmt:
        raise ValidationDomainError(f"Tipo MIME no permitido: {mime_type}", code="invalid_mime_type")
    if byte_size <= 0 or byte_size > MAX_MEDIA_BYTES:
        raise ValidationDomainError("El tamaño del archivo excede el límite permitido (25 MB)", code="invalid_file_size")
    return fmt


def process_gif_with_ffmpeg(input_path: Path, output_webp_path: Path, thumb_path: Path) -> bool:
    """Convierte GIF a WebP animado optimizado y genera miniatura si FFmpeg está disponible."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return False

    try:
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(input_path),
                "-vcodec",
                "libwebp",
                "-filter:v",
                "fps=15,scale='min(720,iw)':-1:flags=lanczos",
                "-lossless",
                "0",
                "-compression_level",
                "4",
                "-q:v",
                "75",
                "-loop",
                "0",
                "-an",
                str(output_webp_path),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(output_webp_path),
                "-vframes",
                "1",
                str(thumb_path),
            ],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return True
    except Exception:
        return False


def sign_media_url(asset_id: uuid.UUID, ttl_seconds: int = 900) -> tuple[str, int]:
    """Genera URL firmada con expiración corta mediante HMAC-SHA256."""
    settings = get_settings()
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{asset_id}:{expires_at}".encode("utf-8")
    sig = hmac.new(settings.jwt_secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"/api/v1/media/file/{asset_id}?exp={expires_at}&sig={sig}", expires_at


def verify_media_signature(asset_id: uuid.UUID, exp: int, sig: str) -> bool:
    """Verifica firma HMAC y ventana de vigencia de la URL firmada."""
    if exp < int(time.time()):
        return False
    settings = get_settings()
    payload = f"{asset_id}:{exp}".encode("utf-8")
    expected = hmac.new(settings.jwt_secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def unlock_lesson_media_for_student(
    db: Session,
    *,
    user_id: uuid.UUID,
    lesson_version_id: uuid.UUID,
    challenge_ids: list[uuid.UUID],
) -> int:
    """Desbloquea recursos multimedia asociados a una lección en la biblioteca personal."""
    if not challenge_ids:
        return 0
    asset_ids = db.scalars(
        select(ChallengeMediaAsset.media_asset_id)
        .join(MediaAsset, ChallengeMediaAsset.media_asset_id == MediaAsset.id)
        .where(
            ChallengeMediaAsset.challenge_id.in_(challenge_ids),
            MediaAsset.deleted_at.is_(None),
            MediaAsset.processing_status == "ready",
        )
        .distinct()
    ).all()

    unlocked = 0
    for asset_id in asset_ids:
        exists = db.scalar(
            select(StudentLibraryItem).where(
                StudentLibraryItem.user_id == user_id,
                StudentLibraryItem.media_asset_id == asset_id,
            )
        )
        if not exists:
            db.add(
                StudentLibraryItem(
                    user_id=user_id,
                    media_asset_id=asset_id,
                    unlocked_from_lesson_version_id=lesson_version_id,
                )
            )
            unlocked += 1
    return unlocked
