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

    @staticmethod
    def _split_sentences(text: str, topic: str = "el tema") -> list[str]:
        sentences = [s.strip() for s in re.split(r"[.\n;]+", text) if len(s.strip()) >= 12]
        defaults = [
            f"Comprender los fundamentos esenciales de {topic}",
            f"Aplicar el procedimiento clave de {topic} paso a paso",
            f"Identificar errores frecuentes y criterios de verificación en {topic}",
            f"Consolidar el dominio mediante práctica activa y repaso espaciado sobre {topic}",
        ]
        while len(sentences) < 4:
            sentences.append(defaults[len(sentences) % len(defaults)])
        return sentences

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        if "<blueprint_request>" in user_prompt:
            text = json.dumps(self._build_blueprint(user_prompt), ensure_ascii=False)
        elif "<study_guide_request>" in user_prompt:
            text = json.dumps(self._build_study_guide(user_prompt), ensure_ascii=False)
        elif "<strong_exam_request>" in user_prompt:
            text = json.dumps(self._build_strong_exam(user_prompt), ensure_ascii=False)
        elif "<dynamic_visual_request>" in user_prompt:
            text = json.dumps(self._build_dynamic_visual(user_prompt), ensure_ascii=False)
        elif "<remediation_request>" in user_prompt:
            text = json.dumps(self._build_remediation(user_prompt), ensure_ascii=False)
        elif "<instructor_source_text>" in user_prompt:
            text = json.dumps(self._build_lesson_draft(user_prompt), ensure_ascii=False)
        else:
            text = self._build_socratic_hint(user_prompt)

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model_name=self.model_name,
            prompt_tokens=max(20, len(user_prompt) // 4),
            completion_tokens=max(40, len(text) // 4),
        )

    def _build_blueprint(self, user_prompt: str) -> dict:
        topic = self._extract_tag(user_prompt, "topic") or "Materia Formativa"
        pedagogy = self._extract_tag(user_prompt, "pedagogy_style") or "active_recall"
        modules_count = max(2, min(5, int(self._extract_tag(user_prompt, "modules_count") or "3")))
        notes = self._extract_tag(user_prompt, "source_notes")
        level = self._extract_tag(user_prompt, "education_level") or "specialized"
        is_safety = level == "rescue" or any(
            kw in f"{topic} {notes}".lower() for kw in ("rescate", "hemorragia", "triaje", "rcp", "seguridad")
        )
        sentences = self._split_sentences(notes, topic)

        pedagogy_labels = {
            "active_recall": "Recuperación Activa + Micro-retos Diarios",
            "problem_based": "Aprendizaje Basado en Casos y Decisiones Reales",
            "flipped_mastery": "Aula Invertida con Dominio por Competencias",
            "spaced_microlearning": "Microlearning Espaciado SM-2 de Alta Retención",
        }
        approach = pedagogy_labels.get(pedagogy, pedagogy_labels["active_recall"])

        modules = []
        for idx in range(modules_count):
            seed_line = sentences[idx % len(sentences)][:120]
            lessons = [
                {
                    "title": f"{topic}: Fundamentos — Parte {idx + 1}.1",
                    "lesson_type": "micro_lesson",
                    "estimated_minutes": 6,
                    "passing_score_pct": 75,
                    "is_safety_critical": is_safety,
                    "key_concepts": [seed_line, f"Aplicación práctica #{idx + 1}"],
                },
                {
                    "title": f"Práctica Guiada: {seed_line[:48]}",
                    "lesson_type": "study_guide_drill",
                    "estimated_minutes": 8,
                    "passing_score_pct": 80,
                    "is_safety_critical": is_safety,
                    "key_concepts": [sentences[(idx + 1) % len(sentences)][:80]],
                },
            ]
            if idx == modules_count - 1:
                lessons.append(
                    {
                        "title": f"Prueba Fuerte de Dominio: {topic}",
                        "lesson_type": "strong_exam",
                        "estimated_minutes": 15,
                        "passing_score_pct": 85,
                        "is_safety_critical": is_safety,
                        "key_concepts": ["Síntesis integral", "Casos de borde", "Evaluación sin pistas"],
                    }
                )
            modules.append(
                {
                    "title": f"Módulo {idx + 1}: {seed_line[:52]}",
                    "description": f"Bloque estructurado sobre {topic} con enfoque {approach}.",
                    "lessons": lessons,
                }
            )

        guide_md = (
            f"# Pensum y Guía Metodológica: {topic}\n\n"
            f"## Metodología Recomendada\n"
            f"- **Enfoque:** {approach}\n"
            f"- **Ritmo de estudio:** Sesiones enfocadas de 10–15 minutos + autoevaluación sin apuntes.\n"
            f"- **Cierre de unidad:** Prueba Fuerte (>= 85%) antes de avanzar.\n\n"
            f"## Ejes Temáticos Extraídos\n"
            + "\n".join(f"- {s[:160]}" for s in sentences[:5])
            + "\n\n## Plan de Repaso Espaciado\n"
            "- **Día 1:** Completar microlección visual y tarjetas clave.\n"
            "- **Día 3:** Sesión Flash en Biblioteca Visual + reordenamiento.\n"
            "- **Día 7:** Simulacro de Prueba Fuerte cronometrada.\n"
        )

        return {
            "course_title": topic,
            "course_description": f"Programa estructurado con enfoque {approach} para dominar {topic} de principio a fin.",
            "methodology": {
                "pedagogical_approach": approach,
                "study_rhythm": "Micro-sesiones de 10 minutos + pausa activa + comprobación inmediata",
                "recall_strategy": "Tarjetas visuales -> Secuencias -> Simulación de decisiones -> Prueba Fuerte",
                "objectives": [s[:140] for s in sentences[:3]],
                "prerequisites": ["Disposición de 10 minutos diarios", "Revisión previa de la guía de estudio"],
                "review_plan": [
                    "Día 1: Exploración conceptual y mapa visual",
                    "Día 3: Repaso espaciado SM-2 de puntos débiles",
                    "Día 7: Evaluación fuerte de integración",
                ],
            },
            "study_guide_markdown": guide_md,
            "modules": modules,
        }

    def _build_study_guide(self, user_prompt: str) -> dict:
        topic = self._extract_tag(user_prompt, "topic") or "Guía de Estudio"
        guide_type = self._extract_tag(user_prompt, "guide_type") or "guia_estudio"
        notes = self._extract_tag(user_prompt, "source_notes")
        pedagogy = self._extract_tag(user_prompt, "pedagogy_style") or "active_recall"
        sentences = self._split_sentences(notes, topic)

        markdown = (
            f"# {topic} ({guide_type.replace('_', ' ').title()})\n\n"
            f"## 1. Propósito de Estudio\n"
            f"Esta guía organiza los conceptos fundamentales de **{topic}** bajo el método `{pedagogy}`.\n\n"
            f"## 2. Núcleo Conceptual\n"
            + "\n".join(f"{i + 1}. **{s[:150]}**" for i, s in enumerate(sentences[:5]))
            + "\n\n## 3. Errores Frecuentes a Evitar\n"
            "- Memorizar definiciones aisladas sin conectar causa y efecto.\n"
            "- Saltarse la verificación de condiciones previas antes de ejecutar un paso.\n\n"
            "## 4. Protocolo de Repaso Activo\n"
            "1. Explica cada punto en voz alta sin mirar la guía.\n"
            "2. Resuelve la Prueba Fuerte asociada para detectar lagunas reales.\n"
            "3. Programa los ítems fallados en tu cola de Repaso Espaciado."
        )
        return {
            "title": f"Guía Profesional: {topic}",
            "content_markdown": markdown,
            "methodology_json": {
                "pedagogical_approach": pedagogy,
                "study_rhythm": "Bloques de 12 minutos de estudio + 3 minutos de evocación sin texto",
                "recall_strategy": "Autoevaluación activa + análisis de errores",
                "objectives": [s[:120] for s in sentences[:3]],
                "common_mistakes": [
                    "Omitir verificación inicial",
                    "Confundir el orden de etapas críticas",
                ],
                "review_plan": ["Día 1: Síntesis", "Día 3: Práctica", "Día 7: Prueba fuerte"],
            },
        }

    def _build_lesson_draft(self, user_prompt: str) -> dict:
        source = self._extract_tag(user_prompt, "instructor_source_text")
        level = self._extract_tag(user_prompt, "education_level") or "specialized"
        is_safety = level == "rescue" or any(
            kw in source.lower() for kw in ("rescate", "hemorragia", "triaje", "cervical", "rcp", "emergencia", "epp")
        )
        sentences = self._split_sentences(source, "la lección")
        s1, s2, s3, s4 = sentences[0][:140], sentences[1][:140], sentences[2][:140], sentences[3][:140]

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
                        "question": "¿Cuál afirmación refleja correctamente la prioridad inicial del contenido?",
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

    def _build_strong_exam(self, user_prompt: str) -> dict:
        source = self._extract_tag(user_prompt, "strong_exam_source")
        level = self._extract_tag(user_prompt, "education_level") or "specialized"
        diff = max(3, min(5, int(self._extract_tag(user_prompt, "difficulty_target") or "4")))
        count = max(5, min(8, int(self._extract_tag(user_prompt, "question_count") or "6")))
        is_safety = level == "rescue" or any(
            kw in source.lower() for kw in ("rescate", "hemorragia", "triaje", "cervical", "rcp", "seguridad")
        )
        sentences = self._split_sentences(source, "evaluación rigurosa")
        s1, s2, s3, s4 = sentences[0][:140], sentences[1][:140], sentences[2][:140], sentences[3][:140]

        pool = [
            {
                "challenge_type": "decision_simulation",
                "schema_version": 1,
                "prompt": "Caso clínico/técnico complejo de doble decisión bajo presión.",
                "payload_json": {
                    "scenario_context": f"Escenario de alta exigencia: {s1}. Surgen complicaciones inesperadas durante la ejecución.",
                    "initial_node_id": "n1",
                    "nodes": {
                        "n1": {
                            "narrative": "Etapa 1: Debes contener el riesgo principal antes de intervenir. ¿Qué ejecutas?",
                            "choices": [
                                {"id": "c1", "text": s2, "next_node_id": "n2"},
                                {"id": "c2", "text": "Acelerar la fase final saltando la verificación inicial", "next_node_id": "end_fail"},
                            ],
                        },
                        "n2": {
                            "narrative": "Etapa 2: La condición inicial se estabiliza parcialmente. ¿Cómo consolidas el resultado?",
                            "choices": [
                                {"id": "c3", "text": s3, "next_node_id": "end_pass"},
                                {"id": "c4", "text": "Dar por terminado el proceso sin validar indicadores", "next_node_id": "end_fail"},
                            ],
                        },
                        "end_pass": {"is_terminal": True, "summary": "Resolución óptima en ambos puntos críticos."},
                        "end_fail": {"is_terminal": True, "summary": "Fallo crítico de protocolo o verificación."},
                    },
                },
                "answer_key_json": {"optimal_paths": [["c1", "c3"]], "acceptable_terminal_nodes": ["end_pass"]},
                "pedagogical_explanation": f"Las pruebas fuertes exigen encadenar {s2} seguido de {s3}.",
                "difficulty": diff,
                "points": 25,
                "estimated_seconds": 90,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "sequence_ordering",
                "schema_version": 1,
                "prompt": "Prueba Fuerte: ordena la cadena completa de diagnóstico y respuesta.",
                "payload_json": {
                    "instruction": "Cualquier inversión en la secuencia invalida el protocolo.",
                    "items": [
                        {"id": "k1", "text": s1},
                        {"id": "k2", "text": s2},
                        {"id": "k3", "text": s3},
                        {"id": "k4", "text": s4},
                    ],
                },
                "answer_key_json": {"expected_order": ["k1", "k2", "k3", "k4"]},
                "pedagogical_explanation": f"La jerarquía causal exige iniciar por '{s1}' y cerrar con '{s4}'.",
                "difficulty": diff,
                "points": 20,
                "estimated_seconds": 75,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "matching",
                "schema_version": 1,
                "prompt": "Matriz de análisis: relaciona cada síntoma/condición con su respuesta exacta.",
                "payload_json": {
                    "instruction": "Distingue entre criterios de prioridad inmediata, control y cierre.",
                    "left_items": [
                        {"id": "a1", "text": "Condición inicial"},
                        {"id": "a2", "text": "Intervención central"},
                        {"id": "a3", "text": "Control de calidad"},
                    ],
                    "right_items": [
                        {"id": "b1", "text": s1},
                        {"id": "b2", "text": s2},
                        {"id": "b3", "text": s3},
                    ],
                    "shuffle": True,
                },
                "answer_key_json": {"pairs": {"a1": "b1", "a2": "b2", "a3": "b3"}},
                "pedagogical_explanation": "Cada fase tiene un criterio de entrada y verificación no intercambiable.",
                "difficulty": diff,
                "points": 20,
                "estimated_seconds": 65,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "visual_concept_card",
                "schema_version": 1,
                "prompt": "Análisis crítico de caso de borde.",
                "payload_json": {
                    "card_title": "Evaluación Crítica — Detección de Error",
                    "visual_caption": s1,
                    "key_points": [s2, s3, "Un distractor común omite la validación previa."],
                    "check_question": {
                        "question": "¿Cuál acción constituye una falla grave según el criterio evaluado?",
                        "options": [
                            {"id": "x1", "text": f"Ejecutar prioritariamente: {s2[:90]}"},
                            {"id": "x2", "text": "Ignorar el criterio previo y aplicar la fase final sin diagnóstico"},
                            {"id": "x3", "text": f"Verificar antes de cerrar: {s3[:90]}"},
                        ],
                    },
                },
                "answer_key_json": {"correct_option_id": "x2"},
                "pedagogical_explanation": f"Saltar la verificación inicial invalida todo el protocolo ({s1}).",
                "difficulty": diff,
                "points": 20,
                "estimated_seconds": 60,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "fill_in_blanks",
                "schema_version": 1,
                "prompt": "Evocación exacta de criterios de control.",
                "payload_json": {
                    "template": "Antes de intervenir se exige {{c1}}, y solo tras estabilizar se ejecuta {{c2}}.",
                    "input_mode": "word_bank",
                    "word_bank": ["verificación inicial", "validación de cierre", "ejecución a ciegas", "omisión"],
                    "blanks": [
                        {"id": "c1", "label": "Requisito previo"},
                        {"id": "c2", "label": "Control posterior"},
                    ],
                },
                "answer_key_json": {
                    "blanks": {
                        "c1": {"accepted": ["verificación inicial"], "case_sensitive": False},
                        "c2": {"accepted": ["validación de cierre"], "case_sensitive": False},
                    }
                },
                "pedagogical_explanation": f"Sin verificación inicial ni validación de cierre no hay dominio completo ({s4}).",
                "difficulty": diff,
                "points": 20,
                "estimated_seconds": 60,
                "is_safety_critical": is_safety,
            },
            {
                "challenge_type": "visual_concept_card",
                "schema_version": 1,
                "prompt": "Síntesis comparativa de prioridades.",
                "payload_json": {
                    "card_title": "Criterio de Decisión Bajo Incertidumbre",
                    "visual_caption": s4,
                    "key_points": [s1, s4],
                    "check_question": {
                        "question": "Cuando dos acciones compiten en tiempo, ¿qué principio prevalece?",
                        "options": [
                            {"id": "p1", "text": s1},
                            {"id": "p2", "text": "Improvisar según intuición sin registro"},
                        ],
                    },
                },
                "answer_key_json": {"correct_option_id": "p1"},
                "pedagogical_explanation": f"El estándar exige priorizar: {s1}.",
                "difficulty": diff,
                "points": 15,
                "estimated_seconds": 50,
                "is_safety_critical": is_safety,
            },
        ]
        return {
            "lesson_summary": f"Prueba Fuerte (Nivel {diff}/5): {s1[:180]}",
            "challenges": pool[:count],
        }

    def _build_dynamic_visual(self, user_prompt: str) -> dict:
        topic = self._extract_tag(user_prompt, "topic") or "Mapa Conceptual"
        kind = self._extract_tag(user_prompt, "diagram_kind") or "auto"
        context = self._extract_tag(user_prompt, "context_text")
        sentences = self._split_sentences(context, topic)

        template = kind if kind in {"cycle", "flowchart", "hierarchy", "comparison", "layers"} else "flowchart"
        if kind == "auto":
            low = f"{topic} {context}".lower()
            if any(w in low for w in ("ciclo", "circul", "feedback", "etapa")):
                template = "cycle"
            elif any(w in low for w in ("jerarqu", "árbol", "tipos", "clasific")):
                template = "hierarchy"
            elif any(w in low for w in ("compar", "diferencia", "versus", "vs")):
                template = "comparison"
            elif any(w in low for w in ("capa", "nivel", "pirámide", "prioridad")):
                template = "layers"

        nodes = [
            {"id": f"z{i + 1}", "label": sentences[i][:34], "detail": sentences[i][:72], "badge": f"Paso {i + 1}"}
            for i in range(4)
        ]
        return {
            "title": topic[:90],
            "subtitle": f"Esquema visual interactivo ({template})",
            "template": template,
            "nodes": nodes,
            "recommended_question": f"Identifica en el diagrama cuál nodo representa el primer punto clave de '{topic}'.",
            "correct_node_id": "z1",
            "explanation": f"El nodo 1 sintetiza el fundamento inicial: {sentences[0][:140]}.",
        }

    def _build_remediation(self, user_prompt: str) -> dict:
        missed = self._extract_tag(user_prompt, "missed_items")
        guide = self._extract_tag(user_prompt, "study_guide_context")
        lines = [ln.lstrip("- ").strip() for ln in missed.splitlines() if ln.strip()]
        bullets = "\n".join(f"- **Punto crítico:** {ln}" for ln in lines[:6]) or "- Refuerzo general de fundamentos"
        guide_excerpt = f"\n\n### Referencia de tu Guía del Curso\n{guide[:360]}" if guide else ""
        return {
            "title": "Micro-Guía de Refuerzo Adaptativo",
            "remediation_markdown": (
                f"## Diagnóstico de Repaso\nDetectamos {len(lines)} ítems que requieren consolidación:\n"
                f"{bullets}{guide_excerpt}\n\n"
                "### Técnica recomendada\nResuelve 5 minutos de Repaso Espaciado SM-2 antes de reintentar la Prueba Fuerte."
            ),
            "action_steps": [
                "Relee los criterios previos de cada reto fallado.",
                "Completa una sesión Flash en Repaso (/reviews).",
                "Vuelve a rendir la Prueba Fuerte buscando 85%+.",
            ],
        }

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
