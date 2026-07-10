import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Numeric, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Remittance(Base):
    """
    A batch of COD orders whose collected amount is remitted back
    to the franchise's bank account.
    """
    __tablename__ = "remittances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    franchise_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="CASCADE"), nullable=True, index=True
    )
    warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_addresses.id", ondelete="CASCADE"), nullable=True, index=True
    )

    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    # pending | processing | remitted
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))

    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    remitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    franchise = relationship("Franchise", lazy="selectin")
    orders = relationship(
        "RemittanceOrder", back_populates="remittance", cascade="all, delete-orphan", lazy="selectin"
    )


class RemittanceOrder(Base):
    """
    Junction table linking a remittance batch to individual COD orders.
    """
    __tablename__ = "remittance_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    remittance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("remittances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )

    cod_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    # Relationships
    remittance = relationship("Remittance", back_populates="orders")
    order = relationship("Order", lazy="selectin")
