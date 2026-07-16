from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApproveDriverRequest(BaseModel):
    franchise_id: str = Field(..., min_length=1)


class RejectDriverRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=1, max_length=500)


class VehicleOut(BaseModel):
    id: str
    type: str
    plate_number: str
    make: str
    model: str
    year: str
    color: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class FleetFileOut(BaseModel):
    document_type: str
    path: str
    content_type: Optional[str] = None
    original_filename: Optional[str] = None

    model_config = {"from_attributes": True}


class PayoutAccountOut(BaseModel):
    account_holder_name: str
    bank_name: str
    account_number: str
    ifsc_or_routing_code: str

    model_config = {"from_attributes": True}


class DriverListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    onboarding_status: str
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime


class DriverDetailOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    dob: Optional[date] = None
    onboarding_status: str
    status: str
    franchise_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    vehicle: Optional[VehicleOut] = None
    documents: list[FleetFileOut] = []
    payout_account: Optional[PayoutAccountOut] = None


class DriverListResponse(BaseModel):
    items: list[DriverListItem]
    total: int
