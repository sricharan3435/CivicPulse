from fastapi import FastAPI
from app.routes.issue import router as issue_router
from app.routes.categories import router as categories_router

app = FastAPI(
    title="CivicPulse API",
    description="Smart Civic Issue Reporting",
    version="1.0.0"
)

app.include_router(issue_router, prefix="/api")
app.include_router(categories_router, prefix="/api")

@app.get("/")
async def home():
    return {
        "message": "Welcome to CivicPulse API",
        "status": "Running"
    }




