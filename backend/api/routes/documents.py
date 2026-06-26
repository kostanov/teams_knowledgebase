from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.application.documents import DocumentService
from backend.persistence.database import get_db
from backend.schemas.documents import (
    DocumentCreate,
    DocumentCreateResponse,
    DocumentDetail,
    DocumentListItem,
)

router = APIRouter(prefix="/kb", tags=["documents"])
document_service = DocumentService()


@router.post("/documents", response_model=DocumentCreateResponse)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
) -> DocumentCreateResponse:
    document_id = document_service.add_document(db, payload)
    return DocumentCreateResponse(document_id=document_id)


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    return document_service.list_documents(db)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document = document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(
        id=document.id,
        title=document.title,
        text=document.text,
        created_at=document.created_at,
    )
