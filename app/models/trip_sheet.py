import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, JSON, Integer, text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TripSheet(Base):
    __tablename__ = "trip_sheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Role-based scoping
    franchise_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Destination & Routing
    is_local: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    route_city : Mapped[list | None] = mapped_column(JSON, nullable=True)
    destination_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    destination_franchise_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True)
    route_franchise_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True) # store as JSON list
    
    # Fleet
    driver_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Freight & Packages totals
    topay_freight: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    topay_packages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    credit_freight: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    credit_packages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cod_freight: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    cod_packages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    prepaid_freight: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    prepaid_packages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    
    total_freight: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    total_packages: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    
    # Driver mobile lifecycle
    driver_status: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Audit
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    # Relationships
    orders = relationship("TripSheetOrder", back_populates="trip_sheet", cascade="all, delete-orphan", lazy="selectin")
    driver = relationship("Driver", lazy="selectin")
    vehicle = relationship("Vehicle", lazy="selectin")
    franchise = relationship("Franchise", foreign_keys=[franchise_id], lazy="selectin")
    destination_franchise = relationship("Franchise", foreign_keys=[destination_franchise_id], lazy="selectin")
    creator = relationship("User", lazy="selectin")


class TripSheetOrder(Base):
    __tablename__ = "trip_sheet_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_sheet_id: Mapped[str] = mapped_column(String(36), ForeignKey("trip_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    sl_no: Mapped[int] = mapped_column(Integer, nullable=False)

    trip_sheet = relationship("TripSheet", back_populates="orders")
    order = relationship("Order", lazy="selectin")
