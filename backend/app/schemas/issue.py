
from pydantic import BaseModel, Field
from typing import Literal


class IssueCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=10, max_length=1000)

    category: Literal[
        "Potholes",
        "Garbage",
        "Water Leaks",
        "Streetlight Failures"
    ]

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
