"""Capa de proveedores IA intercambiables (Gemini, Groq y Fallback determinístico)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    used_fallback: bool = False
    fallback_reason: str | None = None


class BaseLLMProvider:
    """Interfaz desacoplada para proveedores de modelos de lenguaje."""

    provider_name: str

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
        }
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, params={"key": self.api_key}, json=body)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates") or []
        text = candidates[0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata") or {}
        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model_name=self.model_name,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
        )


class GroqProvider(BaseLLMProvider):
    provider_name = "groq"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model_name=self.model_name,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )


class DeterministicFallbackProvider(BaseLLMProvider):
    """Fallback pedagógico local cuando no hay API key o falla el proveedor externo."""

    provider_name = "fallback"
    model_name = "deterministic-pedagogical-v1"

    @staticmethod
    def _extract_tag(prompt: str, tag: str) -> str:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", prompt, re.DOTALL)
        return match.group(1).strip() if match else ""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        if "<instructor_source_text>" in user_prompt:
            payload = self._build_lesson_draft(user_prompt)
            text = json.dumps(payload, ensure_ascii=False)
        else:
            text = self._build_socratic_hint(user_prompt)

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model_name=self.model_name,
            prompt_tokens=max(20, len(user_prompt) // 4),
            completion_tokens=max(40, len(text) // 4),
        )

    def _build_lesson_draft(self, user_prompt: str) -> dict:
        source = self._extract_tag(user_prompt, "instructor_source_text")
        level = self._extract_tag(user_prompt, "education_level") or "specialized"
        is_safety = level == "rescue" or any(
            kw in source.lower() for kw in ("rescate", "hemorragia", "triaje", "cervical", "rcp", "emergencia", "epp")
        )
        sentences = [s.strip() for s in re.split(r"[.\n]+", source) if len(s.strip()) >= 15]
        while len(sentences) < 4:
            sentences.append(sentences[0] if sentences else "Evaluar la situación antes de actuar")

        s1, s2, s3 = sentences[0][:140], sentences[1][:140], sentences[2][:140]
        s4 = sentences[3][:140]

        challenges = [
            {
                "challenge_type": "visual_concept_card",
                "schema_version": 1,
                "prompt": "Analiza el concepto principal del material de estudio.",
                "payload_json": {
                    "card_title": "Principio clave de la lección",
                    "visual_caption": s1,
                    "key_points": [s1, s2],
                    "check_question": {
                        "question": "¿Cuál afirmación refleja correctamente la prioridad inicial del protocolo?",
                        "options": [
                            {"id": "a", "text": s1},
                            {"id": "b", "text": "Omitir la verificación previa para ahorrar tiempo"},
                        ],
                    },
                },
                "answer_key_json": {"correct_option_id": "a"},
                "pedagogical_explanation": f"Según el texto autorizado: {s1}.",
                "difficulty": 2,
                "points": 10,
                "estimated_seconds": 40,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "sequence_ordering",
                "schema_version": 1,
                "prompt": "Ordena los puntos clave siguiendo la progresión lógica del texto.",
                "payload_json": {
                    "instruction": "Organiza del paso inicial al paso posterior.",
                    "items": [
                        {"id": "step_1", "text": s1},
                        {"id": "step_2", "text": s2},
                        {"id": "step_3", "text": s3},
                    ],
                },
                "answer_key_json": {"expected_order": ["step_1", "step_2", "step_3"]},
                "pedagogical_explanation": f"La secuencia correcta sigue el orden operativo: {s1} -> {s2} -> {s3}.",
                "difficulty": 2,
                "points": 15,
                "estimated_seconds": 50,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "matching",
                "schema_version": 1,
                "prompt": "Relaciona cada fase con su acción correspondiente.",
                "payload_json": {
                    "instruction": "Asocia cada etapa con su descripción del manual.",
                    "left_items": [
                        {"id": "l1", "text": "Fase 1"},
                        {"id": "l2", "text": "Fase 2"},
                    ],
                    "right_items": [
                        {"id": "r1", "text": s1},
                        {"id": "r2", "text": s2},
                    ],
                    "shuffle": True,
                },
                "answer_key_json": {"pairs": {"l1": "r1", "l2": "r2"}},
                "pedagogical_explanation": f"La Fase 1 corresponde a '{s1}' y la Fase 2 a '{s2}'.",
                "difficulty": 2,
                "points": 15,
                "estimated_seconds": 45,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "decision_simulation",
                "schema_version": 1,
                "prompt": "Simulación práctica basada en el escenario del manual.",
                "payload_json": {
                    "scenario_context": s1,
                    "initial_node_id": "n1",
                    "nodes": {
                        "n1": {
                            "narrative": "¿Cómo aplicas el criterio descrito antes de continuar?",
                            "choices": [
                                {"id": "c_ok", "text": s2, "next_node_id": "end_ok"},
                                {"id": "c_bad", "text": "Actuar sin seguir las pautas documentadas", "next_node_id": "end_bad"},
                            ],
                        },
                        "end_ok": {"is_terminal": True, "summary": "Decisión alineada al manual autorizado."},
                        "end_bad": {"is_terminal": True, "summary": "Decisión riesgosa fuera de protocolo."},
                    },
                },
                "answer_key_json": {"optimal_paths": [["c_ok"]], "acceptable_terminal_nodes": ["end_ok"]},
                "pedagogical_explanation": f"El procedimiento válido exige priorizar: {s2}.",
                "difficulty": 3,
                "points": 20,
                "estimated_seconds": 60,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "fill_in_blanks",
                "schema_version": 1,
                "prompt": "Completa la síntesis operativa del contenido.",
                "payload_json": {
                    "template": "El principio prioritario establece {{b1}} antes de continuar con {{b2}}.",
                    "input_mode": "word_bank",
                    "word_bank": ["evaluación segura", "intervención posterior", "improvisación"],
                    "blanks": [
                        {"id": "b1", "label": "Prioridad inicial"},
                        {"id": "b2", "label": "Siguiente etapa"},
                    ],
                },
                "answer_key_json": {
                    "blanks": {
                        "b1": {"accepted": ["evaluación segura"], "case_sensitive": False},
                        "b2": {"accepted": ["intervención posterior"], "case_sensitive": False},
                    }
                },
                "pedagogical_explanation": f"Referencia de cierre: {s4}.",
                "difficulty": 2,
                "points": 10,
                "estimated_seconds": 40,
                "is_safety_critical": is_safety,
            },
        ]
        return {"lesson_summary": s1[:240], "challenges": challenges}

    def _build_socratic_hint(self, user_prompt: str) -> str:
        is_safety = self._extract_tag(user_prompt, "is_safety_critical") == "true"
        level = self._extract_tag(user_prompt, "education_level") or "specialized"
        safety_note = (
            " Por tratarse de un protocolo crítico de seguridad, valida cualquier duda práctica con tu instructor asignado."
            if is_safety
            else ""
        )
        analogy = (
            "Piensa en revisar los frenos antes de iniciar un descenso: "
            if level in {"rescue", "technical", "specialized", "university"}
            else "Imagina revisar que el puente sea firme antes de cruzar: "
        )
        return (
            f"{analogy}observa qué condición debe cumplirse primero para evitar riesgos mayores. "
            f"¿Cuál de tus pasos o elecciones garantiza control antes de avanzar al siguiente nivel?{safety_note}"
        )


def resolve_provider(provider_name: str, model_name: str | None, settings: Settings | None = None) -> BaseLLMProvider:
    cfg = settings or get_settings()
    if provider_name == "gemini" and cfg.gemini_api_key:
        return GeminiProvider(api_key=cfg.gemini_api_key, model_name=model_name or cfg.gemini_model)
    if provider_name == "groq" and cfg.groq_api_key:
        return GroqProvider(api_key=cfg.groq_api_key, model_name=model_name or cfg.groq_model)
    return DeterministicFallbackProvider()


def run_with_fallback(
    *,
    provider_name: str,
    model_name: str | None,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_seconds: float,
) -> LLMResponse:
    """Ejecuta el proveedor configurado y conmuta a fallback ante error o falta de API key."""
    primary = resolve_provider(provider_name, model_name)
    if isinstance(primary, DeterministicFallbackProvider):
        res = primary.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        if provider_name != "fallback":
            return LLMResponse(
                text=res.text,
                provider=res.provider,
                model_name=res.model_name,
                prompt_tokens=res.prompt_tokens,
                completion_tokens=res.completion_tokens,
                used_fallback=True,
                fallback_reason="missing_api_key",
            )
        return res

    try:
        return primary.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        fb = DeterministicFallbackProvider().generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        return LLMResponse(
            text=fb.text,
            provider=fb.provider,
            model_name=fb.model_name,
            prompt_tokens=fb.prompt_tokens,
            completion_tokens=fb.completion_tokens,
            used_fallback=True,
            fallback_reason=type(exc).__name__,
        )
