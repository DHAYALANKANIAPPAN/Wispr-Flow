"""Tests for user authentication and role-based access control.

Purpose:
    Validates registration, login, password hashing, and role checks.
    Guarantees students cannot read other students' data, and teachers
    cannot read other teachers' class data.
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
    """In-memory SQLite test client fixture with isolated DB session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_register_and_login_success(test_client):
    """Test standard registration and login flow for a student."""
    # Register student
    reg_res = test_client.post(
        "/auth/register",
        json={
            "name": "Student One",
            "email": "student1@example.com",
            "password": "strongpassword123",
            "role": "student",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "student1@example.com"
    assert reg_data["user"]["role"] == "student"

    # Login
    login_res = test_client.post(
        "/auth/login",
        json={
            "email": "student1@example.com",
            "password": "strongpassword123",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["role"] == "student"


def test_wrong_password_fails(test_client):
    """Test that wrong password returns 401."""
    test_client.post(
        "/auth/register",
        json={
            "name": "User Two",
            "email": "user2@example.com",
            "password": "correctpassword",
            "role": "student",
        },
    )

    bad_res = test_client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "wrongpassword",
        },
    )
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["detail"]


def test_student_cannot_read_another_student_data(test_client):
    """Test that student A cannot access student B's data (403 Forbidden)."""
    # Create student A
    res_a = test_client.post(
        "/auth/register",
        json={
            "name": "Student A",
            "email": "student_a@example.com",
            "password": "passwordA123",
            "role": "student",
        },
    )
    token_a = res_a.json()["access_token"]
    student_a_id = res_a.json()["user"]["id"]

    # Create student B
    res_b = test_client.post(
        "/auth/register",
        json={
            "name": "Student B",
            "email": "student_b@example.com",
            "password": "passwordB123",
            "role": "student",
        },
    )
    student_b_id = res_b.json()["user"]["id"]

    # Student A accesses own data -> OK
    own_res = test_client.get(
        f"/students/{student_a_id}/mastery-test",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert own_res.status_code == 200

    # Student A accesses student B's data -> 403 Forbidden
    other_res = test_client.get(
        f"/students/{student_b_id}/mastery-test",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert other_res.status_code == 403
    assert "forbidden" in other_res.json()["detail"].lower()


def test_teacher_role_isolation(test_client):
    """Test teacher role requirements and cross-teacher isolation."""
    # Register teacher 1
    t1_res = test_client.post(
        "/auth/register",
        json={
            "name": "Teacher One",
            "email": "t1@example.com",
            "password": "teacherpass123",
            "role": "teacher",
        },
    )
    t1_token = t1_res.json()["access_token"]
    t1_id = t1_res.json()["user"]["id"]

    # Register teacher 2
    t2_res = test_client.post(
        "/auth/register",
        json={
            "name": "Teacher Two",
            "email": "t2@example.com",
            "password": "teacherpass123",
            "role": "teacher",
        },
    )
    t2_id = t2_res.json()["user"]["id"]

    # Register student
    s_res = test_client.post(
        "/auth/register",
        json={
            "name": "Student Isolated",
            "email": "student_iso@example.com",
            "password": "studentpass123",
            "role": "student",
        },
    )
    s_token = s_res.json()["access_token"]

    # Student attempts to access teacher endpoint -> 403
    s_teacher_res = test_client.get(
        f"/teachers/{t1_id}/class-summary-test",
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert s_teacher_res.status_code == 403

    # Teacher 1 accesses own class -> 200
    t1_own_res = test_client.get(
        f"/teachers/{t1_id}/class-summary-test",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert t1_own_res.status_code == 200

    # Teacher 1 attempts to access teacher 2's class -> 403
    t1_cross_res = test_client.get(
        f"/teachers/{t2_id}/class-summary-test",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert t1_cross_res.status_code == 403
