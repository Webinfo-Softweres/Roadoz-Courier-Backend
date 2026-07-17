import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    franchise_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(50), nullable=False)
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'draft'"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    franchise = relationship("Franchise", lazy="selectin")
