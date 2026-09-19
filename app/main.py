from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import Base, engine
# Import models to ensure they register with Base.metadata
import app.models  # noqa: F401
from app.api.v1.api import api_router

# OpenAPI Tag Metadata for Swagger UI
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, JWT token authentication, and user profile management.",
    },
    {
        "name": "Documents",
        "description": "Upload examination PDFs and images, list documents, and poll asynchronous processing status.",
    },
    {
        "name": "Questions",
        "description": "Retrieve extracted questions, options, types, and source page traceability.",
    },
    {
        "name": "Answers",
        "description": "Retrieve parsed answer keys and questions matched with answers.",
    },
    {
        "name": "Review",
        "description": "Retrieve items flagged for human verification (low confidence, OCR errors, malformed options, etc.).",
    },
    {
        "name": "Relationships",
        "description": "Establish relationships between documents (e.g. associating separate Question Paper and Answer Key PDFs).",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and directories are ready
    logger.info("Initializing application and database schemas...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Production-grade Document Processing & Question Extraction Service. "
        "Converts PDF documents and examination images into structured questions, "
        "extracts options, detects answer keys, computes confidence scores, and flags review items."
    ),
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please check server logs."}
    )


from starlette.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

# Mount static frontend and sample documents
os.makedirs("app/static", exist_ok=True)
os.makedirs("sample_documents", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/samples", StaticFiles(directory="sample_documents"), name="samples")


# Root route serves interactive studio frontend
@app.get("/", response_class=FileResponse, include_in_schema=False)
def index():
    return FileResponse(os.path.join("app", "static", "index.html"))


@app.get("/info", tags=["Health"], summary="Service Info")
def root_info():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health", tags=["Health"], summary="Health check")
def health_check():
    return {"status": "ok"}


# Include API v1 routes both with /api/v1 prefix and at root for convenience
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router)
