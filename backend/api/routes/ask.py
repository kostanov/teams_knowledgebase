from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.application.qa import QAService
from backend.persistence.database import get_db
from backend.schemas.qa import AskRequest, AskResponse

router = APIRouter(prefix="/kb", tags=["questions"])
qa_service = QAService()


@router.post("/ask", response_model=AskResponse)
def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_db),
) -> AskResponse:
    return qa_service.ask(db, payload)
