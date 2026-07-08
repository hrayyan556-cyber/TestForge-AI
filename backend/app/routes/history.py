from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Project, Requirement, TestCase, UploadedDocument, User
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


def _owned_project(project_id: int, session: Session, current_user: User) -> Project:
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _delete_requirement_tree(requirements: list[Requirement], session: Session) -> int:
    deleted_cases = 0
    requirement_ids = [req.id for req in requirements if req.id is not None]
    if requirement_ids:
        cases = session.exec(select(TestCase).where(TestCase.requirement_id.in_(requirement_ids))).all()
        deleted_cases = len(cases)
        for case in cases:
            session.delete(case)
    for requirement in requirements:
        session.delete(requirement)
    return deleted_cases


@router.get("/summary")
def history_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    projects = session.exec(select(Project).where(Project.user_id == current_user.id)).all()
    project_ids = [project.id for project in projects if project.id is not None]
    if project_ids:
        requirements = session.exec(select(Requirement).where(Requirement.project_id.in_(project_ids))).all()
        requirement_ids = [req.id for req in requirements if req.id is not None]
        cases = session.exec(select(TestCase).where(TestCase.requirement_id.in_(requirement_ids))).all() if requirement_ids else []
    else:
        requirements = []
        cases = []
    documents = session.exec(select(UploadedDocument).where(UploadedDocument.user_id == current_user.id)).all()
    return {
        "projects": len(projects),
        "requirements": len(requirements),
        "test_cases": len(cases),
        "uploaded_documents": len(documents),
    }


@router.delete("/project/{project_id}")
def clear_project_history(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, session, current_user)
    requirements = session.exec(select(Requirement).where(Requirement.project_id == project.id)).all()
    documents = session.exec(
        select(UploadedDocument).where(
            UploadedDocument.user_id == current_user.id,
            UploadedDocument.project_id == project.id,
        )
    ).all()
    deleted_cases = _delete_requirement_tree(requirements, session)
    deleted_docs = len(documents)
    for document in documents:
        session.delete(document)
    session.commit()
    return {
        "success": True,
        "scope": "project",
        "project_id": project_id,
        "deleted_requirements": len(requirements),
        "deleted_test_cases": deleted_cases,
        "deleted_uploaded_documents": deleted_docs,
    }


@router.delete("/all")
def clear_all_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    projects = session.exec(select(Project).where(Project.user_id == current_user.id)).all()
    project_ids = [project.id for project in projects if project.id is not None]
    requirements = session.exec(select(Requirement).where(Requirement.project_id.in_(project_ids))).all() if project_ids else []
    documents = session.exec(select(UploadedDocument).where(UploadedDocument.user_id == current_user.id)).all()
    deleted_cases = _delete_requirement_tree(requirements, session)
    deleted_docs = len(documents)
    for document in documents:
        session.delete(document)
    session.commit()
    return {
        "success": True,
        "scope": "all",
        "deleted_requirements": len(requirements),
        "deleted_test_cases": deleted_cases,
        "deleted_uploaded_documents": deleted_docs,
        "projects_kept": len(projects),
    }
