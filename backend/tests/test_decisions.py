"""Tests for decision trace logging and retrieval.

Purpose:
    Validates that each decision type is recorded properly with its JSON payload,
    can be queried back per student, and invalid inputs fail closed.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import User, DecisionLog
from backend.app.decisions import (
    log_decision,
    get_student_decisions,
    VALID_DECISION_TYPES,
)


@pytest.fixture
def test_db():
    """In-memory SQLite database session fixture."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Create dummy student
    student = User(
        id="student_decision_test",
        role="student",
        name="Decision Test Student",
        email="dec_student@test.com",
        password_hash="dummy",
    )
    session.add(student)
    session.commit()

    yield session
    session.close()


def test_each_decision_type_written_and_read_back(test_db):
    """Test that all defined decision types can be written and retrieved accurately."""
    student_id = "student_decision_test"

    payloads = {
        "next_question": {"rule": "weakest_concept", "concept": "ohms_law", "mastery": 0.35},
        "revision_schedule": {"rule": "critical_review_1_day", "days_until_review": 1, "mastery": 0.35},
        "misconception_flag": {"misconception_id": "MC_PROPORTIONAL_I_R", "evidence": "I is directly proportional to R"},
        "diagnostic_start": {"diagnostic_id": "diag_01", "total_questions": 8},
        "mastery_update": {"concept_id": "ohms_law", "old_mastery": 0.35, "new_mastery": 0.48},
    }

    # Write each type
    for d_type, payload in payloads.items():
        log_entry = log_decision(test_db, student_id, d_type, payload)
        assert log_entry is not None

    test_db.commit()

    # Query all decisions for student
    all_logs = get_student_decisions(test_db, student_id)
    assert len(all_logs) == len(payloads)

    # Query filtered by type
    nq_logs = get_student_decisions(test_db, student_id, decision_type="next_question")
    assert len(nq_logs) == 1
    assert nq_logs[0].payload_json["rule"] == "weakest_concept"
    assert nq_logs[0].payload_json["concept"] == "ohms_law"

    misc_logs = get_student_decisions(test_db, student_id, decision_type="misconception_flag")
    assert len(misc_logs) == 1
    assert misc_logs[0].payload_json["misconception_id"] == "MC_PROPORTIONAL_I_R"


def test_invalid_decision_type_raises(test_db):
    """Writing an unregistered decision type must fail closed with ValueError."""
    with pytest.raises(ValueError, match="Invalid decision_type"):
        log_decision(test_db, "student_decision_test", "unregistered_magic_type", {})


def test_empty_student_id_raises(test_db):
    """Empty or non-string student ID must raise ValueError."""
    with pytest.raises(ValueError, match="student_id must be a non-empty string"):
        log_decision(test_db, "", "next_question", {"rule": "test"})


def test_non_dict_payload_raises(test_db):
    """Non-dict payload must raise ValueError."""
    with pytest.raises(ValueError, match="payload must be a valid dictionary"):
        log_decision(test_db, "student_decision_test", "next_question", "raw_string")  # type: ignore
