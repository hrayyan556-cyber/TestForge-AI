from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Project, Requirement, TestCase, User
from app.schemas import RequirementCreate, RequirementRead
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


def _get_owned_project(project_id: int, session: Session, current_user: User) -> Project:
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_owned_requirement(requirement_id: int, session: Session, current_user: User) -> Requirement:
    requirement = session.get(Requirement, requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    _get_owned_project(requirement.project_id, session, current_user)
    return requirement


@router.post("", response_model=RequirementRead)
def create_requirement(
    payload: RequirementCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(payload.project_id, session, current_user)
    requirement = Requirement(
        project_id=payload.project_id,
        title=payload.title.strip(),
        module_name=payload.module_name.strip() or "General",
        description=payload.description.strip(),
        source_filename=payload.source_filename.strip(),
    )
    session.add(requirement)
    session.commit()
    session.refresh(requirement)
    return requirement


@router.get("", response_model=List[RequirementRead])
def list_requirements(
    project_id: int = Query(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(project_id, session, current_user)
    return session.exec(
        select(Requirement)
        .where(Requirement.project_id == project_id)
        .order_by(Requirement.created_at.desc())
    ).all()


@router.delete("/{requirement_id}")
def delete_requirement(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    requirement = _get_owned_requirement(requirement_id, session, current_user)
    cases = session.exec(select(TestCase).where(TestCase.requirement_id == requirement.id)).all()
    for case in cases:
        session.delete(case)
    session.delete(requirement)
    session.commit()
    return {"success": True, "deleted_requirement_id": requirement_id}
