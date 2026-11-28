"""Endpoints de recursos multimedia, imágenes dinámicas SVG y biblioteca visual personal."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, get_optional_user, require_permission, require_super_admin
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.media.dynamic_visuals import render_structured_diagram_svg, sanitize_svg_markup
from app.modules.media.models import MediaAsset, StudentLibraryItem
from app.modules.media.service import (
    get_local_media_root,
    process_gif_with_ffmpeg,
    sign_media_url,
    validate_media_upload,
    verify_media_signature,
)
from app.modules.media.storage import load_media_bytes, save_media_bytes
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
    signed_url: str | None = None
    dynamic_spec_json: dict | None = None
    has_svg_markup: bool = False


class DynamicVisualCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    education_level: str = "specialized"
    visibility: Literal["public", "institutional", "private"] = "institutional"
    dynamic_spec: dict[str, Any] | None = None
    raw_svg: str | None = None


class MediaAssetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    tags: list[str] | None = None
    visibility: Literal["public", "institutional", "private"] | None = None
    dynamic_spec: dict[str, Any] | None = None
    raw_svg: str | None = None


class AIIllustrationRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=240)
    style: Literal["scientific", "diagram", "illustration"] = "scientific"
    education_level: str = "specialized"
    visibility: Literal["public", "institutional", "private"] = "institutional"


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


def _to_media_out(asset: MediaAsset, *, with_signed_url: bool = True) -> MediaAssetOut:
    signed = sign_media_url(asset.id)[0] if with_signed_url else None
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
        signed_url=signed,
        dynamic_spec_json=asset.dynamic_spec_json,
        has_svg_markup=bool(asset.svg_markup),
    )


def _scope_filter(organization_id: uuid.UUID | None):
    return MediaAsset.organization_id.is_(None) if organization_id is None else (MediaAsset.organization_id == organization_id)


def _list_scoped_media(db: Session, organization_id: uuid.UUID | None) -> list[MediaAssetOut]:
    rows = db.scalars(
        select(MediaAsset)
        .where(_scope_filter(organization_id), MediaAsset.deleted_at.is_(None))
        .order_by(MediaAsset.created_at.desc())
    ).all()
    return [_to_media_out(a) for a in rows]


def _create_scoped_dynamic_visual(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    payload: DynamicVisualCreate,
) -> MediaAssetOut:
    if payload.raw_svg:
        svg_markup = sanitize_svg_markup(payload.raw_svg)
        spec_json = payload.dynamic_spec
    else:
        spec_json = dict(payload.dynamic_spec or {"title": payload.title, "template": "flowchart", "nodes": []})
        spec_json.setdefault("title", payload.title)
        svg_markup, zones = render_structured_diagram_svg(spec_json)
        spec_json["zones"] = zones

    asset_id = uuid.uuid4()
    visibility = "public" if organization_id is None else (
        "institutional" if payload.visibility == "public" else payload.visibility
    )
    asset = MediaAsset(
        id=asset_id,
        organization_id=organization_id,
        uploaded_by=actor_user_id,
        title=payload.title.strip(),
        description=payload.description,
        tags_json=[t.strip() for t in payload.tags if t.strip()],
        education_level=payload.education_level,
        visibility=visibility,
        media_format="svg",
        mime_type="image/svg+xml",
        storage_key=f"dynamic/{organization_id or 'global'}/{asset_id}.svg",
        byte_size=max(1, len(svg_markup.encode("utf-8"))),
        processing_status="ready",
        svg_markup=svg_markup,
        dynamic_spec_json=spec_json,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_media_out(asset)


def _update_scoped_media(
    db: Session,
    *,
    asset_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: MediaAssetUpdate,
) -> MediaAssetOut:
    asset = db.scalar(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            _scope_filter(organization_id),
            MediaAsset.deleted_at.is_(None),
        )
    )
    if not asset:
        raise NotFoundError("Recurso multimedia no encontrado")
    if payload.title is not None:
        asset.title = payload.title.strip()
    if payload.description is not None:
        asset.description = payload.description
    if payload.tags is not None:
        asset.tags_json = [t.strip() for t in payload.tags if t.strip()]
    if payload.visibility is not None:
        asset.visibility = "public" if organization_id is None else (
            "institutional" if payload.visibility == "public" else payload.visibility
        )
    if payload.raw_svg is not None:
        asset.svg_markup = sanitize_svg_markup(payload.raw_svg)
        asset.byte_size = max(1, len(asset.svg_markup.encode("utf-8")))
    elif payload.dynamic_spec is not None:
        spec_json = dict(payload.dynamic_spec)
        spec_json.setdefault("title", asset.title)
        svg_markup, zones = render_structured_diagram_svg(spec_json)
        spec_json["zones"] = zones
        asset.svg_markup = svg_markup
        asset.dynamic_spec_json = spec_json
        asset.byte_size = max(1, len(svg_markup.encode("utf-8")))
    db.commit()
    db.refresh(asset)
    return _to_media_out(asset)


def _delete_scoped_media(
    db: Session,
    *,
    asset_id: uuid.UUID,
    organization_id: uuid.UUID | None,
) -> None:
    asset = db.scalar(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            _scope_filter(organization_id),
            MediaAsset.deleted_at.is_(None),
        )
    )
    if not asset:
        raise NotFoundError("Recurso multimedia no encontrado")
    asset.deleted_at = datetime.now(timezone.utc)
    db.commit()


def _upload_file_impl(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    title: str,
    description: str | None,
    tags: str,
    education_level: str,
    visibility: str,
    file: UploadFile,
) -> MediaAssetOut:
    content = file.file.read()
    mime_type = file.content_type or "application/octet-stream"
    media_format = validate_media_upload(mime_type, len(content))

    asset_id = uuid.uuid4()
    storage_root = get_local_media_root()
    scope_dir = f"orgs/{organization_id}" if organization_id else "global"
    ext = Path(file.filename or "asset.bin").suffix or ".bin"
    raw_key = f"{scope_dir}/{asset_id}{ext}"
    raw_path = storage_root / raw_key
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)

    final_key = raw_key
    final_mime = mime_type
    final_bytes = content
    thumb_key: str | None = None
    svg_markup: str | None = None
    if mime_type.lower() == "image/svg+xml":
        svg_markup = sanitize_svg_markup(content.decode("utf-8", errors="ignore"))
    elif mime_type.lower() == "image/gif":
        webp_key = f"{scope_dir}/{asset_id}.webp"
        thumb_rel = f"{scope_dir}/{asset_id}_thumb.jpg"
        if process_gif_with_ffmpeg(raw_path, storage_root / webp_key, storage_root / thumb_rel):
            final_key = webp_key
            final_mime = "image/webp"
            thumb_key = thumb_rel
            final_bytes = (storage_root / final_key).read_bytes()

    save_media_bytes(final_key, final_bytes, final_mime)

    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]
    eff_visibility = "public" if organization_id is None else ("institutional" if visibility == "public" else visibility)
    asset = MediaAsset(
        id=asset_id,
        organization_id=organization_id,
        uploaded_by=actor_user_id,
        title=title.strip(),
        description=description,
        tags_json=parsed_tags,
        education_level=education_level,
        visibility=eff_visibility,
        media_format=media_format,
        mime_type=final_mime,
        storage_key=final_key,
        thumbnail_key=thumb_key,
        byte_size=max(1, len(final_bytes)),
        processing_status="ready",
        svg_markup=svg_markup,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_media_out(asset)


# ---------------------------------------------------------------------------
# Endpoints Organizacionales (Educador / Coordinador)
# ---------------------------------------------------------------------------
@router.get("/orgs/{org_id}/media", response_model=list[MediaAssetOut])
def list_org_media(
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> list[MediaAssetOut]:
    return _list_scoped_media(db, tenant.organization.id)


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
    return _upload_file_impl(
        db,
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
        title=title,
        description=description,
        tags=tags,
        education_level=education_level,
        visibility=visibility,
        file=file,
    )


@router.post("/orgs/{org_id}/media/dynamic", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def create_org_dynamic_visual(
    payload: DynamicVisualCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _create_scoped_dynamic_visual(
        db, organization_id=tenant.organization.id, actor_user_id=tenant.user.id, payload=payload
    )


@router.patch("/orgs/{org_id}/media/{asset_id}", response_model=MediaAssetOut)
def update_org_media_asset(
    asset_id: uuid.UUID,
    payload: MediaAssetUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _update_scoped_media(db, asset_id=asset_id, organization_id=tenant.organization.id, payload=payload)


@router.delete("/orgs/{org_id}/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_media_asset(
    asset_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    _delete_scoped_media(db, asset_id=asset_id, organization_id=tenant.organization.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Endpoints Globales SuperAdmin
# ---------------------------------------------------------------------------
@router.get("/admin/media", response_model=list[MediaAssetOut])
def list_global_media(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[MediaAssetOut]:
    return _list_scoped_media(db, None)


@router.post("/admin/media", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def upload_global_media_asset(
    title: str = Form(..., min_length=2, max_length=200),
    description: str | None = Form(default=None),
    tags: str = Form(default=""),
    education_level: str = Form(default="specialized"),
    visibility: Literal["public", "institutional", "private"] = Form(default="public"),
    file: UploadFile = File(...),
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _upload_file_impl(
        db,
        organization_id=None,
        actor_user_id=admin.id,
        title=title,
        description=description,
        tags=tags,
        education_level=education_level,
        visibility=visibility,
        file=file,
    )


@router.post("/admin/media/dynamic", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def create_global_dynamic_visual(
    payload: DynamicVisualCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _create_scoped_dynamic_visual(db, organization_id=None, actor_user_id=admin.id, payload=payload)


@router.patch("/admin/media/{asset_id}", response_model=MediaAssetOut)
def update_global_media_asset(
    asset_id: uuid.UUID,
    payload: MediaAssetUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _update_scoped_media(db, asset_id=asset_id, organization_id=None, payload=payload)


@router.delete("/admin/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_media_asset(
    asset_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    _delete_scoped_media(db, asset_id=asset_id, organization_id=None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _create_ai_illustration_impl(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    payload: AIIllustrationRequest,
) -> MediaAssetOut:
    """Genera ilustración real vía proveedor externo opcional o SVG multi-capa enriquecido."""
    settings = get_settings()
    asset_id = uuid.uuid4()
    eff_visibility = "public" if organization_id is None else (
        "institutional" if payload.visibility == "public" else payload.visibility
    )

    if settings.image_ai_provider == "pollinations":
        try:
            prompt_q = f"{payload.topic} {payload.style} educational clean illustration"
            with httpx.Client(timeout=15.0) as client:
                r = client.get(f"https://image.pollinations.ai/prompt/{prompt_q}")
                if r.status_code == 200 and r.content[:4] in {b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"RIFF"}:
                    key = f"ai_img/{organization_id or 'global'}/{asset_id}.png"
                    save_media_bytes(key, r.content, "image/png")
                    asset = MediaAsset(
                        id=asset_id,
                        organization_id=organization_id,
                        uploaded_by=actor_user_id,
                        title=payload.topic[:200],
                        description=f"Ilustración IA ({payload.style})",
                        tags_json=["ia-ilustracion", payload.style],
                        education_level=payload.education_level,
                        visibility=eff_visibility,
                        media_format="png",
                        mime_type="image/png",
                        storage_key=key,
                        byte_size=len(r.content),
                        processing_status="ready",
                    )
                    db.add(asset)
                    db.commit()
                    db.refresh(asset)
                    return _to_media_out(asset)
        except Exception:
            pass

    svg_markup, zones = render_structured_diagram_svg(
        {
            "title": payload.topic,
            "subtitle": f"Lámina ilustrativa ({payload.style})",
            "template": "layers" if payload.style == "scientific" else "hierarchy",
            "nodes": [
                {"id": "z1", "label": payload.topic[:36], "detail": "Concepto visual central", "badge": "1"},
                {"id": "z2", "label": "Estructura clave", "detail": "Componentes principales", "badge": "2"},
                {"id": "z3", "label": "Aplicación", "detail": "Uso práctico en evaluación", "badge": "3"},
            ],
        }
    )
    asset = MediaAsset(
        id=asset_id,
        organization_id=organization_id,
        uploaded_by=actor_user_id,
        title=payload.topic[:200],
        description=f"Ilustración IA ({payload.style})",
        tags_json=["ia-ilustracion", payload.style],
        education_level=payload.education_level,
        visibility=eff_visibility,
        media_format="svg",
        mime_type="image/svg+xml",
        storage_key=f"ai_img/{organization_id or 'global'}/{asset_id}.svg",
        byte_size=max(1, len(svg_markup.encode("utf-8"))),
        processing_status="ready",
        svg_markup=svg_markup,
        dynamic_spec_json={"title": payload.topic, "template": "layers", "zones": zones},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_media_out(asset)


@router.post("/orgs/{org_id}/media/ai-illustration", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def create_org_ai_illustration(
    payload: AIIllustrationRequest,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _create_ai_illustration_impl(
        db, organization_id=tenant.organization.id, actor_user_id=tenant.user.id, payload=payload
    )


@router.post("/admin/media/ai-illustration", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def create_global_ai_illustration(
    payload: AIIllustrationRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> MediaAssetOut:
    return _create_ai_illustration_impl(db, organization_id=None, actor_user_id=admin.id, payload=payload)


# ---------------------------------------------------------------------------
# Lectura segura / URLs firmadas / Biblioteca personal
# ---------------------------------------------------------------------------
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

    if asset.svg_markup:
        return Response(content=asset.svg_markup, media_type="image/svg+xml")

    loaded = load_media_bytes(asset.storage_key)
    if loaded is None:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">'
            f'<rect width="320" height="180" rx="12" fill="#e6f2f5"/>'
            f'<text x="160" y="92" font-family="sans-serif" font-size="14" text-anchor="middle" fill="#0f4c5c">'
            f'{asset.title[:36]}</text></svg>'
        )
        return Response(content=svg, media_type="image/svg+xml")

    return Response(content=loaded, media_type=asset.mime_type)


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
