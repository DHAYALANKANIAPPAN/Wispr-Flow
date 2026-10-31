"""Tests for controlled misconception taxonomy and validation rules.

Purpose:
    Validates that each controlled ID is registered,
    unrecognized IDs coerce to 'NONE',
    explanations under 5 words return 'NONE',
    known misconceptions are detected, and non-misconceptions (e.g. resistance blocking charge) produce 'NONE'.
"""

from backend.app.misconceptions import (
    CONTROLLED_IDS,
    load_misconceptions,
    validate_misconception_id,
    is_valid_misconception_id,
    detect_rule_based_misconception,
)


def test_each_id_has_valid_record():
    """Verify each controlled ID is present in the taxonomy with required fields."""
    taxonomy = load_misconceptions()
    for mid in CONTROLLED_IDS:
        assert mid in taxonomy, f"Missing record for controlled ID: {mid}"
        rec = taxonomy[mid]
        assert "name" in rec
        assert "description" in rec


def test_unknown_id_coerces_to_none():
    """Any arbitrary or unapproved misconception ID must fail closed to 'NONE'."""
    assert validate_misconception_id("MC_GRAVITATIONAL_PULL") == "NONE"
    assert validate_misconception_id("") == "NONE"
    assert validate_misconception_id(None) == "NONE"
    assert validate_misconception_id("RANDOM_TEXT") == "NONE"

    assert is_valid_misconception_id("MC_GRAVITATIONAL_PULL") is False
    assert is_valid_misconception_id("MC_PROPORTIONAL_I_R") is True


def test_no_explanation_produces_none():
    """Empty explanation or explanation with no text produces 'NONE'."""
    assert detect_rule_based_misconception("") == "NONE"
    assert detect_rule_based_misconception(None) == "NONE"
    assert detect_rule_based_misconception("yes 5") == "NONE"  # < 5 words


def test_proportional_i_r_detected():
    """'Current increases because resistance is higher' produces MC_PROPORTIONAL_I_R."""
    explanation = "Current increases because resistance is higher in this circuit branch"
    detected = detect_rule_based_misconception(explanation)
    assert detected == "MC_PROPORTIONAL_I_R"


def test_charge_blocking_produces_none():
    """'Current decreases because resistance blocks the movement of charge' produces NONE."""
    explanation = "Current decreases because resistance blocks the movement of charge through the wire"
    detected = detect_rule_based_misconception(explanation)
    assert detected == "NONE"
