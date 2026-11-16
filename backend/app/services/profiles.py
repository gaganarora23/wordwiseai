import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.child import Child
from app.schemas.profile import ProfileCreate


def create_profile(session: Session, data: ProfileCreate) -> Child:
    child = Child(nickname=data.nickname, grade=data.grade, daily_goal=data.daily_goal)
    session.add(child)
    session.commit()
    session.refresh(child)
    return child


def list_profiles(session: Session) -> list[Child]:
    return list(session.scalars(select(Child).order_by(Child.created_at, Child.id)))


def get_profile(session: Session, profile_id: uuid.UUID) -> Child | None:
    return session.get(Child, profile_id)


def update_profile(session: Session, profile_id: uuid.UUID, data: ProfileCreate) -> Child | None:
    child = session.get(Child, profile_id)
    if child is None:
        return None
    child.nickname = data.nickname
    child.grade = data.grade
    child.daily_goal = data.daily_goal
    child.updated_at = func.now()
    session.commit()
    session.refresh(child)
    return child


def delete_profile(session: Session, profile_id: uuid.UUID) -> bool:
    """Delete one profile; the database cascades remove its sessions, answers, results and mastery."""
    child = session.get(Child, profile_id)
    if child is None:
        return False
    session.delete(child)
    session.commit()
    return True
