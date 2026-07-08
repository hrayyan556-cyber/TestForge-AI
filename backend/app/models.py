from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    email: str = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    password_hash: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class AuthToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(sa_column=Column(String(128), unique=True, index=True, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(index=True, max_length=120)
    description: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now)


class Requirement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    title: str = Field(max_length=160)
    module_name: str = Field(default="General", max_length=120)
    description: str = Field(sa_column=Column(Text))
    source_filename: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class TestCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requirement_id: int = Field(foreign_key="requirement.id", index=True)
    title: str = Field(max_length=220)
    test_type: str = Field(default="Functional", max_length=60)
    priority: str = Field(default="Medium", max_length=30)
    severity: str = Field(default="Minor", max_length=30)
    preconditions: str = Field(default="[]", sa_column=Column(Text))
    steps: str = Field(default="[]", sa_column=Column(Text))
    test_data: str = Field(default="", sa_column=Column(Text))
    expected_result: str = Field(sa_column=Column(Text))
    status: str = Field(default="Draft", max_length=30)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UploadedDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", index=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(default="", max_length=120)
    extracted_text: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now)
