from fastapi import FastAPI

from frontend.presentation.routes import audit, documents, history, questions

app = FastAPI(
    title="Система знаний команды — Frontend",
    version="0.1.0",
)

app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(history.router)
app.include_router(audit.router)
