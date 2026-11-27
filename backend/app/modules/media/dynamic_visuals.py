"""Motor de imágenes dinámicas SVG seguras y generador de zonas interactivas."""

from __future__ import annotations

import html
import re
from typing import Any

from app.core.exceptions import ValidationDomainError

DANGEROUS_TAG_RE = re.compile(
    r"<\s*/?\s*(script|foreignObject|iframe|object|embed|link|meta|style)[^>]*>.*?(?:<\s*/\s*\1\s*>)?",
    re.IGNORECASE | re.DOTALL,
)
EVENT_ATTR_RE = re.compile(r"\s+on[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
JS_URI_RE = re.compile(r"(javascript|data\s*:\s*text/html)\s*:", re.IGNORECASE)


def sanitize_svg_markup(raw_svg: str) -> str:
    """Elimina scripts, eventos inline y etiquetas riesgosas manteniendo SVG limpio."""
    cleaned = raw_svg.strip()
    if "<svg" not in cleaned.lower():
        raise ValidationDomainError("El contenido SVG debe incluir un elemento raíz <svg>", code="invalid_svg")
    cleaned = DANGEROUS_TAG_RE.sub("", cleaned)
    cleaned = EVENT_ATTR_RE.sub("", cleaned)
    cleaned = JS_URI_RE.sub("blocked:", cleaned)
    if "<svg" not in cleaned.lower():
        raise ValidationDomainError("El SVG no pasó la validación de seguridad", code="invalid_svg")
    return cleaned


def _esc(value: Any, limit: int = 64) -> str:
    text = str(value or "").strip()[:limit]
    return html.escape(text, quote=True)


def _wrap_lines(text: str, max_chars: int = 20, max_lines: int = 2) -> list[str]:
    words = text.strip().split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word[:max_chars]
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines or [text[:max_chars]]


def render_structured_diagram_svg(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Renderiza una infografía SVG profesional (800x450) y retorna zonas normalizadas."""
    template = str(spec.get("template") or "flowchart").lower()
    if template not in {"cycle", "flowchart", "hierarchy", "comparison", "layers"}:
        template = "flowchart"

    title = _esc(spec.get("title") or "Diagrama Conceptual", 72)
    subtitle = _esc(spec.get("subtitle") or "Mapa visual dinámico para aprendizaje y repaso", 96)
    raw_nodes = spec.get("nodes") or []
    nodes: list[dict[str, str]] = []
    for idx, item in enumerate(raw_nodes[:6]):
        if isinstance(item, dict):
            nodes.append(
                {
                    "id": str(item.get("id") or f"z{idx + 1}")[:32],
                    "label": str(item.get("label") or f"Concepto {idx + 1}")[:60],
                    "detail": str(item.get("detail") or "")[:90],
                    "badge": str(item.get("badge") or f"{idx + 1}")[:12],
                }
            )
    if len(nodes) < 2:
        nodes = [
            {"id": "z1", "label": "Concepto base", "detail": "Fundamento inicial", "badge": "1"},
            {"id": "z2", "label": "Aplicación clave", "detail": "Ejecución práctica", "badge": "2"},
            {"id": "z3", "label": "Verificación", "detail": "Control de dominio", "badge": "3"},
        ]

    palette = ["#0f4c5c", "#1e6091", "#047857", "#d97706", "#4f46e5", "#0e7490"]
    shapes: list[str] = []
    zones: list[dict[str, Any]] = []
    w_box, h_box = 800, 450

    if template == "flowchart":
        count = len(nodes)
        cols = min(count, 3)
        rows = 1 if count <= 3 else 2
        card_w = 210 if cols == 3 else 280
        card_h = 112 if rows == 2 else 150
        x_gap = (w_box - cols * card_w) / (cols + 1)
        y_start = 115 if rows == 2 else 160
        y_gap = 40
        for idx, node in enumerate(nodes):
            r = idx // cols
            c = idx % cols
            x = x_gap + c * (card_w + x_gap)
            y = y_start + r * (card_h + y_gap)
            color = palette[idx % len(palette)]
            shapes.append(_render_card(x, y, card_w, card_h, node, color))
            zones.append(
                {
                    "id": node["id"],
                    "shape": "rect",
                    "x": round(x / w_box, 3),
                    "y": round(y / h_box, 3),
                    "w": round(card_w / w_box, 3),
                    "h": round(card_h / h_box, 3),
                    "label": node["label"][:80],
                }
            )
            if c < cols - 1 and idx + 1 < count:
                ax1 = x + card_w + 4
                ax2 = x + card_w + x_gap - 6
                ay = y + card_h / 2
                shapes.append(
                    f'<line x1="{ax1:.1f}" y1="{ay:.1f}" x2="{ax2:.1f}" y2="{ay:.1f}" '
                    f'stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />'
                )

    elif template == "cycle":
        import math

        cx, cy, radius = 400.0, 255.0, 128.0
        n = len(nodes)
        card_w, card_h = 176.0, 82.0
        shapes.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#cbd5e1" '
            f'stroke-width="2.5" stroke-dasharray="7 6" />'
        )
        shapes.append(
            f'<circle cx="{cx}" cy="{cy}" r="52" fill="#e6f2f5" stroke="#0f4c5c" stroke-width="2" />'
        )
        shapes.append(
            f'<text x="{cx}" y="{cy + 4}" font-family="system-ui,sans-serif" font-size="13" font-weight="700" '
            f'text-anchor="middle" fill="#0f4c5c">CICLO</text>'
        )
        for idx, node in enumerate(nodes):
            angle = -math.pi / 2 + (2 * math.pi * idx / n)
            nx = cx + radius * math.cos(angle) - card_w / 2
            ny = cy + radius * math.sin(angle) - card_h / 2
            nx = max(18.0, min(w_box - card_w - 18.0, nx))
            ny = max(92.0, min(h_box - card_h - 14.0, ny))
            color = palette[idx % len(palette)]
            shapes.append(_render_card(nx, ny, card_w, card_h, node, color))
            zones.append(
                {
                    "id": node["id"],
                    "shape": "rect",
                    "x": round(nx / w_box, 3),
                    "y": round(ny / h_box, 3),
                    "w": round(card_w / w_box, 3),
                    "h": round(card_h / h_box, 3),
                    "label": node["label"][:80],
                }
            )

    elif template == "hierarchy":
        root = nodes[0]
        children = nodes[1:] or [root]
        rw, rh = 280.0, 78.0
        rx, ry = (w_box - rw) / 2, 102.0
        shapes.append(_render_card(rx, ry, rw, rh, root, palette[0]))
        zones.append(
            {
                "id": root["id"],
                "shape": "rect",
                "x": round(rx / w_box, 3),
                "y": round(ry / h_box, 3),
                "w": round(rw / w_box, 3),
                "h": round(rh / h_box, 3),
                "label": root["label"][:80],
            }
        )
        n_ch = len(children)
        cw = min(210.0, (w_box - 40.0 - (n_ch - 1) * 18.0) / n_ch)
        ch = 128.0
        total_w = n_ch * cw + (n_ch - 1) * 18.0
        start_x = (w_box - total_w) / 2
        cy = 248.0
        for idx, node in enumerate(children):
            x = start_x + idx * (cw + 18.0)
            shapes.append(
                f'<path d="M 400 {ry + rh:.1f} L 400 {ry + rh + 28:.1f} L {x + cw / 2:.1f} {ry + rh + 28:.1f} L {x + cw / 2:.1f} {cy - 4:.1f}" '
                f'fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />'
            )
            shapes.append(_render_card(x, cy, cw, ch, node, palette[(idx + 1) % len(palette)]))
            zones.append(
                {
                    "id": node["id"],
                    "shape": "rect",
                    "x": round(x / w_box, 3),
                    "y": round(cy / h_box, 3),
                    "w": round(cw / w_box, 3),
                    "h": round(ch / h_box, 3),
                    "label": node["label"][:80],
                }
            )

    elif template == "comparison":
        cols = min(len(nodes), 3)
        shown = nodes[:3]
        gap = 24.0
        cw = (w_box - 64.0 - (cols - 1) * gap) / cols
        ch = 290.0
        cy = 112.0
        for idx, node in enumerate(shown):
            x = 32.0 + idx * (cw + gap)
            shapes.append(_render_card(x, cy, cw, ch, node, palette[idx % len(palette)], tall=True))
            zones.append(
                {
                    "id": node["id"],
                    "shape": "rect",
                    "x": round(x / w_box, 3),
                    "y": round(cy / h_box, 3),
                    "w": round(cw / w_box, 3),
                    "h": round(ch / h_box, 3),
                    "label": node["label"][:80],
                }
            )

    else:  # layers / pirámide de prioridades
        n = min(len(nodes), 5)
        layer_h = 54.0
        y0 = 108.0
        for idx, node in enumerate(nodes[:n]):
            shrink = idx * 44.0
            lw = max(320.0, 680.0 - shrink)
            lx = (w_box - lw) / 2
            ly = y0 + idx * (layer_h + 10.0)
            color = palette[idx % len(palette)]
            shapes.append(
                f'<rect x="{lx:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{layer_h:.1f}" rx="12" '
                f'fill="#ffffff" stroke="{color}" stroke-width="2.2" />'
            )
            shapes.append(
                f'<rect x="{lx:.1f}" y="{ly:.1f}" width="12" height="{layer_h:.1f}" rx="6" fill="{color}" />'
            )
            shapes.append(
                f'<text x="{lx + 26:.1f}" y="{ly + 24:.1f}" font-family="system-ui,sans-serif" font-size="14" '
                f'font-weight="700" fill="#0f172a">{_esc(node["badge"] + ". " + node["label"], 56)}</text>'
            )
            if node["detail"]:
                shapes.append(
                    f'<text x="{lx + 26:.1f}" y="{ly + 42:.1f}" font-family="system-ui,sans-serif" font-size="12" '
                    f'fill="#475569">{_esc(node["detail"], 74)}</text>'
                )
            zones.append(
                {
                    "id": node["id"],
                    "shape": "rect",
                    "x": round(lx / w_box, 3),
                    "y": round(ly / h_box, 3),
                    "w": round(lw / w_box, 3),
                    "h": round(layer_h / h_box, 3),
                    "label": node["label"][:80],
                }
            )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_box} {h_box}" width="100%" height="100%">'
        '<defs>'
        '<linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#f8fafc"/>'
        '<stop offset="100%" stop-color="#e6f2f5"/>'
        '</linearGradient>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b"/>'
        '</marker>'
        '</defs>'
        f'<rect width="{w_box}" height="{h_box}" rx="18" fill="url(#bgGrad)"/>'
        f'<rect x="20" y="18" width="{w_box - 40}" height="64" rx="12" fill="#0f4c5c"/>'
        f'<text x="38" y="45" font-family="system-ui,sans-serif" font-size="19" font-weight="800" fill="#ffffff">{title}</text>'
        f'<text x="38" y="67" font-family="system-ui,sans-serif" font-size="12.5" fill="#cbd5e1">{subtitle}</text>'
        + "".join(shapes)
        + "</svg>"
    )
    return sanitize_svg_markup(svg), zones


def _render_card(
    x: float,
    y: float,
    w: float,
    h: float,
    node: dict[str, str],
    color: str,
    *,
    tall: bool = False,
) -> str:
    label_lines = _wrap_lines(node["label"], max_chars=22 if w >= 200 else 17, max_lines=2)
    detail_lines = _wrap_lines(node["detail"], max_chars=24 if w >= 200 else 19, max_lines=3 if tall else 2) if node["detail"] else []
    parts = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="#ffffff" stroke="{color}" stroke-width="2.2"/>',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="24" rx="10" fill="{color}"/>',
        f'<text x="{x + 12:.1f}" y="{y + 16:.1f}" font-family="system-ui,sans-serif" font-size="11.5" font-weight="800" fill="#ffffff">{_esc(node["badge"], 16)}</text>',
    ]
    ty = y + 44
    for line in label_lines:
        parts.append(
            f'<text x="{x + 12:.1f}" y="{ty:.1f}" font-family="system-ui,sans-serif" font-size="13.5" font-weight="700" fill="#0f172a">{_esc(line, 40)}</text>'
        )
        ty += 17
    if detail_lines:
        ty += 4
        for line in detail_lines:
            parts.append(
                f'<text x="{x + 12:.1f}" y="{ty:.1f}" font-family="system-ui,sans-serif" font-size="11.5" fill="#475569">{_esc(line, 46)}</text>'
            )
            ty += 15
    return "".join(parts)
