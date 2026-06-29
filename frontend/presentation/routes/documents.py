from pathlib import Path

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from frontend.application.documents import DocumentsPageService, DocumentsServiceError

router = APIRouter(tags=["documents"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)
service = DocumentsPageService()


@router.get("/", response_class=HTMLResponse)
@router.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request) -> HTMLResponse:
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    try:
        documents = service.list_documents()
        backend_ok = True
    except DocumentsServiceError as exc:
        documents = []
        backend_ok = False
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "documents.html",
        {
            "active": "documents",
            "documents": documents,
            "error": error,
            "success": success,
            "backend_ok": backend_ok,
        },
    )


@router.post("/documents")
def create_document(
    title: str = Form(...),
    text: str = Form(...),
) -> RedirectResponse:
    try:
        service.create_document(title, text)
    except DocumentsServiceError as exc:
        return RedirectResponse(
            url=f"/documents?error={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(url="/documents?success=Документ добавлен", status_code=303)


@router.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(request: Request, document_id: str) -> HTMLResponse:
    try:
        document = service.get_document(document_id)
    except DocumentsServiceError as exc:
        return templates.TemplateResponse(
            request,
            "document_detail.html",
            {
                "active": "documents",
                "error": str(exc),
                "document": None,
            },
            status_code=404 if exc.status_code == 404 else 200,
        )
    return templates.TemplateResponse(
        request,
        "document_detail.html",
        {
            "active": "documents",
            "document": document,
            "error": None,
        },
    )
