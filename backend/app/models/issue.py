from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fake: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    assigned_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
