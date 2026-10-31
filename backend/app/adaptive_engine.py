"""Adaptive item selection engine with explainable reason traces.

Purpose:
    Selects the optimal next question for a student based on:
    1. Prerequisite unlock verification (excluding locked concepts).
    2. Overdue revision schedules (spaced repetition priority).
    3. Weakest concept mastery targeting.
    4. Difficulty stepping based on mastery and consecutive performance.
    5. Repetition suppression (avoiding repeats in the last 10 attempts).
    6. Strict approval enforcement: only questions with status='approved' are served.

Status:
    Active, Phase 3 implementation.

Fail-Closed Behavior:
    - If no concepts are unlocked or the question bank is exhausted,
      returns question_id None with reason 'no_eligible_question'.
    - Never serves draft questions to students.
    - Never drops difficulty to 1 for students with mastery above 0.70.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.app.knowledge_graph import knowledge_graph
from backend.app.models import (
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    RevisionSchedule,
)


def select_next_question(
    student_id: str,
    db: Session,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Select the optimal next question for a student and generate a reason trace.

    Algorithm:
        a) Exclude locked concepts (is_unlocked is False).
        b) If any unlocked concept has a revision due today or earlier,
           choose the one with the earliest due date. Rule: 'revision_due'.
        c) Otherwise, choose the unlocked concept with lowest mastery. Rule: 'weakest_concept'.
        d) Difficulty from mastery:
           - Below 0.40 -> 1
           - 0.40 to 0.70 -> 2
           - Above 0.70 -> 3
        e) Raise difficulty one level after 3 consecutive correct answers at current level.
           Never serve difficulty 1 to a student with mastery above 0.70.
        f) Do not repeat any question answered in the last 10 attempts.
        g) If nothing qualifies, return question_id None with reason 'no_eligible_question'.

    Args:
        student_id: Target student identifier.
        db: Active database session.
        now: Optional current timestamp (defaults to UTC now).

    Returns:
        dict:
            - 'question_id': Optional[str]
            - 'concept_id': Optional[str]
            - 'reason': dict with 'rule', 'concept', 'mastery', 'detail'
    """
    ref_time = now if now is not None else datetime.now(timezone.utc)
    # Ensure tz-aware comparison
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    # 1. Fetch student mastery and identify unlocked concepts
    mastery_records = (
        db.query(LearnerMastery)
        .filter(LearnerMastery.student_id == student_id)
        .all()
    )
    mastery_map = {m.concept_id: m.mastery for m in mastery_records}

    all_concepts = knowledge_graph.get_all_concepts()
    unlocked_concept_ids: List[str] = []

    for c in all_concepts:
        cid = c["id"]
        if knowledge_graph.is_unlocked(student_id=student_id, concept_id=cid, mastery_map=mastery_map):
            unlocked_concept_ids.append(cid)

    if not unlocked_concept_ids:
        return {
            "question_id": None,
            "concept_id": None,
            "reason": {
                "rule": "no_eligible_question",
                "concept": "",
                "mastery": 0.0,
                "detail": "All concepts are currently locked behind unfulfilled prerequisites.",
            },
        }

    # 2. Check for due revisions among unlocked concepts
    rev_schedules = (
        db.query(RevisionSchedule)
        .filter(
            RevisionSchedule.student_id == student_id,
            RevisionSchedule.concept_id.in_(unlocked_concept_ids),
        )
        .all()
    )

    overdue_revisions = []
    for sched in rev_schedules:
        due = sched.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due <= ref_time:
            overdue_revisions.append((due, sched.concept_id))

    # Rank unlocked concepts by mastery (ascending)
    ranked_unlocked = []
    for cid in unlocked_concept_ids:
        m = mastery_map.get(cid, 0.50)
        ranked_unlocked.append((m, cid))
    ranked_unlocked.sort(key=lambda x: x[0])

    selected_concept_id: Optional[str] = None
    rule_name: str = ""
    rule_detail: str = ""

    if overdue_revisions:
        # Sort by earliest due date
        overdue_revisions.sort(key=lambda x: x[0])
        selected_concept_id = overdue_revisions[0][1]
        rule_name = "revision_due"
        rule_detail = f"Scheduled spaced revision is due for concept '{selected_concept_id}'."
    else:
        # 3. Otherwise choose unlocked concept with lowest mastery
        selected_concept_id = ranked_unlocked[0][1]
        rule_name = "weakest_concept"
        rule_detail = f"Selected unlocked concept '{selected_concept_id}' with lowest current mastery ({ranked_unlocked[0][0]:.2f})."

    concept_mastery = mastery_map.get(selected_concept_id, 0.50)

    # 4. Determine target difficulty
    if concept_mastery < 0.40:
        target_difficulty = 1
        diff_rule = "mastery_below_0.40_diff_1"
    elif concept_mastery < 0.70:
        target_difficulty = 2
        diff_rule = "mastery_0.40_to_0.70_diff_2"
    else:
        target_difficulty = 3
        diff_rule = "mastery_above_0.70_diff_3"

    # Check recent 3 attempts on this concept for difficulty step-up
    recent_concept_attempts = (
        db.query(Attempt)
        .join(Question, Attempt.question_id == Question.id)
        .join(QuestionConcept, Question.id == QuestionConcept.question_id)
        .filter(
            Attempt.student_id == student_id,
            QuestionConcept.concept_id == selected_concept_id,
        )
        .order_by(Attempt.created_at.desc())
        .limit(3)
        .all()
    )

    if (
        len(recent_concept_attempts) == 3
        and all(a.correct for a in recent_concept_attempts)
        and target_difficulty < 3
    ):
        target_difficulty += 1
        diff_rule += "_stepped_up_streak"

    # Enforce guardrail: Never serve difficulty 1 to mastery > 0.70
    if concept_mastery >= 0.70 and target_difficulty < 2:
        target_difficulty = 2

    rule_detail += f" Target difficulty: {target_difficulty} ({diff_rule})."

    # 5. Get recent 10 attempts to suppress immediate repetitions
    recent_10_attempts = (
        db.query(Attempt.question_id)
        .filter(Attempt.student_id == student_id)
        .order_by(Attempt.created_at.desc())
        .limit(10)
        .all()
    )
    suppressed_ids = {r[0] for r in recent_10_attempts}

    # 6. Query approved candidate questions for this concept
    def find_question_for_concept(cid: str, preferred_diff: int) -> Optional[Question]:
        base_query = (
            db.query(Question)
            .join(QuestionConcept, Question.id == QuestionConcept.question_id)
            .filter(
                QuestionConcept.concept_id == cid,
                Question.status == "approved",
            )
        )
        if suppressed_ids:
            base_query = base_query.filter(Question.id.notin_(suppressed_ids))

        # Try exact difficulty first
        q_exact = base_query.filter(Question.difficulty == preferred_diff).first()
        if q_exact:
            return q_exact

        # If mastery >= 0.70, never allow difficulty 1
        if concept_mastery >= 0.70:
            return base_query.filter(Question.difficulty >= 2).first()

        # Fallback to any difficulty
        return base_query.first()

    chosen_question = find_question_for_concept(selected_concept_id, target_difficulty)

    # If no question available for this concept, check other unlocked concepts by ascending mastery
    if not chosen_question:
        for other_m, other_cid in ranked_unlocked:
            if other_cid == selected_concept_id:
                continue
            other_diff = 1 if other_m < 0.40 else (2 if other_m < 0.70 else 3)
            # Enforce guardrail: Never serve difficulty 1 to mastery >= 0.70
            if other_m >= 0.70 and other_diff < 2:
                other_diff = 2

            q_alt = find_question_for_concept(other_cid, other_diff)
            if q_alt:
                chosen_question = q_alt
                selected_concept_id = other_cid
                concept_mastery = other_m
                rule_name = "weakest_concept_fallback"
                rule_detail = f"Primary concept bank exhausted. Selected next available weakest concept '{other_cid}'."
                break

    if not chosen_question:
        return {
            "question_id": None,
            "concept_id": selected_concept_id,
            "reason": {
                "rule": "no_eligible_question",
                "concept": selected_concept_id or "",
                "mastery": concept_mastery,
                "detail": "All approved questions for available concepts were either answered recently or do not exist.",
            },
        }

    return {
        "question_id": chosen_question.id,
        "concept_id": selected_concept_id,
        "reason": {
            "rule": rule_name,
            "concept": selected_concept_id,
            "mastery": concept_mastery,
            "detail": rule_detail,
        },
    }
