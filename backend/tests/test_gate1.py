"""Gate 1 Verification Test.

Specification Contract:
    "GATE 1: a student logs in and sees the chapter's concepts.
     Only then does frontend work start."

Verification Steps:
    1. Student registers and logs in to obtain bearer token.
    2. Student queries GET /concepts with Authorization header.
    3. Verifies all 7 CBSE Electricity concepts are returned.
    4. Verifies root concepts (electric_current, potential_difference, resistance) are unlocked.
    5. Verifies dependent concepts (ohms_law, series_circuits, parallel_circuits, electrical_power) are locked.
    6. Verifies unauthenticated access is rejected (401).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.main import app


@pytest.fixture
def test_client():
    """In-memory test client."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_gate1_student_login_and_view_concepts(test_client):
    """Verify GATE 1 end-to-end: student logs in and receives concept list with unlock statuses."""
    # 1. Unauthenticated request must fail closed
    unauth_res = test_client.get("/concepts")
    assert unauth_res.status_code == 401

    # 2. Register & login student
    reg_res = test_client.post(
        "/auth/register",
        json={
            "name": "Gate 1 Student",
            "email": "gate1_student@test.com",
            "password": "gate1password123",
            "role": "student",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]

    # 3. Query GET /concepts
    res = test_client.get(
        "/concepts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    concepts = res.json()

    # Must contain exactly the 7 chapter concepts
    assert len(concepts) == 7
    concept_map = {c["id"]: c for c in concepts}

    expected_concepts = [
        "electric_current",
        "potential_difference",
        "resistance",
        "ohms_law",
        "series_circuits",
        "parallel_circuits",
        "electrical_power",
    ]
    for cid in expected_concepts:
        assert cid in concept_map, f"Missing expected concept: {cid}"

    # Verify initial unlock states for a new student
    # Root concepts (no prerequisites) are unlocked
    assert concept_map["electric_current"]["is_unlocked"] is True
    assert concept_map["potential_difference"]["is_unlocked"] is True
    assert concept_map["resistance"]["is_unlocked"] is True

    # Dependent concepts are locked initially
    assert concept_map["ohms_law"]["is_unlocked"] is False
    assert concept_map["series_circuits"]["is_unlocked"] is False
    assert concept_map["parallel_circuits"]["is_unlocked"] is False
    assert concept_map["electrical_power"]["is_unlocked"] is False
