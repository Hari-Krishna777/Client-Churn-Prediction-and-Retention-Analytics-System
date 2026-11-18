from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import ALLOWED_HOSTS, CORS_ORIGINS, ENABLE_SECURITY_HEADERS, HTTPS_ENFORCE

from app.database.connection import init_db
from app.routes.health import router as health_router
from app.routes.predictions import router as prediction_router
from app.routes.batch import router as batch_router
from app.routes.analytics import router as analytics_router
from app.routes.datasets import router as datasets_router
from app.routes.auth import router as auth_router
from app.routes.retention import router as retention_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Production schema changes are applied through Alembic, not implicitly at
    # application startup.  This opt-in keeps local SQLite development simple
    # while preventing an API deployment from bypassing reviewed migrations.
    if os.getenv("AUTO_CREATE_SCHEMA", "false").lower() in {"1", "true", "yes"}:
        init_db()
    yield


app = FastAPI(
    title="ChurnIQ — Client Churn Prediction API",
    description="ML-powered customer churn prediction, batch analytics, SHAP explainability, retention recommendation engine, and PostgreSQL persistence",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware to support frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
if HTTPS_ENFORCE:
    app.add_middleware(HTTPSRedirectMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


if ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(batch_router)
app.include_router(analytics_router)
app.include_router(datasets_router)
app.include_router(auth_router)
app.include_router(retention_router)


@app.get("/")
def root():
    return {
        "app": "ChurnIQ API",
        "status": "online",
        "version": "3.0.0",
        "documentation": "/docs"
    }
