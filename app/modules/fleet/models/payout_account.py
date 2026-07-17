import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DriverPayoutAccount(Base):
    __tablename__ = "driver_payout_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    account_holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ifsc_or_routing_code: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    driver = relationship("Driver", back_populates="payout_account", lazy="selectin")
