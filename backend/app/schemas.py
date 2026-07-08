from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""


class ProjectRead(ProjectCreate):
    id: int
    created_at: datetime


class RequirementCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=2, max_length=160)
    module_name: str = "General"
    description: str = Field(min_length=10)
    source_filename: str = ""


class RequirementRead(RequirementCreate):
    id: int
    created_at: datetime


class TestCaseRead(BaseModel):
    id: int
    requirement_id: int
    title: str
    test_type: str
    priority: str
    severity: str
    preconditions: List[str]
    steps: List[str]
    test_data: str
    expected_result: str
    status: str
    created_at: datetime
    updated_at: datetime


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    test_type: Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    preconditions: Optional[List[str]] = None
    steps: Optional[List[str]] = None
    test_data: Optional[str] = None
    expected_result: Optional[str] = None
    status: Optional[str] = None


class GenerateRequest(BaseModel):
    project_id: Optional[int] = None
    project_name: Optional[str] = "Demo Project"
    module_name: str = "General"
    requirement_title: str = "Generated Requirement"
    requirement_text: str = Field(min_length=10)
    source_filename: str = ""
    test_types: List[str] = Field(default_factory=lambda: ["Functional", "Negative", "Boundary"])
    number_of_cases: int = Field(default=8, ge=1, le=30)


class UploadExtractResponse(BaseModel):
    filename: str
    character_count: int
    suggested_title: str
    extracted_text: str


class PlaywrightScriptResponse(BaseModel):
    filename: str
    script: str
