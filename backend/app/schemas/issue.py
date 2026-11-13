from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Category = Literal["Potholes", "Garbage", "Water Leaks", "Streetlight Failures", "Other"]
IssueStatus = Literal["pending", "in_progress", "resolved"]


class IssueCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    category: Category
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("image_url")
    @classmethod
    def validate_cloudinary_url(cls, value):
        if value is not None:
            parsed = urlparse(value)
            if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
                raise ValueError("Photo URL must be a secure Cloudinary URL")
        return value


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueReviewUpdate(BaseModel):
    status: IssueStatus | None = None
    verified: bool | None = None
    is_fake: bool | None = None
    assigned_team: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def require_non_null_updates(self):
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Status cannot be null")
        if "verified" in self.model_fields_set and self.verified is None:
            raise ValueError("Verified cannot be null")
        if "is_fake" in self.model_fields_set and self.is_fake is None:
            raise ValueError("Fake status cannot be null")
        return self


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    latitude: float
    longitude: float
    status: str
    image_url: str | None = None
    verified: bool
    is_fake: bool
    assigned_team: str | None = None
    priority_score: float
    duplicate_of_id: int | None = None
    created_at: datetime
    updated_at: datetime


class UploadRead(BaseModel):
    image_url: str
