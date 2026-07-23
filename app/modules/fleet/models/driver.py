import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    franchise_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vehicle_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    onboarding_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'incomplete'"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'draft'"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", lazy="selectin")
    franchise = relationship("Franchise", lazy="selectin")
    warehouse = relationship("WareHouseAddress", lazy="selectin")
    vehicle = relationship("Vehicle", lazy="selectin")
    payout_account = relationship(
        "DriverPayoutAccount", back_populates="driver", uselist=False, lazy="selectin"
    )
