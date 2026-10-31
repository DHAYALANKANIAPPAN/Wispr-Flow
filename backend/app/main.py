"""FastAPI application main entrypoint and routing.

Purpose:
    Exposes REST endpoints for authentication, diagnostic assessments,
    adaptive quizzes, answer evaluation, learner mastery, and analytics.

Status:
    Active, Phase 1 implementation.

Fail-Closed Behavior:
    Fails closed on missing or unverified credentials, invalid schema payloads,
    and missing concept/question entities.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.db import get_db, Base, engine
from backend.app.models import User
from backend.app.schemas import (
    UserRegister,
    UserLogin,
    UserOut,
    TokenResponse,
)
from backend.app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_student_access,
    require_teacher_access,
)

# Ensure tables exist (auto-migration for dev SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Adaptive IQ API",
    description="Adaptive Exam-Prep Tutor with a Learner Model",
    version="1.0.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "Adaptive IQ"}


@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new student or teacher user.

    Args:
        payload: UserRegister schema with email, password, name, and role.
        db: Database session.

    Returns:
        TokenResponse: Access token and created user info.

    Raises:
        HTTPException: 400 if email is already registered.
    """
    existing_user = db.query(User).filter_by(email=payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a student or teacher user with email and password.

    Args:
        payload: UserLogin credentials.
        db: Database session.

    Returns:
        TokenResponse: Access token and authenticated user info.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = db.query(User).filter_by(email=payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user profile."""
    return UserOut.model_validate(current_user)


@app.get("/students/{student_id}/mastery-test", tags=["auth"])
def get_student_mastery_auth_test(
    student_id: str,
    current_user: User = Depends(get_current_user),
):
    """Auth validation endpoint to verify cross-student access is blocked.

    Args:
        student_id: Target student ID.
        current_user: Authenticated caller.

    Returns:
        dict: Confirmation if authorized.
    """
    require_student_access(student_id=student_id, current_user=current_user)
    return {"status": "authorized", "student_id": student_id}


@app.get("/teachers/{teacher_id}/class-summary-test", tags=["auth"])
def get_teacher_class_auth_test(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
):
    """Auth validation endpoint to verify cross-teacher access is blocked.

    Args:
        teacher_id: Target teacher ID.
        current_user: Authenticated caller.

    Returns:
        dict: Confirmation if authorized.
    """
    require_teacher_access(teacher_id=teacher_id, current_user=current_user)
    return {"status": "authorized", "teacher_id": teacher_id}
