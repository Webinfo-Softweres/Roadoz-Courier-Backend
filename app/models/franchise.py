import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Franchise(Base):
    __tablename__ = "franchises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    franchise_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    proposed_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ownership_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detailed_business_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prior_experience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    years_active: Mapped[int | None] = mapped_column(Integer, nullable=True)

    office_space_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    office_ownership: Mapped[str | None] = mapped_column(String(20), nullable=True)
    staff_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internet_availability: Mapped[bool] = mapped_column(Boolean, default=False)
    computer_laptop: Mapped[bool] = mapped_column(Boolean, default=False)

    investment_capacity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_of_funds: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    existing_loans: Mapped[bool] = mapped_column(Boolean, default=False)

    preferred_service_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nearby_landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_codes_covered: Mapped[str | None] = mapped_column(String(500), nullable=True)

    doc_id_proof: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_address_proof: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_photographs: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_business_registration: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_bank_statement: Mapped[bool] = mapped_column(Boolean, default=False)

    agree_to_terms: Mapped[bool] = mapped_column(Boolean, default=False)
    submission_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submission_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821

    @property
    def full_name(self) -> str:
        return self.name

    @property
    def email_id(self) -> str:
        return self.email

    @property
    def mobile_number(self) -> str | None:
        return self.phone
