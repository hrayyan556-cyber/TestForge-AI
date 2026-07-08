from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlmodel import Session, select

from app.database import get_session
from app.models import Project, Requirement, TestCase, User
from app.schemas import GenerateRequest, PlaywrightScriptResponse, ProjectRead, RequirementRead, TestCaseRead, TestCaseUpdate
from app.services.ai_service import generate_test_cases_with_ai
from app.utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["test-cases"])


def _safe_json_list(value: str) -> List[str]:
    try:
        data = json.loads(value or "[]")
        return [str(item) for item in data] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _to_read_model(case: TestCase) -> TestCaseRead:
    return TestCaseRead(
        id=case.id,
        requirement_id=case.requirement_id,
        title=case.title,
        test_type=case.test_type,
        priority=case.priority,
        severity=case.severity,
        preconditions=_safe_json_list(case.preconditions),
        steps=_safe_json_list(case.steps),
        test_data=case.test_data,
        expected_result=case.expected_result,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


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


def _cases_for_requirement(requirement_id: int, session: Session) -> List[TestCase]:
    return session.exec(
        select(TestCase)
        .where(TestCase.requirement_id == requirement_id)
        .order_by(TestCase.id)
    ).all()


def _download_response(data: bytes | str, filename: str, media_type: str) -> StreamingResponse:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate-test-cases")
def generate_test_cases(
    payload: GenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if payload.project_id:
        project = _get_owned_project(payload.project_id, session, current_user)
    else:
        project = Project(
            user_id=current_user.id,
            name=(payload.project_name or "Demo Project").strip(),
            description="Created from generator",
        )
        session.add(project)
        session.commit()
        session.refresh(project)

    requirement = Requirement(
        project_id=project.id,
        title=payload.requirement_title.strip(),
        module_name=payload.module_name.strip() or "General",
        description=payload.requirement_text.strip(),
        source_filename=payload.source_filename.strip(),
    )
    session.add(requirement)
    session.commit()
    session.refresh(requirement)

    ai_result = generate_test_cases_with_ai(
        requirement_text=payload.requirement_text,
        module_name=payload.module_name,
        requirement_title=payload.requirement_title,
        test_types=payload.test_types,
        number_of_cases=payload.number_of_cases,
    )

    saved_cases: List[TestCase] = []
    for item in ai_result.get("test_cases", []):
        test_case = TestCase(
            requirement_id=requirement.id,
            title=item.get("title", "Untitled test case")[:220],
            test_type=item.get("test_type", "Functional"),
            priority=item.get("priority", "Medium"),
            severity=item.get("severity", "Minor"),
            preconditions=json.dumps(item.get("preconditions", [])),
            steps=json.dumps(item.get("steps", [])),
            test_data=item.get("test_data", ""),
            expected_result=item.get("expected_result", "Expected result not provided"),
        )
        session.add(test_case)
        saved_cases.append(test_case)

    session.commit()
    for test_case in saved_cases:
        session.refresh(test_case)

    return {
        "project": ProjectRead(id=project.id, name=project.name, description=project.description, created_at=project.created_at),
        "requirement": RequirementRead(id=requirement.id, project_id=requirement.project_id, title=requirement.title, module_name=requirement.module_name, description=requirement.description, source_filename=requirement.source_filename, created_at=requirement.created_at),
        "ai_assumptions": ai_result.get("assumptions", []),
        "test_cases": [_to_read_model(case) for case in saved_cases],
    }


@router.get("/test-cases/{requirement_id}", response_model=List[TestCaseRead])
def list_test_cases(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _get_owned_requirement(requirement_id, session, current_user)
    return [_to_read_model(case) for case in _cases_for_requirement(requirement_id, session)]


@router.patch("/test-cases/{case_id}", response_model=TestCaseRead)
def update_test_case(
    case_id: int,
    payload: TestCaseUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    case = session.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    _get_owned_requirement(case.requirement_id, session, current_user)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key in {"preconditions", "steps"}:
            setattr(case, key, json.dumps(value or []))
        elif value is not None:
            setattr(case, key, value)

    case.updated_at = datetime.now(timezone.utc)
    session.add(case)
    session.commit()
    session.refresh(case)
    return _to_read_model(case)


@router.delete("/test-cases/{case_id}")
def delete_test_case(
    case_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    case = session.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    _get_owned_requirement(case.requirement_id, session, current_user)
    session.delete(case)
    session.commit()
    return {"success": True}


@router.post("/test-cases/{case_id}/duplicate", response_model=TestCaseRead)
def duplicate_test_case(
    case_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    case = session.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    _get_owned_requirement(case.requirement_id, session, current_user)

    duplicated = TestCase(
        requirement_id=case.requirement_id,
        title=f"Copy of {case.title}"[:220],
        test_type=case.test_type,
        priority=case.priority,
        severity=case.severity,
        preconditions=case.preconditions,
        steps=case.steps,
        test_data=case.test_data,
        expected_result=case.expected_result,
        status="Draft",
    )
    session.add(duplicated)
    session.commit()
    session.refresh(duplicated)
    return _to_read_model(duplicated)


@router.get("/export/csv/{requirement_id}")
def export_csv(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Test Case ID",
        "Title",
        "Type",
        "Priority",
        "Severity",
        "Preconditions",
        "Steps",
        "Test Data",
        "Expected Result",
        "Status",
    ])
    for case in cases:
        writer.writerow([
            case.id,
            case.title,
            case.test_type,
            case.priority,
            case.severity,
            " | ".join(_safe_json_list(case.preconditions)),
            " | ".join(_safe_json_list(case.steps)),
            case.test_data,
            case.expected_result,
            case.status,
        ])

    return _download_response(output.getvalue(), f"test_cases_requirement_{requirement_id}.csv", "text/csv")


@router.get("/export/jira-csv/{requirement_id}")
def export_jira_csv(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    requirement = _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Issue Type",
        "Summary",
        "Description",
        "Priority",
        "Labels",
        "Test Type",
        "Test Steps",
        "Expected Result",
    ])
    for case in cases:
        description = (
            f"Requirement: {requirement.title}\n"
            f"Module: {requirement.module_name}\n\n"
            f"Preconditions:\n- " + "\n- ".join(_safe_json_list(case.preconditions)) + "\n\n"
            f"Test Data:\n{case.test_data}\n\n"
            f"Severity: {case.severity}\nStatus: {case.status}"
        )
        writer.writerow([
            "Task",
            case.title,
            description,
            case.priority,
            f"qa,test-case,{requirement.module_name.lower().replace(' ', '-')}",
            case.test_type,
            "\n".join(f"{i}. {step}" for i, step in enumerate(_safe_json_list(case.steps), start=1)),
            case.expected_result,
        ])

    return _download_response(output.getvalue(), f"jira_test_cases_requirement_{requirement_id}.csv", "text/csv")


@router.get("/export/excel/{requirement_id}")
def export_excel(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test Cases"
    headers = [
        "Test Case ID",
        "Title",
        "Type",
        "Priority",
        "Severity",
        "Preconditions",
        "Steps",
        "Test Data",
        "Expected Result",
        "Status",
    ]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)

    for case in cases:
        sheet.append([
            case.id,
            case.title,
            case.test_type,
            case.priority,
            case.severity,
            "\n".join(_safe_json_list(case.preconditions)),
            "\n".join(f"{i}. {step}" for i, step in enumerate(_safe_json_list(case.steps), start=1)),
            case.test_data,
            case.expected_result,
            case.status,
        ])

    widths = [14, 42, 16, 14, 14, 36, 52, 34, 52, 14]
    for idx, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + idx)].width = width
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")

    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return _download_response(
        stream.getvalue(),
        f"test_cases_requirement_{requirement_id}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/export/pdf/{requirement_id}")
def export_pdf(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    requirement = _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)

    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=landscape(A4), rightMargin=0.35 * inch, leftMargin=0.35 * inch, topMargin=0.35 * inch, bottomMargin=0.35 * inch)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("AI QA Test Cases", styles["Title"]),
        Paragraph(f"Requirement: {requirement.title}", styles["Heading2"]),
        Paragraph(f"Module: {requirement.module_name}", styles["Normal"]),
        Spacer(1, 0.15 * inch),
    ]

    data = [["ID", "Title", "Type", "Priority", "Steps", "Expected Result", "Status"]]
    for case in cases:
        steps = "<br/>".join(f"{i}. {step}" for i, step in enumerate(_safe_json_list(case.steps), start=1))
        data.append([
            str(case.id),
            Paragraph(case.title, styles["BodyText"]),
            case.test_type,
            case.priority,
            Paragraph(steps or "-", styles["BodyText"]),
            Paragraph(case.expected_result, styles["BodyText"]),
            case.status,
        ])

    table = Table(data, colWidths=[0.45 * inch, 2.2 * inch, 0.9 * inch, 0.8 * inch, 3.1 * inch, 3.3 * inch, 0.8 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
    ]))
    story.append(table)
    doc.build(story)
    stream.seek(0)
    return _download_response(stream.getvalue(), f"test_cases_requirement_{requirement_id}.pdf", "application/pdf")


def _safe_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return cleaned or "generated_test"


def _generate_playwright_script(requirement: Requirement, cases: List[TestCase]) -> str:
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        "const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';",
        "",
        f"test.describe('{requirement.module_name} - {requirement.title}', () => {{",
    ]
    for case in cases:
        test_name = case.title.replace("'", "\\'")
        lines.extend([
            f"  test('{test_name}', async ({{ page }}) => {{",
            "    await page.goto(BASE_URL);",
            "",
            "    // Preconditions:",
        ])
        for precondition in _safe_json_list(case.preconditions):
            lines.append(f"    // - {precondition}")
        lines.append("")
        for index, step in enumerate(_safe_json_list(case.steps), start=1):
            safe_step = step.replace("`", "\\`")
            lines.extend([
                f"    await test.step(`Step {index}: {safe_step}`, async () => {{",
                "      // TODO: Replace this comment with real selectors/actions from your app.",
                "      // Example: await page.getByRole('button', { name: 'Submit' }).click();",
                "    });",
                "",
            ])
        expected = case.expected_result.replace("`", "\\`")
        lines.extend([
            f"    // Expected result: {expected}",
            "    await expect(page).toHaveURL(/.*/);",
            "  });",
            "",
        ])
    lines.append("});")
    return "\n".join(lines)


@router.get("/playwright/{requirement_id}", response_model=PlaywrightScriptResponse)
def get_playwright_script(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    requirement = _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)
    filename = f"{_safe_identifier(requirement.module_name)}_{_safe_identifier(requirement.title)}.spec.ts"
    return PlaywrightScriptResponse(filename=filename, script=_generate_playwright_script(requirement, cases))


@router.get("/export/playwright/{requirement_id}")
def export_playwright_script(
    requirement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    requirement = _get_owned_requirement(requirement_id, session, current_user)
    cases = _cases_for_requirement(requirement_id, session)
    filename = f"{_safe_identifier(requirement.module_name)}_{_safe_identifier(requirement.title)}.spec.ts"
    return _download_response(_generate_playwright_script(requirement, cases), filename, "text/plain")
