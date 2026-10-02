import logging
import os
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import BACKEND_DIR, CORS_ORIGINS
from database import engine, Base
from migrate_db import migrate
from init_db import init_db
from seed_data import seed_db
from routers import ocr, employees, documents, auth, users, audit, backups, settings, templates, references, errors, absences

logger = logging.getLogger("ns-system")
logging.basicConfig(level=logging.INFO)
logger.addHandler(logging.FileHandler(os.path.join(BACKEND_DIR, "errors.log"), encoding="utf-8"))

app = FastAPI(title="NS SYSTEM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

migrate()
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def on_startup():
    init_db()
    seed_db()


def _error_payload(code: str, message: str, status_code: int):
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "code": code, "message": message},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Не удалось выполнить операцию."
    return _error_payload(f"E{exc.status_code}", detail, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_payload("E422", "Проверьте введённые данные.", 422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    code = uuid.uuid4().hex[:8].upper()
    logger.error("Unhandled error %s\n%s", code, traceback.format_exc())
    return _error_payload(f"E500-{code}", "Не удалось выполнить операцию. Попробуйте ещё раз.", 500)


app.include_router(auth.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(absences.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(backups.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(errors.router, prefix="/api")
app.include_router(references.router, prefix="/api")
