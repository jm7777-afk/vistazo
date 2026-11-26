"""Pruebas unitarias de validación y evaluación de los 6 tipos de retos."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationDomainError
from app.modules.challenges.evaluators import get_challenge_handler


def test_visual_concept_card_validation_and_eval() -> None:
    handler = get_challenge_handler("visual_concept_card", 1)
    payload = {
        "card_title": "PLS",
        "key_points": ["Vía aérea permeable"],
        "check_question": {
            "question": "¿Cuándo no aplicar?",
            "options": [{"id": "a", "text": "Sin trauma"}, {"id": "b", "text": "Trauma cervical"}],
        },
    }
    answer_key = {"correct_option_id": "b"}
    clean_p, clean_k = handler.validate_definition(payload, answer_key)
    res_ok = handler.evaluate(
        payload_raw=clean_p,
        answer_key_raw=clean_k,
        submission_raw={"selected_option_id": "b"},
        max_points=10,
        is_safety_critical=True,
    )
    assert res_ok.is_correct is True
    assert res_ok.score_awarded == 10

    with pytest.raises(ValidationDomainError):
        handler.validate_definition(payload, {"correct_option_id": "z"})


def test_matching_safety_critical_requires_full_match() -> None:
    handler = get_challenge_handler("matching", 1)
    payload = {
        "instruction": "Empareja",
        "left_items": [{"id": "l1", "text": "Rojo"}, {"id": "l2", "text": "Verde"}],
        "right_items": [{"id": "r1", "text": "Inmediato"}, {"id": "r2", "text": "Leve"}],
    }
    answer_key = {"pairs": {"l1": "r1", "l2": "r2"}}
    res_partial = handler.evaluate(
        payload_raw=payload,
        answer_key_raw=answer_key,
        submission_raw={"pairs": {"l1": "r1", "l2": "r1"}},
        max_points=15,
        is_safety_critical=True,
    )
    assert res_partial.is_correct is False
    assert res_partial.score_awarded == 0


def test_sequence_ordering_cross_rule_and_eval() -> None:
    handler = get_challenge_handler("sequence_ordering", 1)
    payload = {
        "instruction": "Ordena",
        "items": [{"id": "1", "text": "EPP"}, {"id": "2", "text": "Presión"}],
    }
    with pytest.raises(ValidationDomainError):
        handler.validate_definition(payload, {"expected_order": ["1", "99"]})

    res = handler.evaluate(
        payload_raw=payload,
        answer_key_raw={"expected_order": ["1", "2"]},
        submission_raw={"ordered_ids": ["1", "2"]},
        max_points=15,
        is_safety_critical=True,
    )
    assert res.is_correct is True


def test_interactive_zones_coordinates_and_selection() -> None:
    handler = get_challenge_handler("interactive_zones", 1)
    payload = {
        "instruction": "Toca el surco carotídeo",
        "zones": [
            {"id": "z1", "shape": "circle", "x": 0.4, "y": 0.5, "r": 0.1, "label": "Carótida"},
            {"id": "z2", "shape": "rect", "x": 0.6, "y": 0.6, "w": 0.2, "h": 0.2, "label": "Clavícula"},
        ],
    }
    answer_key = {"correct_zone_ids": ["z1"], "accept_coordinates_within_zones": True}
    res_tap = handler.evaluate(
        payload_raw=payload,
        answer_key_raw=answer_key,
        submission_raw={"tap_point": {"x": 0.42, "y": 0.51}},
        max_points=15,
        is_safety_critical=True,
    )
    assert res_tap.is_correct is True


def test_decision_simulation_and_fill_in_blanks() -> None:
    dec_handler = get_challenge_handler("decision_simulation", 1)
    dec_payload = {
        "scenario_context": "Incidente eléctrico",
        "initial_node_id": "n1",
        "nodes": {
            "n1": {
                "narrative": "Cable caído",
                "choices": [{"id": "c1", "text": "Cortar energía", "next_node_id": "end_ok"}],
            },
            "end_ok": {"is_terminal": True, "summary": "Seguro"},
        },
    }
    res_dec = dec_handler.evaluate(
        payload_raw=dec_payload,
        answer_key_raw={"optimal_paths": [["c1"]], "acceptable_terminal_nodes": ["end_ok"]},
        submission_raw={"chosen_sequence": ["c1"]},
        max_points=20,
        is_safety_critical=True,
    )
    assert res_dec.is_correct is True

    fib_handler = get_challenge_handler("fill_in_blanks", 1)
    fib_payload = {
        "template": "Relación {{b1}}:{{b2}}",
        "blanks": [{"id": "b1", "label": "Comp"}, {"id": "b2", "label": "Vent"}],
    }
    fib_key = {
        "blanks": {
            "b1": {"accepted": ["30"], "case_sensitive": False},
            "b2": {"accepted": ["2"], "case_sensitive": False},
        }
    }
    res_fib = fib_handler.evaluate(
        payload_raw=fib_payload,
        answer_key_raw=fib_key,
        submission_raw={"answers": {"b1": " 30 ", "b2": "2"}},
        max_points=10,
        is_safety_critical=True,
    )
    assert res_fib.is_correct is True
