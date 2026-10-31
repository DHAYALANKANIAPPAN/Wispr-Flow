"""Deterministic answer checker and fail-closed reasoning evaluator.

Purpose:
    Performs a deterministic correctness check against answer keys,
    evaluates student reasoning via LLM or rule-based fallback,
    maps to controlled misconceptions, computes evidence scores,
    and produces student-facing feedback.

Status:
    Active, Phase 2 implementation.

Fail-Closed Behavior:
    - The LLM NEVER determines correctness; correctness is strictly deterministic.
    - If explanation is under 5 words, reasoning is set to 'none' (never 'weak'),
      misconception_id is None, and llm_status is 'skipped'.
    - If the LLM throws an exception, times out, or returns invalid JSON/keys,
      the system fails closed: reasoning='none', misconception_id=None,
      and llm_status is 'unavailable' or 'invalid_output'.
    - The LLM can never flip a correct answer to incorrect, or vice-versa.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import httpx

from backend.app.text_clean import normalize_explanation
from backend.app.misconceptions import (
    validate_misconception_id,
    detect_rule_based_misconception,
    get_all_misconceptions,
)

EVAL_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "evaluation.json"


def load_evidence_weights() -> Dict[str, float]:
    """Load evidence score weights from config/evaluation.json."""
    if not EVAL_CONFIG_PATH.exists():
        return {
            "correct_sound": 1.0,
            "correct_none": 0.8,
            "correct_weak": 0.7,
            "incorrect_none": 0.3,
            "incorrect_misconception": 0.0,
        }
    with open(EVAL_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("weights", {})


_WEIGHTS = load_evidence_weights()


def check_deterministic_correctness(
    student_answer: str,
    answer_key: str,
    answer_type: str,
    tolerance: Optional[float] = 0.0,
) -> bool:
    """Evaluate answer correctness deterministically against the ground truth key.

    Args:
        student_answer: Raw string submitted by the student.
        answer_key: Canonical correct answer string.
        answer_type: 'numeric' or 'text'.
        tolerance: Allowed absolute numeric error.

    Returns:
        bool: True if correct, False otherwise.
    """
    if student_answer is None or answer_key is None:
        return False

    s_clean = str(student_answer).strip()
    k_clean = str(answer_key).strip()

    if answer_type == "numeric":
        try:
            # Extract leading floating point number if units attached (e.g. '20 V' -> 20.0)
            s_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s_clean)
            k_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", k_clean)
            if not s_match or not k_match:
                return False

            s_val = float(s_match.group(0))
            k_val = float(k_match.group(0))
            tol = float(tolerance) if tolerance is not None else 0.0
            return abs(s_val - k_val) <= tol
        except (ValueError, TypeError):
            return False

    elif answer_type == "text":
        # Normalize whitespace and casing
        norm_s = " ".join(s_clean.lower().split())
        norm_k = " ".join(k_clean.lower().split())
        return norm_s == norm_k

    return False


def compute_evidence_score(
    correct: bool,
    reasoning: str,
    misconception_id: Optional[str],
) -> float:
    """Compute evidence score based on correctness and reasoning evaluation.

    Weights read from config/evaluation.json:
        correct + sound            -> 1.0
        correct + none             -> 0.8
        correct + weak             -> 0.7
        incorrect + None           -> 0.3
        incorrect + misconception  -> 0.0

    Args:
        correct: Deterministic correctness boolean.
        reasoning: 'sound' | 'weak' | 'none'.
        misconception_id: Detected misconception ID or None.

    Returns:
        float: Computed evidence score.
    """
    if correct:
        if reasoning == "sound":
            return _WEIGHTS.get("correct_sound", 1.0)
        elif reasoning == "weak":
            return _WEIGHTS.get("correct_weak", 0.7)
        else:
            return _WEIGHTS.get("correct_none", 0.8)
    else:
        if misconception_id is not None and misconception_id != "NONE":
            return _WEIGHTS.get("incorrect_misconception", 0.0)
        return _WEIGHTS.get("incorrect_none", 0.3)


def build_feedback(
    correct: bool,
    reasoning: str,
    misconception_id: Optional[str],
    question_text: str,
    answer_key: str,
) -> str:
    """Generate concise student-facing feedback without inventing misconceptions.

    Args:
        correct: Deterministic correctness flag.
        reasoning: 'sound' | 'weak' | 'none'.
        misconception_id: Detected misconception ID or None.
        question_text: Question prompt text.
        answer_key: Canonical correct answer.

    Returns:
        str: Constructive feedback text.
    """
    if correct:
        if reasoning == "sound":
            return "Correct! Your reasoning is sound and well-explained."
        elif reasoning == "weak":
            return f"Correct! The answer is {answer_key}. Your reasoning was partially supported; make sure to relate all key variables."
        else:
            return f"Correct! The answer is {answer_key}."

    # Incorrect cases
    if misconception_id == "MC_PROPORTIONAL_I_R":
        return f"Incorrect. Remember that Current and Resistance are inversely proportional at constant voltage: I = V/R, so higher resistance reduces current."
    elif misconception_id == "MC_RESISTANCE_RISES_WITH_I":
        return f"Incorrect. At constant temperature, a resistor's resistance is a fixed physical property (R = rho * L / A), not something that increases with current."
    elif misconception_id == "MC_CURRENT_USED_UP":
        return f"Incorrect. Electric current is the continuous rate of charge flow and is never consumed or used up by circuit components."
    elif misconception_id == "MC_VOLTAGE_SPLITS_PARALLEL":
        return f"Incorrect. In parallel circuits, all branches connect across the same two common nodes, so potential difference (voltage) is identical across each branch."
    elif misconception_id == "MC_POWER_IS_ENERGY":
        return f"Incorrect. Power is the rate of energy transfer in Watts (Joules per second), while energy is the total work done measured in Joules."

    return f"Incorrect. The expected answer is {answer_key}. Review the governing formula and definitions."


def _call_llm_reasoning(
    question_text: str,
    answer_key: str,
    student_answer: str,
    cleaned_explanation: str,
) -> Dict[str, Any]:
    """Call the external LLM provider to evaluate reasoning.

    Returns dict with raw LLM response or raises exception on failure.
    """
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY environment variable is not configured")

    system_prompt = (
        "You are an expert Physics tutor evaluator for CBSE Class 10 Electricity.\n"
        "The explanation was dictated by voice and may contain transcription errors or filler. "
        "Judge the reasoning, not the wording. "
        "Choose exactly one misconception_id from the list, or NONE.\n"
        "Allowed misconception IDs:\n"
        "- MC_PROPORTIONAL_I_R (believes current and resistance are directly proportional)\n"
        "- MC_RESISTANCE_RISES_WITH_I (believes resistance rises with current at constant V)\n"
        "- MC_CURRENT_USED_UP (believes current is consumed by components in circuit)\n"
        "- MC_VOLTAGE_SPLITS_PARALLEL (believes voltage divides across parallel branches)\n"
        "- MC_POWER_IS_ENERGY (confuses power Watts with energy Joules)\n"
        "- NONE (sound, incomplete, or ambiguous reasoning)\n"
        "Rate reasoning as sound, weak, or none.\n"
        "Return JSON only with keys: 'reasoning' ('sound'|'weak'|'none') and 'misconception_id' (string)."
    )

    prompt = (
        f"Question: {question_text}\n"
        f"Correct Answer: {answer_key}\n"
        f"Student Answer: {student_answer}\n"
        f"Student Explanation: {cleaned_explanation}\n"
    )

    # Standard OpenAI-compatible format
    endpoint = os.getenv("LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    payload = {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        res_json = response.json()
        content_text = res_json["choices"][0]["message"]["content"]
        return json.loads(content_text)


def evaluate_answer(
    question: Dict[str, Any],
    student_answer: str,
    explanation: str,
    llm_callable: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluate student answer deterministically, classify reasoning, and compute evidence.

    Fixed Contract:
        returns {
            "correct": bool,
            "reasoning": "sound" | "weak" | "none",
            "misconception_id": str | None,
            "evidence": float,
            "llm_status": "ok" | "unavailable" | "invalid_output" | "skipped",
            "feedback": str
        }

    Args:
        question: Question metadata dictionary containing text, answer_key, answer_type, tolerance.
        student_answer: Student submitted answer string.
        explanation: Student submitted reasoning explanation string.
        llm_callable: Optional callable override for testing LLM interaction.

    Returns:
        dict: Complete evaluation payload.
    """
    # 1. Deterministic correctness check (LLM never decides this)
    correct = check_deterministic_correctness(
        student_answer=student_answer,
        answer_key=question.get("answer_key", ""),
        answer_type=question.get("answer_type", "text"),
        tolerance=question.get("tolerance", 0.0),
    )

    # 2. Normalize explanation
    clean_res = normalize_explanation(explanation)
    clean_text = clean_res["clean"]
    word_count = clean_res["word_count"]

    reasoning = "none"
    misconception_id: Optional[str] = None
    llm_status = "skipped"

    # 3. Reasoning classification
    if word_count < 5:
        # Contract: An explanation under 5 words is reasoning "none", never "weak".
        reasoning = "none"
        misconception_id = None
        llm_status = "skipped"
    else:
        # Attempt LLM evaluation
        eval_fn = llm_callable if llm_callable is not None else _call_llm_reasoning
        try:
            llm_result = eval_fn(
                question_text=question.get("text", ""),
                answer_key=question.get("answer_key", ""),
                student_answer=student_answer,
                cleaned_explanation=clean_text,
            )

            if not isinstance(llm_result, dict):
                llm_status = "invalid_output"
            else:
                raw_reasoning = str(llm_result.get("reasoning", "")).lower()
                if raw_reasoning in {"sound", "weak", "none"}:
                    reasoning = raw_reasoning
                else:
                    reasoning = "none"

                raw_mid = llm_result.get("misconception_id")
                validated_mid = validate_misconception_id(raw_mid)
                misconception_id = None if validated_mid == "NONE" else validated_mid
                llm_status = "ok"

        except Exception:
            # Fail closed: LLM unavailable or crashed
            # Fall back to deterministic rule-based misconception detection
            fallback_mid = detect_rule_based_misconception(clean_text)
            validated_fallback = validate_misconception_id(fallback_mid)

            misconception_id = None if validated_fallback == "NONE" else validated_fallback
            reasoning = "none"
            llm_status = "unavailable"

    # 4. Compute evidence score
    evidence = compute_evidence_score(
        correct=correct,
        reasoning=reasoning,
        misconception_id=misconception_id,
    )

    # 5. Build feedback
    feedback = build_feedback(
        correct=correct,
        reasoning=reasoning,
        misconception_id=misconception_id,
        question_text=question.get("text", ""),
        answer_key=question.get("answer_key", ""),
    )

    return {
        "correct": correct,
        "reasoning": reasoning,
        "misconception_id": misconception_id,
        "evidence": evidence,
        "llm_status": llm_status,
        "feedback": feedback,
    }
