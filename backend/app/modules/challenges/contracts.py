"""Contratos Pydantic estrictos para payload, answer_key y respuestas de los 6 tipos de retos."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# 1. Tarjeta conceptual visual
# ---------------------------------------------------------------------------
class ConceptOption(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=400)


class ConceptCheckQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    options: list[ConceptOption] = Field(min_length=2, max_length=6)


class VisualConceptPayload(BaseModel):
    card_title: str = Field(min_length=2, max_length=200)
    visual_media_id: str | None = None
    visual_caption: str | None = Field(default=None, max_length=400)
    key_points: list[str] = Field(min_length=1, max_length=6)
    check_question: ConceptCheckQuestion


class VisualConceptAnswerKey(BaseModel):
    correct_option_id: str = Field(min_length=1, max_length=32)


class VisualConceptSubmission(BaseModel):
    selected_option_id: str = Field(min_length=1, max_length=32)


# ---------------------------------------------------------------------------
# 2. Emparejamiento
# ---------------------------------------------------------------------------
class MatchItem(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=300)
    media_id: str | None = None


class MatchingPayload(BaseModel):
    instruction: str = Field(min_length=3, max_length=400)
    left_items: list[MatchItem] = Field(min_length=2, max_length=8)
    right_items: list[MatchItem] = Field(min_length=2, max_length=8)
    shuffle: bool = True


class MatchingAnswerKey(BaseModel):
    pairs: dict[str, str]


class MatchingSubmission(BaseModel):
    pairs: dict[str, str]


# ---------------------------------------------------------------------------
# 3. Ordenar secuencia
# ---------------------------------------------------------------------------
class SequenceItem(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=400)


class SequencePayload(BaseModel):
    instruction: str = Field(min_length=3, max_length=400)
    items: list[SequenceItem] = Field(min_length=2, max_length=10)


class SequenceAnswerKey(BaseModel):
    expected_order: list[str] = Field(min_length=2, max_length=10)


class SequenceSubmission(BaseModel):
    ordered_ids: list[str] = Field(min_length=2, max_length=10)


# ---------------------------------------------------------------------------
# 4. Zonas interactivas
# ---------------------------------------------------------------------------
class InteractiveZone(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    shape: Literal["circle", "rect"]
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    r: float | None = Field(default=None, gt=0.0, le=0.5)
    w: float | None = Field(default=None, gt=0.0, le=1.0)
    h: float | None = Field(default=None, gt=0.0, le=1.0)
    label: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_geometry(self) -> InteractiveZone:
        if self.shape == "circle" and self.r is None:
            raise ValueError("Una zona circular requiere radio 'r'")
        if self.shape == "rect" and (self.w is None or self.h is None):
            raise ValueError("Una zona rectangular requiere 'w' y 'h'")
        return self


class InteractiveZonesPayload(BaseModel):
    instruction: str = Field(min_length=3, max_length=400)
    diagram_media_id: str | None = None
    diagram_svg_preset: str | None = None
    aspect_ratio: str = "16:9"
    selection_mode: Literal["single", "multiple"] = "single"
    zones: list[InteractiveZone] = Field(min_length=2, max_length=12)


class InteractiveZonesAnswerKey(BaseModel):
    correct_zone_ids: list[str] = Field(min_length=1)
    accept_coordinates_within_zones: bool = True


class TapPoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class InteractiveZonesSubmission(BaseModel):
    selected_zone_ids: list[str] = Field(default_factory=list)
    tap_point: TapPoint | None = None


# ---------------------------------------------------------------------------
# 5. Simulación de toma de decisiones
# ---------------------------------------------------------------------------
class DecisionChoice(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=2, max_length=400)
    next_node_id: str = Field(min_length=1, max_length=40)


class DecisionNode(BaseModel):
    narrative: str = Field(default="", max_length=1000)
    choices: list[DecisionChoice] = Field(default_factory=list)
    is_terminal: bool = False
    summary: str | None = Field(default=None, max_length=600)


class DecisionSimulationPayload(BaseModel):
    scenario_context: str = Field(min_length=5, max_length=1000)
    initial_node_id: str = Field(min_length=1, max_length=40)
    nodes: dict[str, DecisionNode]


class DecisionSimulationAnswerKey(BaseModel):
    optimal_paths: list[list[str]] = Field(min_length=1)
    acceptable_terminal_nodes: list[str] = Field(min_length=1)


class DecisionSimulationSubmission(BaseModel):
    chosen_sequence: list[str] = Field(min_length=1, max_length=20)


# ---------------------------------------------------------------------------
# 6. Completar espacios
# ---------------------------------------------------------------------------
class BlankDescriptor(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=120)


class FillInBlanksPayload(BaseModel):
    template: str = Field(min_length=5, max_length=1500)
    input_mode: Literal["word_bank", "free_text"] = "word_bank"
    word_bank: list[str] = Field(default_factory=list)
    blanks: list[BlankDescriptor] = Field(min_length=1, max_length=10)


class BlankAcceptedRule(BaseModel):
    accepted: list[str] = Field(min_length=1)
    case_sensitive: bool = False


class FillInBlanksAnswerKey(BaseModel):
    blanks: dict[str, BlankAcceptedRule]


class FillInBlanksSubmission(BaseModel):
    answers: dict[str, str]
