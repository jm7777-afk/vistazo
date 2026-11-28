"""Motor extensible (Registry + Strategy) para validación y evaluación de retos."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import ValidationDomainError
from app.modules.challenges.contracts import (
    DecisionSimulationAnswerKey,
    DecisionSimulationPayload,
    DecisionSimulationSubmission,
    FillInBlanksAnswerKey,
    FillInBlanksPayload,
    FillInBlanksSubmission,
    InteractiveZone,
    InteractiveZonesAnswerKey,
    InteractiveZonesPayload,
    InteractiveZonesSubmission,
    MatchingAnswerKey,
    MatchingPayload,
    MatchingSubmission,
    OpenResponseAnswerKey,
    OpenResponsePayload,
    OpenResponseSubmission,
    SequenceAnswerKey,
    SequencePayload,
    SequenceSubmission,
    VisualConceptAnswerKey,
    VisualConceptPayload,
    VisualConceptSubmission,
)

TPayload = TypeVar("TPayload", bound=BaseModel)
TAnswerKey = TypeVar("TAnswerKey", bound=BaseModel)
TSubmission = TypeVar("TSubmission", bound=BaseModel)


@dataclass(frozen=True)
class EvaluationResult:
    is_correct: bool
    score_awarded: int
    detail: dict[str, Any]


class BaseChallengeHandler(Generic[TPayload, TAnswerKey, TSubmission]):
    """Contrato base para añadir nuevos tipos de retos sin cambiar el esquema de BD."""

    payload_model: type[TPayload]
    answer_key_model: type[TAnswerKey]
    submission_model: type[TSubmission]

    def validate_definition(self, payload_raw: dict, answer_key_raw: dict) -> tuple[dict, dict]:
        try:
            payload = self.payload_model.model_validate(payload_raw)
            answer_key = self.answer_key_model.model_validate(answer_key_raw)
        except ValidationError as exc:
            raise ValidationDomainError(f"Contrato JSON inválido: {exc.errors()[0]['msg']}") from exc

        self.validate_cross_rules(payload, answer_key)
        return payload.model_dump(), answer_key.model_dump()

    def validate_cross_rules(self, payload: TPayload, answer_key: TAnswerKey) -> None:
        """Reglas cruzadas entre payload y answer_key."""

    def evaluate(
        self,
        *,
        payload_raw: dict,
        answer_key_raw: dict,
        submission_raw: dict,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        try:
            payload = self.payload_model.model_validate(payload_raw)
            answer_key = self.answer_key_model.model_validate(answer_key_raw)
            submission = self.submission_model.model_validate(submission_raw)
        except ValidationError as exc:
            raise ValidationDomainError(f"Respuesta enviada inválida: {exc.errors()[0]['msg']}") from exc

        return self._score(
            payload=payload,
            answer_key=answer_key,
            submission=submission,
            max_points=max_points,
            is_safety_critical=is_safety_critical,
        )

    def _score(
        self,
        *,
        payload: TPayload,
        answer_key: TAnswerKey,
        submission: TSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        raise NotImplementedError


class VisualConceptHandler(
    BaseChallengeHandler[VisualConceptPayload, VisualConceptAnswerKey, VisualConceptSubmission]
):
    payload_model = VisualConceptPayload
    answer_key_model = VisualConceptAnswerKey
    submission_model = VisualConceptSubmission

    def validate_cross_rules(self, payload: VisualConceptPayload, answer_key: VisualConceptAnswerKey) -> None:
        option_ids = {opt.id for opt in payload.check_question.options}
        if answer_key.correct_option_id not in option_ids:
            raise ValidationDomainError("correct_option_id debe existir dentro de check_question.options")

    def _score(
        self,
        *,
        payload: VisualConceptPayload,
        answer_key: VisualConceptAnswerKey,
        submission: VisualConceptSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        correct = submission.selected_option_id == answer_key.correct_option_id
        return EvaluationResult(
            is_correct=correct,
            score_awarded=max_points if correct else 0,
            detail={"selected_option_id": submission.selected_option_id},
        )


class MatchingHandler(BaseChallengeHandler[MatchingPayload, MatchingAnswerKey, MatchingSubmission]):
    payload_model = MatchingPayload
    answer_key_model = MatchingAnswerKey
    submission_model = MatchingSubmission

    def validate_cross_rules(self, payload: MatchingPayload, answer_key: MatchingAnswerKey) -> None:
        left_ids = {item.id for item in payload.left_items}
        right_ids = {item.id for item in payload.right_items}
        if set(answer_key.pairs.keys()) != left_ids:
            raise ValidationDomainError("answer_key.pairs debe cubrir exactamente todos los left_items")
        if not set(answer_key.pairs.values()).issubset(right_ids):
            raise ValidationDomainError("Los valores de answer_key.pairs deben existir en right_items")

    def _score(
        self,
        *,
        payload: MatchingPayload,
        answer_key: MatchingAnswerKey,
        submission: MatchingSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        total = len(answer_key.pairs)
        matches = sum(1 for k, v in answer_key.pairs.items() if submission.pairs.get(k) == v)
        all_correct = matches == total
        if is_safety_critical:
            awarded = max_points if all_correct else 0
        else:
            awarded = int(round((matches / total) * max_points)) if total else 0
        return EvaluationResult(
            is_correct=all_correct,
            score_awarded=awarded,
            detail={"matched": matches, "total": total},
        )


class SequenceOrderingHandler(BaseChallengeHandler[SequencePayload, SequenceAnswerKey, SequenceSubmission]):
    payload_model = SequencePayload
    answer_key_model = SequenceAnswerKey
    submission_model = SequenceSubmission

    def validate_cross_rules(self, payload: SequencePayload, answer_key: SequenceAnswerKey) -> None:
        item_ids = [item.id for item in payload.items]
        if sorted(answer_key.expected_order) != sorted(item_ids) or len(answer_key.expected_order) != len(item_ids):
            raise ValidationDomainError("expected_order debe ser una permutación exacta de items")

    def _score(
        self,
        *,
        payload: SequencePayload,
        answer_key: SequenceAnswerKey,
        submission: SequenceSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        correct = submission.ordered_ids == answer_key.expected_order
        return EvaluationResult(
            is_correct=correct,
            score_awarded=max_points if correct else 0,
            detail={"positions_matched": sum(1 for a, b in zip(submission.ordered_ids, answer_key.expected_order) if a == b)},
        )


class InteractiveZonesHandler(
    BaseChallengeHandler[InteractiveZonesPayload, InteractiveZonesAnswerKey, InteractiveZonesSubmission]
):
    payload_model = InteractiveZonesPayload
    answer_key_model = InteractiveZonesAnswerKey
    submission_model = InteractiveZonesSubmission

    def validate_cross_rules(self, payload: InteractiveZonesPayload, answer_key: InteractiveZonesAnswerKey) -> None:
        zone_ids = {z.id for z in payload.zones}
        if not set(answer_key.correct_zone_ids).issubset(zone_ids):
            raise ValidationDomainError("correct_zone_ids debe referenciar zonas existentes")

    @staticmethod
    def _point_in_zone(x: float, y: float, zone: InteractiveZone) -> bool:
        if zone.shape == "circle" and zone.r is not None:
            return math.hypot(x - zone.x, y - zone.y) <= zone.r
        if zone.shape == "rect" and zone.w is not None and zone.h is not None:
            return zone.x <= x <= (zone.x + zone.w) and zone.y <= y <= (zone.y + zone.h)
        return False

    def _score(
        self,
        *,
        payload: InteractiveZonesPayload,
        answer_key: InteractiveZonesAnswerKey,
        submission: InteractiveZonesSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        selected = set(submission.selected_zone_ids)
        if not selected and submission.tap_point and answer_key.accept_coordinates_within_zones:
            for z in payload.zones:
                if self._point_in_zone(submission.tap_point.x, submission.tap_point.y, z):
                    selected.add(z.id)
        correct = selected == set(answer_key.correct_zone_ids)
        return EvaluationResult(
            is_correct=correct,
            score_awarded=max_points if correct else 0,
            detail={"resolved_zones": sorted(selected)},
        )


class DecisionSimulationHandler(
    BaseChallengeHandler[DecisionSimulationPayload, DecisionSimulationAnswerKey, DecisionSimulationSubmission]
):
    payload_model = DecisionSimulationPayload
    answer_key_model = DecisionSimulationAnswerKey
    submission_model = DecisionSimulationSubmission

    def validate_cross_rules(
        self, payload: DecisionSimulationPayload, answer_key: DecisionSimulationAnswerKey
    ) -> None:
        if payload.initial_node_id not in payload.nodes:
            raise ValidationDomainError("initial_node_id no existe en nodes")
        for node_id, node in payload.nodes.items():
            for choice in node.choices:
                if choice.next_node_id not in payload.nodes:
                    raise ValidationDomainError(f"next_node_id '{choice.next_node_id}' no existe en nodes")
        for term in answer_key.acceptable_terminal_nodes:
            node = payload.nodes.get(term)
            if not node or not node.is_terminal:
                raise ValidationDomainError(f"Nodo terminal '{term}' inválido en answer_key")

    def _score(
        self,
        *,
        payload: DecisionSimulationPayload,
        answer_key: DecisionSimulationAnswerKey,
        submission: DecisionSimulationSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        current_id = payload.initial_node_id
        visited: set[str] = {current_id}
        for choice_id in submission.chosen_sequence:
            node = payload.nodes.get(current_id)
            if not node or node.is_terminal:
                return EvaluationResult(False, 0, {"reason": "invalid_transition", "node_id": current_id})
            match = next((c for c in node.choices if c.id == choice_id), None)
            if not match:
                return EvaluationResult(False, 0, {"reason": "unknown_choice", "choice_id": choice_id})
            if match.next_node_id in visited:
                return EvaluationResult(False, 0, {"reason": "cycle_detected"})
            current_id = match.next_node_id
            visited.add(current_id)

        terminal_node = payload.nodes.get(current_id)
        is_acceptable = bool(
            terminal_node and terminal_node.is_terminal and current_id in answer_key.acceptable_terminal_nodes
        )
        return EvaluationResult(
            is_correct=is_acceptable,
            score_awarded=max_points if is_acceptable else 0,
            detail={"terminal_node_id": current_id},
        )


class FillInBlanksHandler(BaseChallengeHandler[FillInBlanksPayload, FillInBlanksAnswerKey, FillInBlanksSubmission]):
    payload_model = FillInBlanksPayload
    answer_key_model = FillInBlanksAnswerKey
    submission_model = FillInBlanksSubmission

    def validate_cross_rules(self, payload: FillInBlanksPayload, answer_key: FillInBlanksAnswerKey) -> None:
        blank_ids = {b.id for b in payload.blanks}
        if set(answer_key.blanks.keys()) != blank_ids:
            raise ValidationDomainError("answer_key.blanks debe coincidir con los IDs definidos en payload.blanks")
        for b_id in blank_ids:
            if f"{{{{{b_id}}}}}" not in payload.template:
                raise ValidationDomainError(f"El placeholder '{{{{{b_id}}}}}' falta en el template")

    def _score(
        self,
        *,
        payload: FillInBlanksPayload,
        answer_key: FillInBlanksAnswerKey,
        submission: FillInBlanksSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        correct_count = 0
        total = len(answer_key.blanks)
        for blank_id, rule in answer_key.blanks.items():
            raw_val = submission.answers.get(blank_id, "").strip()
            if rule.case_sensitive:
                matched = raw_val in [a.strip() for a in rule.accepted]
            else:
                matched = raw_val.lower() in [a.strip().lower() for a in rule.accepted]
            if matched:
                correct_count += 1

        all_correct = correct_count == total
        if is_safety_critical:
            awarded = max_points if all_correct else 0
        else:
            awarded = int(round((correct_count / total) * max_points)) if total else 0
        return EvaluationResult(
            is_correct=all_correct,
            score_awarded=awarded,
            detail={"correct_blanks": correct_count, "total_blanks": total},
        )


class OpenResponseHandler(BaseChallengeHandler[OpenResponsePayload, OpenResponseAnswerKey, OpenResponseSubmission]):
    payload_model = OpenResponsePayload
    answer_key_model = OpenResponseAnswerKey
    submission_model = OpenResponseSubmission

    def _score(
        self,
        *,
        payload: OpenResponsePayload,
        answer_key: OpenResponseAnswerKey,
        submission: OpenResponseSubmission,
        max_points: int,
        is_safety_critical: bool,
    ) -> EvaluationResult:
        text = submission.response_text.strip()
        words = [w for w in text.split() if w]
        low = text.lower()
        criteria = [c.strip() for c in (payload.keywords_expected or answer_key.rubric_criteria) if c.strip()]
        if not criteria:
            criteria = [w for w in answer_key.reference_answer.lower().split() if len(w) >= 5][:4]

        matched = [c for c in criteria if c.lower() in low]
        ratio = (len(matched) / len(criteria)) if criteria else (1.0 if len(words) >= payload.min_words else 0.5)
        length_ok = len(words) >= payload.min_words
        if not length_ok:
            ratio = min(ratio, 0.5)
        awarded = int(round(max_points * ratio))
        is_ok = ratio >= 0.6 and length_ok
        feedback = (
            f"Pre-evaluación por rúbrica: {len(matched)}/{len(criteria) or 1} criterios clave cubiertos "
            f"({len(words)} palabras). Pendiente o validado para revisión docente."
        )
        return EvaluationResult(
            is_correct=is_ok,
            score_awarded=awarded,
            detail={
                "word_count": len(words),
                "matched_criteria": matched,
                "rubric_feedback": feedback,
            },
        )


CHALLENGE_REGISTRY: dict[tuple[str, int], BaseChallengeHandler[Any, Any, Any]] = {
    ("visual_concept_card", 1): VisualConceptHandler(),
    ("matching", 1): MatchingHandler(),
    ("sequence_ordering", 1): SequenceOrderingHandler(),
    ("interactive_zones", 1): InteractiveZonesHandler(),
    ("decision_simulation", 1): DecisionSimulationHandler(),
    ("fill_in_blanks", 1): FillInBlanksHandler(),
    ("open_response", 1): OpenResponseHandler(),
}


def get_challenge_handler(challenge_type: str, schema_version: int = 1) -> BaseChallengeHandler[Any, Any, Any]:
    handler = CHALLENGE_REGISTRY.get((challenge_type, schema_version))
    if not handler:
        raise ValidationDomainError(f"Tipo de reto o versión no soportada: {challenge_type} v{schema_version}")
    return handler
