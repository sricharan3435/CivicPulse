from fastapi import FastAPI

app = FastAPI(
    title="CivicPulse API",
    description="Smart Civic Issue Reporting",
    version="1.0.0"
)

@app.get("/")
async def home():
    return {
        "message": "Welcome to CivicPulse API",
        "status": "Running"
    }