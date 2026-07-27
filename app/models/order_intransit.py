import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import pytz

IST = pytz.timezone("Asia/Kolkata")

def indian_time():
    return datetime.now(IST)


class OrderInTransit(Base):
    """
    Stores the in-transit event for an order when a trip sheet is generated.
    Records the GPS location (lat/lng), pincode, and the franchise/warehouse 
    that dispatched the order.
    """
    __tablename__ = "order_intransit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_sheet_id: Mapped[str] = mapped_column(String(36), ForeignKey("trip_sheets.id", ondelete="CASCADE"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(30), default="In_transit", nullable=False)
    
    # GPS location at time of dispatch
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=True)
    pincode: Mapped[str] = mapped_column(String(10), nullable=True)

    # Who dispatched
    franchise_id: Mapped[str] = mapped_column(String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True)
    dispatched_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    order = relationship("Order", backref="intransit_records")
    franchise = relationship("Franchise", backref="intransit_records")
    dispatched_by_user = relationship("User", backref="intransit_dispatches", foreign_keys=[dispatched_by])

    created_at: Mapped[datetime] = mapped_column(DateTime, default=indian_time, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=indian_time, onupdate=indian_time, nullable=False)
