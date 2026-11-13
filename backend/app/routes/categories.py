from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def get_categories():
    return {"categories": ["Potholes", "Garbage", "Water Leaks", "Streetlight Failures", "Other"]}
