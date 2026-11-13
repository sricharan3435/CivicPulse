from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.connection import Base, engine
from app.models.issue import Issue  # noqa: F401 - registers the model with Base
from app.models.user import User, UserSession  # noqa: F401 - register auth tables
from app.routes.categories import router as categories_router
from app.routes.auth import router as auth_router
from app.routes.geocoding import router as geocoding_router
from app.routes.issue import admin_router, router as issue_router

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title="CivicPulse API",
    description="A community-powered civic issue reporting app",
    version="1.0.0",
)
app.include_router(issue_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(geocoding_router, prefix="/api")
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.on_event("startup")
def initialize_database():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": "CivicPulse API"}


@app.get("/", include_in_schema=False)
def home():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {
        "message": "CivicPulse API is running. Start the React app with `cd frontend && npm run dev`.",
        "frontend": "http://127.0.0.1:5173",
        "api_docs": "/docs",
    }


@app.get("/{path:path}", include_in_schema=False)
def spa_routes(path: str):
    if path.startswith(("api/", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    raise HTTPException(status_code=404, detail="Frontend has not been built")
