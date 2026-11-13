import os
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.database.connection import get_db
from app.models.issue import Issue
from app.models.user import User
from app.routes.auth import get_admin_user, get_current_user, get_optional_user
from app.schemas.issue import IssueCreate, IssueRead, IssueReviewUpdate, IssueStatusUpdate
from app.services.prioritization import analyze_report

router = APIRouter(prefix="/issues", tags=["issues"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def issue_stats(db: Session = Depends(get_db)):
    public_issues = Issue.is_fake.is_(False)
    total = db.scalar(select(func.count()).select_from(Issue).where(public_issues)) or 0
    rows = db.execute(select(Issue.status, func.count()).where(public_issues).group_by(Issue.status)).all()
    counts = {"pending": 0, "in_progress": 0, "resolved": 0}
    counts.update({key: value for key, value in rows})
    return {"total": total, **counts}


@router.post("/upload")
async def upload_issue_photo(request: Request):
    required = ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    if not all(os.getenv(name) for name in required):
        raise HTTPException(status_code=503, detail="Photo uploads require Cloudinary configuration")
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 11 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo must be 10 MB or smaller")
    form = await request.form()
    photo = form.get("photo")
    if not isinstance(photo, StarletteUploadFile):
        raise HTTPException(status_code=422, detail="Select an image photo")
    try:
        latitude = float(form.get("latitude", ""))
        longitude = float(form.get("longitude", ""))
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="A valid location is required to watermark the photo")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="The photo location is outside valid coordinates")
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP photo")
    raw = await photo.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo must be 10 MB or smaller")
    try:
        from PIL import Image, ImageDraw, ImageOps
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
            api_key=os.environ["CLOUDINARY_API_KEY"],
            api_secret=os.environ["CLOUDINARY_API_SECRET"],
            secure=True,
        )
        image = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
        image.thumbnail((2400, 2400))
        watermark = f"CivicPulse  |  {latitude:.5f}, {longitude:.5f}  |  {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}"
        draw = ImageDraw.Draw(image, "RGBA")
        box = draw.textbbox((0, 0), watermark)
        width, height = box[2] - box[0], box[3] - box[1]
        draw.rectangle((10, image.height - height - 25, width + 30, image.height - 10), fill=(0, 0, 0, 150))
        draw.text((20, image.height - height - 18), watermark, fill=(255, 255, 255, 240))
        output = BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        result = cloudinary.uploader.upload(
            output.getvalue(), folder="civicpulse/reports", resource_type="image",
            format="jpg", transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
        return {"image_url": result["secure_url"]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not process or upload that image") from exc


@router.get("", response_model=list[IssueRead])
def list_issues(
    category: str | None = None,
    issue_status: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = select(Issue)
    if not user or user.role != "admin":
        query = query.where(Issue.is_fake.is_(False))
    if category:
        query = query.where(Issue.category == category)
    if issue_status:
        query = query.where(Issue.status == issue_status)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Issue.title.ilike(term), Issue.description.ilike(term)))
    return db.scalars(query.order_by(Issue.priority_score.desc(), Issue.created_at.desc(), Issue.id.desc()).offset(offset).limit(limit)).all()


@router.get("/{issue_id}", response_model=IssueRead)
def get_issue(issue_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if not issue or (issue.is_fake and (not user or user.role != "admin")):
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("", response_model=IssueRead, status_code=status.HTTP_201_CREATED)
def create_issue(payload: IssueCreate, reporter: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = payload.model_dump()
    image_url = values.pop("image_url", None)
    recent = db.scalars(select(Issue).order_by(Issue.created_at.desc()).limit(500)).all()
    score, duplicate_of_id = analyze_report(
        values["title"], values["description"], values["category"], values["latitude"], values["longitude"], recent
    )
    issue = Issue(**values, image_url=image_url,
                  priority_score=score, duplicate_of_id=duplicate_of_id, reporter_id=reporter.id)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.patch("/{issue_id}/status", response_model=IssueRead)
def update_issue_status(
    issue_id: int,
    payload: IssueStatusUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = payload.status
    db.commit()
    db.refresh(issue)
    return issue


@admin_router.patch("/issues/{issue_id}", response_model=IssueRead)
def review_issue(
    issue_id: int,
    payload: IssueReviewUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    return issue


@admin_router.get("/analytics")
def admin_analytics(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    issues = db.scalars(select(Issue)).all()
    if not issues:
        return {"by_category": [], "average_priority": 0, "potential_duplicates": 0, "fake_issues": 0}
    try:
        import numpy as np
        import pandas as pd

        frame = pd.DataFrame([{
            "category": issue.category,
            "status": issue.status,
            "priority": issue.priority_score,
            "duplicate": issue.duplicate_of_id is not None,
        } for issue in issues])
        by_category = frame.groupby(["category", "status"], as_index=False).size().to_dict("records")
        average = round(float(np.mean(frame["priority"].to_numpy())), 1)
        duplicates = int(frame["duplicate"].sum())
    except ImportError:
        by_category = [{"category": name, "status": status_name, "size": count}
                       for (name, status_name), count in _group_counts(issues).items()]
        average = round(sum(issue.priority_score for issue in issues) / len(issues), 1)
        duplicates = sum(issue.duplicate_of_id is not None for issue in issues)
    fake_issues = sum(issue.is_fake for issue in issues)
    return {"by_category": by_category, "average_priority": average, "potential_duplicates": duplicates, "fake_issues": fake_issues}


def _group_counts(issues):
    counts = {}
    for issue in issues:
        key = (issue.category, issue.status)
        counts[key] = counts.get(key, 0) + 1
    return counts
