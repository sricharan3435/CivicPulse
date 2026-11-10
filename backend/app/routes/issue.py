from fastapi import APIRouter
from app.schemas.issue import IssueCreate

router = APIRouter()

@router.post("/issues", status_code=201)
async def create_issue(issue: IssueCreate):
    return {
        "message" : "Issue received successfully",
        "issue": issue.model_dump()
    }