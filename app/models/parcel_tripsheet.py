import uuid
from datetime import datetime
from typing import Optional, Any

import pytz
from sqlalchemy import String, DateTime, JSON, Numeric, text, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

IST = pytz.timezone("Asia/Kolkata")

def _indian_time():
    return datetime.now(IST)


class ParcelTripSheetOrder(Base):
    __tablename__ = "parcel_tripsheet_orders"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_sheet_id: Mapped[str] = mapped_column(String(36), ForeignKey("parcel_tripsheets.id", ondelete="CASCADE"), nullable=False, index=True)
    parcel_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("parcel_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_indian_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_indian_time, onupdate=_indian_time)
    
    trip_sheet = relationship("ParcelTripSheet", back_populates="trip_sheet_orders")
    parcel_order = relationship("ParcelOrder", lazy="selectin")


class ParcelTripSheet(Base):
    __tablename__ = "parcel_tripsheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Driver details stored directly
    driver_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Vehicle details stored directly
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vehicle_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Routing information
    city_routes: Mapped[Any] = mapped_column(JSON, nullable=True)  # List of cities or string description
    city_destination: Mapped[str] = mapped_column(String(200), nullable=True)
    
    # Odometer readings
    starting_kilometer: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    ending_kilometer: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Metadata
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'Dispatched'"))
    
    # Ownership / scope
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    franchise_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("franchises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("warehouse_addresses.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_indian_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_indian_time, onupdate=_indian_time)

    # Relationships
    creator = relationship("User", lazy="selectin")
    franchise = relationship("Franchise", lazy="selectin")
    warehouse = relationship("WareHouseAddress", lazy="selectin")
    
    trip_sheet_orders = relationship(
        "ParcelTripSheetOrder",
        back_populates="trip_sheet",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
