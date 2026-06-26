from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.application.qa import QAService
from backend.persistence.database import get_db
from backend.schemas.ai import AIAnswerRequest, AIAnswerResponse

router = APIRouter(prefix="/ai", tags=["ai"])
qa_service = QAService()


@router.post("/answer_with_sources", response_model=AIAnswerResponse)
def answer_with_sources(
    payload: AIAnswerRequest,
    db: Session = Depends(get_db),
) -> AIAnswerResponse:
    return qa_service.answer_with_sources(db, payload)
