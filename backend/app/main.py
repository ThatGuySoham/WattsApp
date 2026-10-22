"""FastAPI entrypoint. Run: uvicorn app.main:app --reload --port 8000"""
import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.db.connection import close_pool, open_pool
from app.ml.regression import InsufficientDataError
from app.routers import analytics, appliances, households
from app.services.analytics import NotFoundError
from app.services.tariff import UnknownStateError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("wattsapp")


@asynccontextmanager
async def lifespan(_: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(title="WattsApp API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def not_found(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InsufficientDataError)
async def insufficient(_: Request, exc: InsufficientDataError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(UnknownStateError)
async def unknown_state(_: Request, exc: UnknownStateError):
    return JSONResponse(status_code=422, content={"detail": str(exc.args[0])})


@app.exception_handler(ValueError)
async def bad_value(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(psycopg.Error)
async def db_error(_: Request, exc: psycopg.Error):
    log.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": f"Database error: {exc.__class__.__name__}"})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(households.router)
app.include_router(appliances.router)
app.include_router(analytics.router)
