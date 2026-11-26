"""Observabilidad HTTP: trazabilidad X-Request-ID, latencias y métricas Prometheus."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsRegistry:
    """Registro thread-safe de métricas HTTP exportables en formato Prometheus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total: dict[tuple[str, str, int], int] = defaultdict(int)
        self.duration_ms_sum: dict[tuple[str, str], float] = defaultdict(float)
        self.duration_ms_count: dict[tuple[str, str], int] = defaultdict(int)

    def observe(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.requests_total[(method, path, status_code)] += 1
            self.duration_ms_sum[(method, path)] += duration_ms
            self.duration_ms_count[(method, path)] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP vistazo_http_requests_total Total de peticiones HTTP procesadas",
            "# TYPE vistazo_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status_code), count in sorted(self.requests_total.items()):
                lines.append(
                    f'vistazo_http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {count}'
                )
            lines.append("# HELP vistazo_http_request_duration_ms_sum Suma de latencia HTTP en ms")
            lines.append("# TYPE vistazo_http_request_duration_ms_sum counter")
            for (method, path), total_ms in sorted(self.duration_ms_sum.items()):
                lines.append(f'vistazo_http_request_duration_ms_sum{{method="{method}",path="{path}"}} {total_ms:.2f}')
            lines.append("# HELP vistazo_http_request_duration_ms_count Conteo de observaciones de latencia")
            lines.append("# TYPE vistazo_http_request_duration_ms_count counter")
            for (method, path), cnt in sorted(self.duration_ms_count.items()):
                lines.append(f'vistazo_http_request_duration_ms_count{{method="{method}",path="{path}"}} {cnt}')
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Asigna X-Request-ID, mide latencia y registra métricas por ruta."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - t0) * 1000.0

        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        metrics_registry.observe(request.method, route_path, response.status_code, duration_ms)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response
