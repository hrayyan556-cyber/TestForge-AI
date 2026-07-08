from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models import User
from app.services.ai_service import get_llm_status
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status")
def llm_status(current_user: User = Depends(get_current_user)):
    return get_llm_status()
