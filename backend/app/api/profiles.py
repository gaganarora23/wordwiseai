import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.profile import Profile, ProfileCreate
from app.services import profiles as profiles_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]

PROFILE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


@router.post("/profiles", response_model=Profile, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileCreate, session: DbSession):
    return profiles_service.create_profile(session, body)


@router.get("/profiles", response_model=list[Profile])
def list_profiles(session: DbSession):
    return profiles_service.list_profiles(session)


@router.get("/profiles/{profile_id}", response_model=Profile)
def get_profile(profile_id: uuid.UUID, session: DbSession):
    child = profiles_service.get_profile(session, profile_id)
    if child is None:
        raise PROFILE_NOT_FOUND
    return child


@router.put("/profiles/{profile_id}", response_model=Profile)
def update_profile(profile_id: uuid.UUID, body: ProfileCreate, session: DbSession):
    child = profiles_service.update_profile(session, profile_id, body)
    if child is None:
        raise PROFILE_NOT_FOUND
    return child


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: uuid.UUID, session: DbSession) -> Response:
    if not profiles_service.delete_profile(session, profile_id):
        raise PROFILE_NOT_FOUND
    return Response(status_code=status.HTTP_204_NO_CONTENT)
