"""Tests for database schema creation and CRUD persistence.

Purpose:
    Validates that tables are created without errors on SQLite,
    supports student insertion, attempt insertion with complete audit fields,
    and reading back stored relations.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    DecisionLog,
    MisconceptionEvent,
)


@pytest.fixture
def test_db():
    """In-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_schema_creation_and_persistence(test_db):
    """Test inserting a user, subject, concept, question, and attempt, then reading it back."""
    # 1. Insert user
    student = User(
        id="student_001",
        role="student",
        name="Alex Student",
        email="alex@test.com",
        password_hash="hashed_pw_dummy",
    )
    test_db.add(student)

    # 2. Insert subject and concept
    subject = Subject(id="physics_10", name="Class 10 Physics")
    concept = Concept(
        id="ohms_law",
        subject_id="physics_10",
        name="Ohm's Law",
        description="Relationship between voltage, current, and resistance",
    )
    test_db.add(subject)
    test_db.add(concept)

    # 3. Insert question and link concept
    question = Question(
        id="q_ohm_01",
        text="A 10 Ohm resistor has 2 A flowing through it. What is the potential difference?",
        answer_key="20",
        answer_type="numeric",
        tolerance=0.1,
        difficulty=1,
        question_type="numerical",
        rubric="V = IR = 2 * 10 = 20 V",
        status="approved",
        reviewed_by="Human Reviewer 1",
    )
    test_db.add(question)
    test_db.flush()

    qc = QuestionConcept(question_id=question.id, concept_id=concept.id)
    test_db.add(qc)

    # 4. Insert attempt
    attempt = Attempt(
        id="att_001",
        student_id=student.id,
        question_id=question.id,
        session_id="sess_01",
        student_answer="20",
        explanation_raw="um using ohms law V equals I times R so 2 times 10 is 20",
        explanation_clean="using ohms law V equals I times R so 2 times 10 is 20",
        correct=True,
        reasoning="sound",
        misconception_id=None,
        evidence=1.0,
        llm_status="ok",
    )
    test_db.add(attempt)

    # 5. Insert learner mastery
    mastery = LearnerMastery(
        student_id=student.id,
        concept_id=concept.id,
        mastery=0.60,
        consecutive_strong=1,
        attempts_count=1,
    )
    test_db.add(mastery)

    # 6. Insert decision log
    log = DecisionLog(
        id="dec_001",
        student_id=student.id,
        decision_type="next_question",
        payload_json={"rule": "weakest_concept", "concept": "ohms_law", "mastery": 0.5},
    )
    test_db.add(log)
    test_db.commit()

    # Query and assert
    fetched_student = test_db.query(User).filter_by(id="student_001").first()
    assert fetched_student is not None
    assert fetched_student.name == "Alex Student"
    assert len(fetched_student.attempts) == 1

    fetched_attempt = test_db.query(Attempt).filter_by(id="att_001").first()
    assert fetched_attempt is not None
    assert fetched_attempt.correct is True
    assert fetched_attempt.evidence == 1.0
    assert fetched_attempt.question.text.startswith("A 10 Ohm resistor")

    fetched_mastery = test_db.query(LearnerMastery).filter_by(student_id="student_001", concept_id="ohms_law").first()
    assert fetched_mastery is not None
    assert fetched_mastery.mastery == 0.60
    assert fetched_mastery.attempts_count == 1

    fetched_dec = test_db.query(DecisionLog).filter_by(id="dec_001").first()
    assert fetched_dec is not None
    assert fetched_dec.payload_json["rule"] == "weakest_concept"
