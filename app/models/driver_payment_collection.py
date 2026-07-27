import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DriverPaymentCollection(Base):
    __tablename__ = "driver_payment_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trip_sheet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("trip_sheets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'PENDING'"))
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    order = relationship("Order", lazy="selectin")
    driver = relationship("Driver", lazy="selectin")
