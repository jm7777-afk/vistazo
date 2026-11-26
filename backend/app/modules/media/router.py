"""Endpoints de recursos multimedia con URLs firmadas y biblioteca visual personal."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, get_optional_user, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.media.models import MediaAsset, StudentLibraryItem
from app.modules.media.service import (
    get_local_media_root,
    process_gif_with_ffmpeg,
    sign_media_url,
    validate_media_upload,
    verify_media_signature,
)
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["media"])


class MediaAssetOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    title: str
    description: str | None
    tags: list[str]
    education_level: str
    visibility: str
    media_format: str
    mime_type: str
    byte_size: int
    processing_status: str


class SignedUrlOut(BaseModel):
    asset_id: uuid.UUID
    signed_url: str
    expires_at: int


class LibraryItemOut(BaseModel):
    library_item_id: uuid.UUID
    asset_id: uuid.UUID
    title: str
    description: str | None
    tags: list[str]
    media_format: str
    is_favorite: bool
    flash_reviews_count: int
    signed_url: str
    unlocked_at: datetime


@router.post("/orgs/{org_id}/media", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def upload_media_asset(
    title: str = Form(..., min_length=2, max_length=200),
    description: str | None = Form(default=None),
    tags: str = Form(default=""),
    education_level: str = Form(default="rescue"),
    visibility: Literal["public", "institutional", "private"] = Form(default="institutional"),
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    content = file.file.read()
    mime_type = file.content_type or "application/octet-stream"
    media_format = validate_media_upload(mime_type, len(content))

    asset_id = uuid.uuid4()
    storage_root = get_local_media_root()
    ext = Path(file.filename or "asset.bin").suffix or ".bin"
    raw_key = f"orgs/{tenant.organization.id}/{asset_id}{ext}"
    raw_path = storage_root / raw_key
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)

    final_key = raw_key
    final_mime = mime_type
    thumb_key: str | None = None
    if mime_type.lower() == "image/gif":
        webp_key = f"orgs/{tenant.organization.id}/{asset_id}.webp"
        thumb_rel = f"orgs/{tenant.organization.id}/{asset_id}_thumb.jpg"
        if process_gif_with_ffmpeg(raw_path, storage_root / webp_key, storage_root / thumb_rel):
            final_key = webp_key
            final_mime = "image/webp"
            thumb_key = thumb_rel

    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
    asset = MediaAsset(
        id=asset_id,
        organization_id=tenant.organization.id,
        uploaded_by=tenant.user.id,
        title=title.strip(),
        description=description,
        tags_json=parsed_tags,
        education_level=education_level,
        visibility=visibility,
        media_format=media_format,
        mime_type=final_mime,
        storage_key=final_key,
        thumbnail_key=thumb_key,
        byte_size=(storage_root / final_key).stat().st_size,
        processing_status="ready",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return MediaAssetOut(
        id=asset.id,
        organization_id=asset.organization_id,
        title=asset.title,
        description=asset.description,
        tags=asset.tags_json,
        education_level=asset.education_level,
        visibility=asset.visibility,
        media_format=asset.media_format,
        mime_type=asset.mime_type,
        byte_size=asset.byte_size,
        processing_status=asset.processing_status,
    )


@router.get("/media/{asset_id}/signed-url", response_model=SignedUrlOut)
def get_signed_media_url(
    asset_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> SignedUrlOut:
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.deleted_at.is_(None)))
    if not asset:
        raise NotFoundError("Recurso multimedia no encontrado")

    if asset.visibility != "public":
        if not current_user:
            raise ForbiddenError("Recurso restringido a miembros autorizados")
        if not current_user.is_super_admin:
            if asset.visibility == "private" and asset.uploaded_by != current_user.id:
                unlocked = db.scalar(
                    select(StudentLibraryItem).where(
                        StudentLibraryItem.user_id == current_user.id,
                        StudentLibraryItem.media_asset_id == asset.id,
                    )
                )
                if not unlocked:
                    raise ForbiddenError("No tienes acceso a este recurso privado")
            elif asset.organization_id is not None:
                member = db.scalar(
                    select(OrganizationMember).where(
                        OrganizationMember.organization_id == asset.organization_id,
                        OrganizationMember.user_id == current_user.id,
                        OrganizationMember.deleted_at.is_(None),
                        OrganizationMember.status == "active",
                    )
                )
                if not member:
                    raise ForbiddenError("No perteneces a la organización propietaria del recurso")

    url, exp = sign_media_url(asset.id)
    return SignedUrlOut(asset_id=asset.id, signed_url=url, expires_at=exp)


@router.get("/media/file/{asset_id}")
def serve_signed_media_file(
    asset_id: uuid.UUID,
    exp: int = Query(...),
    sig: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_media_signature(asset_id, exp, sig):
        raise UnauthorizedError("URL firmada inválida o expirada")

    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.deleted_at.is_(None)))
    if not asset:
        raise NotFoundError("Recurso multimedia no encontrado")

    file_path = get_local_media_root() / asset.storage_key
    if not file_path.exists():
        # Devuelve SVG placeholder limpio si fue creado solo en metadata (ej. seed)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">'
            f'<rect width="320" height="180" rx="12" fill="#e6f2f5"/>'
            f'<text x="160" y="92" font-family="sans-serif" font-size="14" text-anchor="middle" fill="#0f4c5c">'
            f'{asset.title[:36]}</text></svg>'
        )
        return Response(content=svg, media_type="image/svg+xml")

    return Response(content=file_path.read_bytes(), media_type=asset.mime_type)


@router.get("/library/me", response_model=list[LibraryItemOut])
def my_visual_library(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LibraryItemOut]:
    rows = db.execute(
        select(StudentLibraryItem, MediaAsset)
        .join(MediaAsset, StudentLibraryItem.media_asset_id == MediaAsset.id)
        .where(StudentLibraryItem.user_id == current_user.id, MediaAsset.deleted_at.is_(None))
        .order_by(StudentLibraryItem.is_favorite.desc(), StudentLibraryItem.unlocked_at.desc())
    ).all()

    return [
        LibraryItemOut(
            library_item_id=item.id,
            asset_id=asset.id,
            title=asset.title,
            description=asset.description,
            tags=asset.tags_json,
            media_format=asset.media_format,
            is_favorite=item.is_favorite,
            flash_reviews_count=item.flash_reviews_count,
            signed_url=sign_media_url(asset.id)[0],
            unlocked_at=item.unlocked_at,
        )
        for item, asset in rows
    ]


@router.post("/library/flash-review/{asset_id}", response_model=LibraryItemOut)
def record_flash_training_review(
    asset_id: uuid.UUID,
    toggle_favorite: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LibraryItemOut:
    row = db.execute(
        select(StudentLibraryItem, MediaAsset)
        .join(MediaAsset, StudentLibraryItem.media_asset_id == MediaAsset.id)
        .where(
            StudentLibraryItem.user_id == current_user.id,
            StudentLibraryItem.media_asset_id == asset_id,
            MediaAsset.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Recurso no desbloqueado en tu biblioteca personal")

    item, asset = row
    item.flash_reviews_count += 1
    item.last_reviewed_at = datetime.now(timezone.utc)
    if toggle_favorite is not None:
        item.is_favorite = toggle_favorite
    db.commit()
    db.refresh(item)
    return LibraryItemOut(
        library_item_id=item.id,
        asset_id=asset.id,
        title=asset.title,
        description=asset.description,
        tags=asset.tags_json,
        media_format=asset.media_format,
        is_favorite=item.is_favorite,
        flash_reviews_count=item.flash_reviews_count,
        signed_url=sign_media_url(asset.id)[0],
        unlocked_at=item.unlocked_at,
    )
