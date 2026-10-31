"""Revision scheduler implementing spaced repetition intervals.

Purpose:
    Calculates future review schedules for academic concepts based on student mastery,
    correctness of latest attempt, and consecutive strong streaks.

Status:
    Active, Phase 2/3 implementation.

Fail-Closed Behavior:
    - If last answer was incorrect, schedule immediate review (0 days).
    - If mastery is invalid or out-of-range, defaults safely to critical review (1 day).
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import RevisionSchedule

SCHEDULING_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "scheduling.json"


def schedule_revision(
    mastery: float,
    last_result_correct: bool,
    consecutive_strong: int = 0,
) -> Dict[str, Any]:
    """Calculate the number of days until the next review and the firing rule name.

    Specification Rules:
        - incorrect answer                           -> 0 days ('incorrect_same_session')
        - mastery < 0.40                             -> 1 day  ('critical_review_1_day')
        - 0.40 <= mastery < 0.70                     -> 3 days ('reinforce_review_3_days')
        - 0.70 <= mastery < 0.90                     -> 7 days ('consolidation_review_7_days')
        - mastery >= 0.90 and consecutive_strong >=3 -> 14 days ('mastered_review_14_days')
        - mastery >= 0.90 and consecutive_strong < 3 -> 7 days ('consolidation_review_7_days')

    Args:
        mastery: Current student concept mastery in [0.0, 1.0].
        last_result_correct: Whether the most recent attempt on this concept was correct.
        consecutive_strong: Number of consecutive attempts with evidence >= 0.90.

    Returns:
        dict:
            - 'days_until_review': int
            - 'rule': str
    """
    if not last_result_correct:
        return {
            "days_until_review": 0,
            "rule": "incorrect_same_session",
        }

    clamped_m = max(0.0, min(1.0, float(mastery)))

    if clamped_m < 0.40:
        return {
            "days_until_review": 1,
            "rule": "critical_review_1_day",
        }

    if 0.40 <= clamped_m < 0.70:
        return {
            "days_until_review": 3,
            "rule": "reinforce_review_3_days",
        }

    if clamped_m >= 0.90 and consecutive_strong >= 3:
        return {
            "days_until_review": 14,
            "rule": "mastered_review_14_days",
        }

    # Covers 0.70 <= mastery < 0.90 AND mastery >= 0.90 without consecutive streak
    return {
        "days_until_review": 7,
        "rule": "consolidation_review_7_days",
    }


def apply_revision_schedule(
    db: Session,
    student_id: str,
    concept_id: str,
    mastery: float,
    last_result_correct: bool,
    consecutive_strong: int = 0,
    now: Optional[datetime] = None,
) -> RevisionSchedule:
    """Compute and persist the next revision date in the revision_schedule table.

    Args:
        db: Active database session.
        student_id: Target student ID.
        concept_id: Target concept ID.
        mastery: Updated mastery score.
        last_result_correct: Boolean flag from attempt correctness.
        consecutive_strong: Count of consecutive strong attempts.
        now: Reference timestamp (defaults to current UTC time).

    Returns:
        RevisionSchedule: Staged database record.
    """
    ref_time = now if now is not None else datetime.now(timezone.utc)
    schedule_data = schedule_revision(
        mastery=mastery,
        last_result_correct=last_result_correct,
        consecutive_strong=consecutive_strong,
    )

    due_date = ref_time + timedelta(days=schedule_data["days_until_review"])

    record = (
        db.query(RevisionSchedule)
        .filter_by(student_id=student_id, concept_id=concept_id)
        .first()
    )

    reason_payload = {
        "rule": schedule_data["rule"],
        "days_until_review": schedule_data["days_until_review"],
        "mastery": mastery,
        "last_result_correct": last_result_correct,
        "consecutive_strong": consecutive_strong,
    }

    if not record:
        record = RevisionSchedule(
            student_id=student_id,
            concept_id=concept_id,
            due_date=due_date,
            reason_json=reason_payload,
        )
        db.add(record)
    else:
        record.due_date = due_date
        record.reason_json = reason_payload

    return record
