"""Minimal user handling.

LectureLens ships without full auth; every upload is attributed to a single
implicit demo user. The table + service layer exist so real authentication can
be dropped in later without touching the rest of the schema.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User

DEFAULT_USER_EMAIL = "student@lecturelens.local"


def get_or_create_user(db: Session, email: str = DEFAULT_USER_EMAIL, display_name: str | None = None) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=display_name or "Demo Student")
        db.add(user)
        db.flush()
    return user
