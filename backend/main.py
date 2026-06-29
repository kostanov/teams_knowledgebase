from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes import ai, ask, audit_runs, documents, history
from backend.persistence.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Система знаний команды — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents.router)
app.include_router(ask.router)
app.include_router(ai.router)
app.include_router(history.router)
app.include_router(audit_runs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
