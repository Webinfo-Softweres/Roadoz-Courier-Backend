from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

from app.core.database import Base

class RazorpayTransaction(Base):
    __tablename__ = "razorpay_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    razorpay_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    
    status: Mapped[str] = mapped_column(String(30), default="created") # created, paid, failed
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to order
    order = relationship("Order", backref="razorpay_transactions")
