import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeliveryAssignment(Base):
    """
    Tracks the assignment of a delivery task to a driver and vehicle for a specific order.
    Can only be created when the order status is OUT_FOR_DELIVERY.
    An OTP is generated and sent to the delivery recipient's email. Verification is
    required to complete the delivery.
    """
    __tablename__ = "delivery_assignments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_delivery_assignment_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # The order being delivered
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # The consignee receiving the delivery
    consignee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consignees.id", ondelete="RESTRICT"), nullable=False
    )

    # The user (delivery recipient/contact) who will provide OTP verification
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Role-based scoping
    franchise_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True
    )


    # Snapshot of delivery address at time of assignment
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fleet assignment
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )

    # OTP fields
    otp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    otp_expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    otp_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )  # pending | verified

    # Assignment lifecycle status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'assigned'")
    )  # assigned | in_progress | completed | cancelled

    # Audit
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    # Relationships
    order = relationship("Order", lazy="selectin")
    consignee = relationship("Consignee", lazy="selectin")
    assigned_to_user = relationship("User", foreign_keys=[assigned_to_user_id], lazy="selectin")
    driver = relationship("Driver", lazy="selectin")
    vehicle = relationship("Vehicle", lazy="selectin")
    franchise = relationship("Franchise", lazy="selectin")
    warehouse = relationship("WareHouseAddress", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
