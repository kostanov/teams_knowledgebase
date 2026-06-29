from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from frontend.application.questions import QuestionsPageService, QuestionsServiceError

router = APIRouter(tags=["questions"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)
service = QuestionsPageService()


@router.get("/questions", response_class=HTMLResponse)
def questions_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "questions.html",
        {
            "active": "questions",
            "question": request.query_params.get("question", ""),
            "result": None,
            "error": None,
            "source_titles": {},
        },
    )


@router.post("/questions", response_class=HTMLResponse)
def ask_question(
    request: Request,
    question: str = Form(...),
) -> HTMLResponse:
    source_titles: dict[str, str] = {}
    try:
        result = service.ask(question)
        for source in result.sources:
            if source.document_id and source.document_id not in source_titles:
                source_titles[source.document_id] = service.get_document_title(
                    source.document_id
                )
        error = None
    except QuestionsServiceError as exc:
        result = None
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "questions.html",
        {
            "active": "questions",
            "question": question,
            "result": result,
            "error": error,
            "source_titles": source_titles,
        },
    )
