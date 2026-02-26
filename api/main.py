"""FastAPI application — thin API layer over the SEO linker core engine."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything reads os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import audit, candidates, config, gsc, pipeline, sitemap

app = FastAPI(
    title="SEO Internal Linker API",
    version="0.4.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(gsc.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
