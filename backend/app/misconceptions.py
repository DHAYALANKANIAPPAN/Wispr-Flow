"""Controlled misconception taxonomy and validation engine.

Purpose:
    Enforces a strict, closed vocabulary of diagnostic misconceptions.
    Validates LLM outputs against the controlled list and provides
    fail-closed fallback classification.

Status:
    Active, Phase 2 implementation.

Fail-Closed Behavior:
    - Any unrecognized misconception ID returned by the LLM is coerced to 'NONE'.
    - An empty explanation or explanation under 5 words always produces 'NONE'.
    - Non-misconception conceptual descriptions (e.g. resistance opposing charge) produce 'NONE'.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

MISCONCEPTIONS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "content"
    / "electricity"
    / "misconceptions.json"
)

# Canonical controlled IDs
CONTROLLED_IDS = {
    "MC_PROPORTIONAL_I_R",
    "MC_RESISTANCE_RISES_WITH_I",
    "MC_CURRENT_USED_UP",
    "MC_VOLTAGE_SPLITS_PARALLEL",
    "MC_POWER_IS_ENERGY",
    "NONE",
}


def load_misconceptions() -> Dict[str, Dict[str, Any]]:
    """Load controlled misconceptions from content/electricity/misconceptions.json.

    Returns:
        dict: Mapping of misconception ID to metadata dict.
    """
    if not MISCONCEPTIONS_PATH.exists():
        return {mid: {"id": mid, "name": mid, "description": ""} for mid in CONTROLLED_IDS}

    with open(MISCONCEPTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {item["id"]: item for item in data.get("controlled_misconceptions", [])}


_TAXONOMY = load_misconceptions()


def get_all_misconceptions() -> List[Dict[str, Any]]:
    """Return list of all registered controlled misconceptions."""
    return list(_TAXONOMY.values())


def is_valid_misconception_id(candidate: Optional[str]) -> bool:
    """Check if a given string is in the controlled misconception vocabulary.

    Args:
        candidate: Candidate misconception ID string.

    Returns:
        bool: True if recognized, False otherwise.
    """
    if not candidate or not isinstance(candidate, str):
        return False
    return candidate.strip().upper() in CONTROLLED_IDS


def validate_misconception_id(candidate: Optional[str]) -> str:
    """Validate and sanitize a candidate misconception ID.

    Fail-closed policy:
        If candidate is None, empty, or not in the controlled list, returns 'NONE'.

    Args:
        candidate: Raw candidate ID from LLM or heuristic.

    Returns:
        str: Validated misconception ID or 'NONE'.
    """
    if not candidate or not isinstance(candidate, str):
        return "NONE"

    cleaned = candidate.strip().upper()
    if cleaned in CONTROLLED_IDS:
        return cleaned

    return "NONE"


def detect_rule_based_misconception(explanation: Optional[str]) -> str:
    """Deterministic rule-based fallback detector for student explanations.

    Used when LLM is unavailable or for deterministic baseline comparisons.

    Args:
        explanation: Student explanation text.

    Returns:
        str: Recognized misconception ID from controlled list, or 'NONE'.
    """
    if not explanation or not isinstance(explanation, str):
        return "NONE"

    text = explanation.lower().strip()
    words = text.split()
    if len(words) < 5:
        return "NONE"

    # Trap case: 'resistance blocks the movement of charge' is NOT a misconception
    if "blocks" in text and "movement of charge" in text:
        return "NONE"
    if "opposes the flow" in text:
        return "NONE"

    # MC_PROPORTIONAL_I_R: Current increases because resistance increases/higher
    if re.search(r"\b(current\s+increases|more\s+current)\b.*?\b(resistance\s+(is\s+)?(higher|increases|doubled|more))\b", text) or \
       re.search(r"\b(resistance\s+(is\s+)?(higher|increases))\b.*?\b(current\s+increases|more\s+current)\b", text):
        return "MC_PROPORTIONAL_I_R"

    # MC_RESISTANCE_RISES_WITH_I: Resistance rises when current rises at constant V
    if re.search(r"\bresistance\s+(rises|increases)\b.*?\b(when|as)\s+current\s+(rises|increases)\b", text):
        return "MC_RESISTANCE_RISES_WITH_I"

    # MC_CURRENT_USED_UP: Current is consumed / used up by components
    if re.search(r"\b(consumed|used\s+up|lost)\b.*?\bcurrent\b", text) or \
       re.search(r"\bcurrent\s+is\s+(consumed|used\s+up|lost)\b", text):
        return "MC_CURRENT_USED_UP"

    # MC_VOLTAGE_SPLITS_PARALLEL: Voltage divides/splits in parallel branches
    if re.search(r"\b(voltage|potential\s+difference)\s+(splits|divides|halved)\b.*?\bparallel\b", text) or \
       re.search(r"\bparallel\b.*?\b(voltage|potential\s+difference)\s+(splits|divides|halved)\b", text):
        return "MC_VOLTAGE_SPLITS_PARALLEL"

    # MC_POWER_IS_ENERGY: Confuses power with energy
    if re.search(r"\b(power\s+is\s+energy|watt\s+is\s+joule|consumed\s+\d+\s+joules\s+because\s+\d+\s+watt)\b", text):
        return "MC_POWER_IS_ENERGY"

    return "NONE"
