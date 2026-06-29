from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from frontend.application.audit import AuditPageService, AuditServiceError

router = APIRouter(tags=["audit"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)
service = AuditPageService()


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request) -> HTMLResponse:
    action = request.query_params.get("action", "")
    status = request.query_params.get("status", "")
    try:
        runs = service.list_runs(
            action=action or None,
            status=status or None,
        )
        actions = service.list_actions(runs)
        error = None
    except AuditServiceError as exc:
        runs = []
        actions = []
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "audit.html",
        {
            "active": "audit",
            "runs": runs,
            "action": action,
            "status": status,
            "actions": actions,
            "error": error,
        },
    )


@router.get("/audit/{run_id}", response_class=HTMLResponse)
def audit_detail(request: Request, run_id: str) -> HTMLResponse:
    try:
        run = service.get_run(run_id)
        error = None
    except AuditServiceError as exc:
        run = None
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "audit_detail.html",
        {
            "active": "audit",
            "run": run,
            "error": error,
        },
        status_code=404 if run is None and error else 200,
    )
