from fastapi import APIRouter

router = APIRouter()

@router.get("/categories")
async def get_categories():
    return {
        "categories": [
            "Potholes",
            "Garbage",
            "Water Leaks",
            "Streetlight Failures"
        ]
    }
