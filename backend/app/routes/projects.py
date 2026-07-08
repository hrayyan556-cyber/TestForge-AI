from __future__ import annotations

from collections import Counter
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Project, Requirement, TestCase, UploadedDocument, User
from app.schemas import ProjectCreate, ProjectRead
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


ALL_TEST_TYPES = ["Functional", "Negative", "Boundary", "Validation", "UI", "API", "Security", "Performance"]
ALL_PRIORITIES = ["Low", "Medium", "High", "Critical"]
ALL_SEVERITIES = ["Minor", "Major", "Critical", "Blocker"]
ALL_STATUSES = ["Draft", "Needs Review", "Approved", "Deprecated"]


def _owned_project(project_id: int, session: Session, current_user: User) -> Project:
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _count_map(values: list[str], labels: list[str]) -> dict[str, int]:
    counts = Counter(values)
    ordered = {label: int(counts.get(label, 0)) for label in labels}
    for key, value in counts.items():
        if key not in ordered:
            ordered[str(key)] = int(value)
    return ordered


@router.post("", response_model=ProjectRead)
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=List[ProjectRead])
def list_projects(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    ).all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return _owned_project(project_id, session, current_user)


@router.get("/{project_id}/analytics")
def get_project_analytics(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, session, current_user)
    requirements = session.exec(
        select(Requirement).where(Requirement.project_id == project.id)
    ).all()
    requirement_ids = [req.id for req in requirements if req.id is not None]

    if requirement_ids:
        cases = session.exec(
            select(TestCase).where(TestCase.requirement_id.in_(requirement_ids))
        ).all()
    else:
        cases = []

    total_cases = len(cases)
    approved = sum(1 for case in cases if case.status == "Approved")
    high_risk = sum(
        1 for case in cases
        if case.priority == "Critical" or case.severity in {"Critical", "Blocker"}
    )
    type_counts = _count_map([case.test_type for case in cases], ALL_TEST_TYPES)
    priority_counts = _count_map([case.priority for case in cases], ALL_PRIORITIES)
    severity_counts = _count_map([case.severity for case in cases], ALL_SEVERITIES)
    status_counts = _count_map([case.status for case in cases], ALL_STATUSES)

    covered_types = sum(1 for value in type_counts.values() if value > 0)
    coverage_score = 0
    if total_cases:
        coverage_score = round(
            min(100, (covered_types / len(ALL_TEST_TYPES)) * 45 + (approved / total_cases) * 35 + min(len(requirements), 5) / 5 * 20)
        )

    recommendations: list[str] = []
    if total_cases == 0:
        recommendations.append("Generate test cases to unlock dashboard analytics.")
    if type_counts.get("Security", 0) == 0 and total_cases:
        recommendations.append("Add at least a few security cases for stronger client confidence.")
    if type_counts.get("Negative", 0) == 0 and total_cases:
        recommendations.append("Add negative scenarios to cover invalid user behavior.")
    if status_counts.get("Draft", 0) > status_counts.get("Approved", 0) and total_cases:
        recommendations.append("Review and approve more cases before exporting a final QA pack.")
    if not recommendations and total_cases:
        recommendations.append("Coverage looks balanced. Export the QA pack or generate automation next.")

    return {
        "project": {"id": project.id, "name": project.name, "description": project.description},
        "summary": {
            "requirements": len(requirements),
            "test_cases": total_cases,
            "approved_cases": approved,
            "high_risk_cases": high_risk,
            "coverage_score": coverage_score,
        },
        "charts": {
            "by_type": type_counts,
            "by_priority": priority_counts,
            "by_severity": severity_counts,
            "by_status": status_counts,
        },
        "recommendations": recommendations,
    }


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project(project_id, session, current_user)

    requirements = session.exec(
        select(Requirement).where(Requirement.project_id == project.id)
    ).all()
    requirement_ids = [req.id for req in requirements if req.id is not None]

    if requirement_ids:
        cases = session.exec(
            select(TestCase).where(TestCase.requirement_id.in_(requirement_ids))
        ).all()
        for case in cases:
            session.delete(case)

    documents = session.exec(
        select(UploadedDocument).where(
            UploadedDocument.user_id == current_user.id,
            UploadedDocument.project_id == project.id,
        )
    ).all()
    for document in documents:
        session.delete(document)

    for requirement in requirements:
        session.delete(requirement)

    session.delete(project)
    session.commit()
    return {"success": True, "deleted_project_id": project_id}
