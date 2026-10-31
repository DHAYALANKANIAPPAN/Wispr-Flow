"""Tests for evaluate_answer, deterministic correctness, and fail-closed evaluation.

Purpose:
    Validates that:
    1. Numeric correctness adheres to answer_key and tolerance.
    2. Explanations under 5 words yield reasoning 'none', misconception None, llm_status 'skipped'.
    3. LLM exceptions fail closed to llm_status 'unavailable'.
    4. Invalid JSON / unknown IDs coerce to 'NONE'.
    5. Evidence scores accurately map to config/evaluation.json.
    6. LLM can NEVER flip a correct answer to incorrect or vice versa.
"""

import pytest
from backend.app.evaluation import (
    evaluate_answer,
    check_deterministic_correctness,
    compute_evidence_score,
)

SAMPLE_NUMERIC_Q = {
    "id": "q_test_num",
    "text": "A 10 Ohm resistor has 2 A current. What is the potential difference?",
    "answer_key": "20",
    "answer_type": "numeric",
    "tolerance": 0.5,
}

SAMPLE_TEXT_Q = {
    "id": "q_test_text",
    "text": "Does electric current get consumed by components in a series circuit?",
    "answer_key": "no",
    "answer_type": "text",
}


def test_correct_numeric_answer_sound_reasoning():
    """Correct numeric answer with sound reasoning yields evidence 1.0 and correct=True."""
    def mock_llm(**kwargs):
        return {"reasoning": "sound", "misconception_id": "NONE"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20 V",
        explanation="According to Ohm's law V equals I times R so 2 times 10 is 20",
        llm_callable=mock_llm,
    )
    assert res["correct"] is True
    assert res["reasoning"] == "sound"
    assert res["misconception_id"] is None
    assert res["evidence"] == 1.0
    assert res["llm_status"] == "ok"


def test_correct_with_weak_explanation():
    """Correct answer with weak reasoning yields evidence 0.7."""
    def mock_llm(**kwargs):
        return {"reasoning": "weak", "misconception_id": "NONE"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20",
        explanation="I multiplied the numbers given in the problem statement to get twenty",
        llm_callable=mock_llm,
    )
    assert res["correct"] is True
    assert res["reasoning"] == "weak"
    assert res["evidence"] == 0.7
    assert res["llm_status"] == "ok"


def test_incorrect_with_misconception():
    """Incorrect answer with detected misconception yields evidence 0.0."""
    def mock_llm(**kwargs):
        return {"reasoning": "none", "misconception_id": "MC_PROPORTIONAL_I_R"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="50",
        explanation="Current increases because resistance is higher so voltage must be 50",
        llm_callable=mock_llm,
    )
    assert res["correct"] is False
    assert res["misconception_id"] == "MC_PROPORTIONAL_I_R"
    assert res["evidence"] == 0.0
    assert "inversely proportional" in res["feedback"]


def test_incorrect_with_unclear_explanation():
    """Incorrect answer with no misconception yields evidence 0.3."""
    def mock_llm(**kwargs):
        return {"reasoning": "none", "misconception_id": "NONE"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="50",
        explanation="I am not sure how the circuit behaves so I just guessed fifty",
        llm_callable=mock_llm,
    )
    assert res["correct"] is False
    assert res["misconception_id"] is None
    assert res["evidence"] == 0.3


def test_explanation_under_5_words_is_none_never_weak():
    """An explanation under 5 words must be reasoning 'none', never 'weak', and skipped."""
    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20",
        explanation="just ohms law",  # 3 words
    )
    assert res["correct"] is True
    assert res["reasoning"] == "none"
    assert res["misconception_id"] is None
    assert res["evidence"] == 0.8  # correct + none
    assert res["llm_status"] == "skipped"


def test_empty_explanation():
    """Empty explanation yields reasoning 'none', evidence 0.8 for correct, skipped status."""
    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20",
        explanation="",
    )
    assert res["correct"] is True
    assert res["reasoning"] == "none"
    assert res["llm_status"] == "skipped"
    assert res["evidence"] == 0.8


def test_llm_exception_fails_closed():
    """When LLM raises exception or times out, system fails closed with llm_status 'unavailable'."""
    def failing_llm(**kwargs):
        raise ConnectionError("LLM API endpoint connection timeout")

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20",
        explanation="Using V equals I times R the answer is twenty volts",
        llm_callable=failing_llm,
    )
    assert res["correct"] is True
    assert res["reasoning"] == "none"
    assert res["misconception_id"] is None
    assert res["llm_status"] == "unavailable"
    assert res["evidence"] == 0.8


def test_invalid_json_fails_closed():
    """When LLM returns invalid output structure, fails closed."""
    def invalid_llm(**kwargs):
        return "Not a dictionary"  # type: ignore

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="20",
        explanation="Using V equals I times R the answer is twenty volts",
        llm_callable=invalid_llm,
    )
    assert res["llm_status"] == "invalid_output"
    assert res["reasoning"] == "none"
    assert res["misconception_id"] is None


def test_unknown_misconception_id_coerces_to_none():
    """Unknown misconception IDs returned by LLM coerce to None."""
    def rogue_llm(**kwargs):
        return {"reasoning": "none", "misconception_id": "MC_MADE_UP_HALLUCINATED_ID"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="50",
        explanation="A detailed explanation with more than five words that hallucinated an ID",
        llm_callable=rogue_llm,
    )
    assert res["correct"] is False
    assert res["misconception_id"] is None
    assert res["evidence"] == 0.3  # incorrect + none


def test_llm_cannot_flip_correctness():
    """The LLM can never flip a correct answer to incorrect or vice versa."""
    # Student answer is wrong, but LLM claims reasoning is sound
    def contradictory_llm(**kwargs):
        return {"reasoning": "sound", "misconception_id": "NONE"}

    res = evaluate_answer(
        question=SAMPLE_NUMERIC_Q,
        student_answer="999",  # incorrect
        explanation="I am completely certain the answer is twenty because V equals IR",
        llm_callable=contradictory_llm,
    )
    assert res["correct"] is False  # Correctness is deterministic, not from LLM!
