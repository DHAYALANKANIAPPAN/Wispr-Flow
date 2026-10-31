"""Tests for adaptive item selection engine and explainable reason traces.

Purpose:
    Validates all question selection policies:
    1. Weakest unlocked concept is prioritized.
    2. Locked concepts (with unmet prerequisites) are skipped.
    3. Overdue revisions take precedence over weakest concepts.
    4. Difficulty steps up after 3 consecutive correct answers.
    5. Difficulty never drops to 1 for mastery >= 0.70.
    6. Questions answered in the last 10 attempts are avoided.
    7. Empty or exhausted bank returns question_id=None without crashing.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import (
    User,
    Subject,
    Concept,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    RevisionSchedule,
)
from backend.app.adaptive_engine import select_next_question


@pytest.fixture
def adaptive_db():
    """In-memory SQLite session with full electricity curriculum and question bank."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Create Subject & 3 concepts
    subject = Subject(id="physics_cbse_10", name="CBSE Class 10 Physics")
    c1 = Concept(id="electric_current", subject_id="physics_cbse_10", name="Electric Current")
    c2 = Concept(id="potential_difference", subject_id="physics_cbse_10", name="Potential Difference")
    c3 = Concept(id="resistance", subject_id="physics_cbse_10", name="Resistance")
    c4 = Concept(id="ohms_law", subject_id="physics_cbse_10", name="Ohm's Law")
    session.add_all([subject, c1, c2, c3, c4])

    # Add questions
    # q1: electric_current, diff 1
    q1 = Question(
        id="q_curr_01",
        text="What is current formula?",
        answer_key="Q/t",
        answer_type="text",
        difficulty=1,
        question_type="conceptual",
        status="approved",
    )
    # q2: electric_current, diff 2
    q2 = Question(
        id="q_curr_02",
        text="Calculate current for 10 C in 2 s",
        answer_key="5",
        answer_type="numeric",
        tolerance=0.1,
        difficulty=2,
        question_type="numerical",
        status="approved",
    )
    # q3: potential_difference, diff 1
    q3 = Question(
        id="q_pd_01",
        text="What is potential difference formula?",
        answer_key="W/Q",
        answer_type="text",
        difficulty=1,
        question_type="conceptual",
        status="approved",
    )
    # q4: resistance, diff 3
    q4 = Question(
        id="q_res_03",
        text="Resistance calculation",
        answer_key="10",
        answer_type="numeric",
        difficulty=3,
        question_type="numerical",
        status="approved",
    )
    # q5: resistance, diff 1 (trap check for mastery > 0.70)
    q5 = Question(
        id="q_res_01",
        text="Define resistance",
        answer_key="opposition to current",
        answer_type="text",
        difficulty=1,
        question_type="conceptual",
        status="approved",
    )
    # q6: potential_difference, diff 3
    q6 = Question(
        id="q_pd_03",
        text="High difficulty potential difference",
        answer_key="24",
        answer_type="numeric",
        difficulty=3,
        question_type="numerical",
        status="approved",
    )
    # q_draft: draft question (must NEVER be served)
    q_draft = Question(
        id="q_draft_01",
        text="Draft question not approved",
        answer_key="draft",
        answer_type="text",
        difficulty=1,
        question_type="conceptual",
        status="draft",
    )
    session.add_all([q1, q2, q3, q4, q5, q6, q_draft])
    session.flush()

    session.add(QuestionConcept(question_id=q1.id, concept_id="electric_current"))
    session.add(QuestionConcept(question_id=q2.id, concept_id="electric_current"))
    session.add(QuestionConcept(question_id=q3.id, concept_id="potential_difference"))
    session.add(QuestionConcept(question_id=q6.id, concept_id="potential_difference"))
    session.add(QuestionConcept(question_id=q4.id, concept_id="resistance"))
    session.add(QuestionConcept(question_id=q5.id, concept_id="resistance"))
    session.add(QuestionConcept(question_id=q_draft.id, concept_id="electric_current"))

    # Create Student
    student = User(id="s_adapt_test", role="student", name="Adaptive Student", email="adapt@test.com", password_hash="dummy")
    session.add(student)
    session.commit()

    yield session
    session.close()


def test_weakest_unlocked_concept_chosen(adaptive_db):
    """Student with low mastery on electric_current (0.30) vs potential_difference (0.60) gets electric_current."""
    student_id = "s_adapt_test"
    adaptive_db.add_all([
        LearnerMastery(student_id=student_id, concept_id="electric_current", mastery=0.30),
        LearnerMastery(student_id=student_id, concept_id="potential_difference", mastery=0.60),
    ])
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    assert res["question_id"] == "q_curr_01"  # difficulty 1 for mastery 0.30
    assert res["concept_id"] == "electric_current"
    assert res["reason"]["rule"] == "weakest_concept"


def test_locked_concept_skipped(adaptive_db):
    """ohms_law is locked initially; engine must never choose questions from ohms_law."""
    student_id = "s_adapt_test"
    # Even if ohms_law has 0.10 mastery (recorded hypothetically), it is locked
    adaptive_db.add(LearnerMastery(student_id=student_id, concept_id="ohms_law", mastery=0.10))
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    assert res["concept_id"] != "ohms_law"
    assert res["concept_id"] in ["electric_current", "potential_difference", "resistance"]


def test_due_revision_beats_weakest(adaptive_db):
    """An overdue revision on potential_difference (mastery 0.75) takes priority over weaker concept (0.35)."""
    student_id = "s_adapt_test"
    now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    yesterday = now - timedelta(days=1)

    adaptive_db.add_all([
        LearnerMastery(student_id=student_id, concept_id="electric_current", mastery=0.35),
        LearnerMastery(student_id=student_id, concept_id="potential_difference", mastery=0.75),
        RevisionSchedule(student_id=student_id, concept_id="potential_difference", due_date=yesterday, reason_json={}),
    ])
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db, now=now)
    assert res["concept_id"] == "potential_difference"
    assert res["reason"]["rule"] == "revision_due"


def test_difficulty_stepping_after_streak(adaptive_db):
    """After 3 consecutive correct answers, difficulty increases by 1."""
    student_id = "s_adapt_test"
    # Mastery 0.35 -> base difficulty is 1
    adaptive_db.add(LearnerMastery(student_id=student_id, concept_id="electric_current", mastery=0.35))
    adaptive_db.commit()

    # Add 3 consecutive correct attempts on electric_current
    for i in range(3):
        adaptive_db.add(Attempt(
            student_id=student_id,
            question_id="q_curr_01",
            student_answer="Q/t",
            correct=True,
            reasoning="sound",
            evidence=1.0,
            llm_status="ok",
        ))
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    # Difficulty should have stepped up from 1 to 2 -> q_curr_02
    assert res["question_id"] == "q_curr_02"
    assert "stepped_up_streak" in res["reason"]["detail"]


def test_difficulty_never_drops_to_1_for_mastery_above_0_70(adaptive_db):
    """For mastery >= 0.70, difficulty 1 is forbidden; difficulty 3 question must be served."""
    student_id = "s_adapt_test"
    adaptive_db.add_all([
        LearnerMastery(student_id=student_id, concept_id="electric_current", mastery=0.95),
        LearnerMastery(student_id=student_id, concept_id="potential_difference", mastery=0.90),
        LearnerMastery(student_id=student_id, concept_id="resistance", mastery=0.85),
    ])
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    assert res["concept_id"] == "resistance"
    assert res["question_id"] == "q_res_03"  # difficulty 3 chosen, q_res_01 (diff 1) is forbidden


def test_repeats_in_last_10_attempts_avoided(adaptive_db):
    """If q_curr_01 was answered in the last 10 attempts, it should not be served again."""
    student_id = "s_adapt_test"
    adaptive_db.add(LearnerMastery(student_id=student_id, concept_id="electric_current", mastery=0.30))
    adaptive_db.add(Attempt(
        student_id=student_id,
        question_id="q_curr_01",
        student_answer="Q/t",
        correct=True,
        reasoning="sound",
        evidence=1.0,
        llm_status="ok",
    ))
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    # q_curr_01 is suppressed, so q_curr_02 (difficulty 2) should be picked
    assert res["question_id"] == "q_curr_02"


def test_empty_bank_returns_no_eligible_question(adaptive_db):
    """When all questions are answered or none exist, returns question_id=None without crashing."""
    student_id = "s_adapt_test"
    # Suppress all questions in DB
    all_qs = adaptive_db.query(Question).all()
    for q in all_qs:
        adaptive_db.add(Attempt(
            student_id=student_id,
            question_id=q.id,
            student_answer="ans",
            correct=True,
            reasoning="sound",
            evidence=1.0,
            llm_status="ok",
        ))
    adaptive_db.commit()

    res = select_next_question(student_id=student_id, db=adaptive_db)
    assert res["question_id"] is None
    assert res["reason"]["rule"] == "no_eligible_question"
