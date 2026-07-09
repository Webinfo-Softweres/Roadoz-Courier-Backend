import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MonthEndClosing(Base):
    """
    Month-end account closing process where franchises submit final payments.
    """
    __tablename__ = "month_end_closings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    franchise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="CASCADE"), nullable=False, index=True
    )

    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_owner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    
    admin_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    franchise = relationship("Franchise", lazy="selectin")
