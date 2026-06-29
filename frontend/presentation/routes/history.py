from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from frontend.application.history import HistoryPageService, HistoryServiceError

router = APIRouter(tags=["history"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)
service = HistoryPageService()


def _parse_needs_review(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.lower() in {"1", "true", "yes", "on"}


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request) -> HTMLResponse:
    needs_review = _parse_needs_review(request.query_params.get("needs_review"))
    search = request.query_params.get("search", "")
    try:
        runs = service.list_runs(needs_review=needs_review, search=search or None)
        error = None
    except HistoryServiceError as exc:
        runs = []
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "active": "history",
            "runs": runs,
            "needs_review": request.query_params.get("needs_review", ""),
            "search": search,
            "error": error,
            "export_jsonl_url": service.export_url(
                fmt="jsonl",
                needs_review=needs_review,
                search=search or None,
            ),
            "export_csv_url": service.export_url(
                fmt="csv",
                needs_review=needs_review,
                search=search or None,
            ),
        },
    )


@router.get("/history/{run_id}", response_class=HTMLResponse)
def history_detail(request: Request, run_id: str) -> HTMLResponse:
    try:
        run = service.get_run(run_id)
        error = None
    except HistoryServiceError as exc:
        run = None
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "history_detail.html",
        {
            "active": "history",
            "run": run,
            "error": error,
        },
        status_code=404 if run is None and error else 200,
    )
