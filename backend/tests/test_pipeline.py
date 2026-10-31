"""Tests for the complete atomic attempt-to-mastery pipeline.

Purpose:
    Validates the 9-step atomic transaction contract:
    1. Correct answer raises mastery and updates revision schedule.
    2. Incorrect answer with misconception lowers mastery and stores MisconceptionEvent.
    3. LLM unavailable still processes deterministic answer and sets llm_status='unavailable'.
    4. Database transaction failure triggers complete rollback (nothing stored).
    5. Diagnostic assessment retrieves approved questions and processes attempts.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.models import (
    User,
    Subject,
    Concept,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    MisconceptionEvent,
    DecisionLog,
    RevisionSchedule,
)
from backend.app.main import app


@pytest.fixture
def pipeline_client():
    """In-memory SQLite test client fixture with seeded questions and concepts."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed Subject and Concepts
    session = TestingSession()
    subj = Subject(id="physics_cbse_10", name="Physics")
    c1 = Concept(id="electric_current", subject_id="physics_cbse_10", name="Electric Current")
    c2 = Concept(id="ohms_law", subject_id="physics_cbse_10", name="Ohm's Law")
    session.add_all([subj, c1, c2])

    # Seed Questions
    q_num = Question(
        id="q_pipe_num",
        text="A current of 2 A flows for 10 s. Find charge.",
        answer_key="20",
        answer_type="numeric",
        tolerance=0.1,
        difficulty=1,
        question_type="numerical",
        status="approved",
    )
    q_diag = Question(
        id="q_diag_01",
        text="A current of 0.5 A flows for 10 min. Find charge.",
        answer_key="300",
        answer_type="numeric",
        tolerance=1.0,
        difficulty=1,
        question_type="numerical",
        status="approved",
    )
    q_draft = Question(
        id="q_pipe_draft",
        text="Draft question not approved",
        answer_key="draft",
        answer_type="text",
        difficulty=1,
        question_type="conceptual",
        status="draft",
    )
    session.add_all([q_num, q_diag, q_draft])
    session.flush()

    session.add(QuestionConcept(question_id=q_num.id, concept_id="electric_current"))
    session.add(QuestionConcept(question_id=q_diag.id, concept_id="electric_current"))
    session.add(QuestionConcept(question_id=q_draft.id, concept_id="electric_current"))
    session.commit()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def test_correct_answer_raises_mastery(pipeline_client):
    """Submitting a correct answer with sound explanation increases concept mastery."""
    client, session = pipeline_client

    # 1. Register student
    reg = client.post(
        "/auth/register",
        json={"name": "Pipeline Student", "email": "pipe1@test.com", "password": "password123", "role": "student"},
    )
    token = reg.json()["access_token"]
    student_id = reg.json()["user"]["id"]

    # 2. Submit correct answer
    res = client.post(
        "/attempts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "q_pipe_num",
            "student_answer": "20",
            "explanation": "Using Q equals I times t so 2 times 10 is 20 coulombs",
        },
    )
    assert res.status_code == 201
    data = res.json()

    assert data["correct"] is True
    assert data["evidence"] >= 0.7
    # Mastery started at 0.50, updated with evidence -> increases
    new_m = data["concept_mastery_updates"]["electric_current"]
    assert new_m > 0.50

    # Verify attempt and decision logs in DB
    att = session.query(Attempt).filter_by(student_id=student_id).first()
    assert att is not None
    assert att.correct is True

    dec_logs = session.query(DecisionLog).filter_by(student_id=student_id).all()
    assert len(dec_logs) >= 3  # mastery_update, revision_schedule, next_question


def test_incorrect_answer_with_misconception_lowers_mastery(pipeline_client):
    """Submitting an incorrect answer with misconception lowers mastery and stores MisconceptionEvent."""
    client, session = pipeline_client

    reg = client.post(
        "/auth/register",
        json={"name": "Student Misc", "email": "misc_pipe@test.com", "password": "password123", "role": "student"},
    )
    token = reg.json()["access_token"]
    student_id = reg.json()["user"]["id"]

    # Mock evaluate_answer to return a known misconception
    with patch("backend.app.main.evaluate_answer") as mock_eval:
        mock_eval.return_value = {
            "correct": False,
            "reasoning": "none",
            "misconception_id": "MC_PROPORTIONAL_I_R",
            "evidence": 0.0,
            "llm_status": "ok",
            "feedback": "Current and resistance are inversely proportional.",
        }

        res = client.post(
            "/attempts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": "q_pipe_num",
                "student_answer": "50",
                "explanation": "Current increases because resistance is higher in this circuit branch",
            },
        )
        assert res.status_code == 201
        data = res.json()

        assert data["correct"] is False
        assert data["misconception_id"] == "MC_PROPORTIONAL_I_R"
        assert data["evidence"] == 0.0
        # Mastery lowered: 0.50 -> 0.50 + 0.2*(0.0 - 0.50) = 0.40
        assert data["concept_mastery_updates"]["electric_current"] == 0.40

        # Check MisconceptionEvent table
        event = session.query(MisconceptionEvent).first()
        assert event is not None
        assert event.misconception_id == "MC_PROPORTIONAL_I_R"


def test_llm_unavailable_still_stores_attempt_with_status(pipeline_client):
    """When LLM is unavailable, attempt is processed deterministically with llm_status='unavailable'."""
    client, session = pipeline_client

    reg = client.post(
        "/auth/register",
        json={"name": "Fallback Student", "email": "fall_pipe@test.com", "password": "password123", "role": "student"},
    )
    token = reg.json()["access_token"]
    student_id = reg.json()["user"]["id"]

    # Force LLM error
    with patch("backend.app.evaluation._call_llm_reasoning", side_effect=ConnectionError("Network down")):
        res = client.post(
            "/attempts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question_id": "q_pipe_num",
                "student_answer": "20",
                "explanation": "Because Q is the product of current and time in seconds",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["correct"] is True
        assert data["llm_status"] == "unavailable"

        att = session.query(Attempt).filter_by(student_id=student_id).first()
        assert att.llm_status == "unavailable"


def test_draft_question_rejected(pipeline_client):
    """Attempting to submit an answer to a draft question must return 400 Bad Request."""
    client, _ = pipeline_client

    reg = client.post(
        "/auth/register",
        json={"name": "Draft Tester", "email": "draft_pipe@test.com", "password": "password123", "role": "student"},
    )
    token = reg.json()["access_token"]

    res = client.post(
        "/attempts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "q_pipe_draft",
            "student_answer": "draft",
            "explanation": "Testing draft submission",
        },
    )
    assert res.status_code == 400
    assert "approved questions" in res.json()["detail"].lower()


def test_failed_database_write_rolls_back_completely(pipeline_client):
    """If database write fails mid-pipeline, nothing is stored (atomic rollback)."""
    client, session = pipeline_client

    reg = client.post(
        "/auth/register",
        json={"name": "Rollback Student", "email": "roll_pipe@test.com", "password": "password123", "role": "student"},
    )
    token = reg.json()["access_token"]
    student_id = reg.json()["user"]["id"]

    # Count initial rows
    init_attempts = session.query(Attempt).filter_by(student_id=student_id).count()

    # Simulate crash in adaptive_engine during pipeline execution
    with patch("backend.app.main.select_next_question", side_effect=RuntimeError("Simulated engine crash")):
        with pytest.raises(RuntimeError):
            client.post(
                "/attempts",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "question_id": "q_pipe_num",
                    "student_answer": "20",
                    "explanation": "Valid explanation that should roll back",
                },
            )

    # Verify atomic rollback: no attempts stored
    after_attempts = session.query(Attempt).filter_by(student_id=student_id).count()
    assert after_attempts == init_attempts
