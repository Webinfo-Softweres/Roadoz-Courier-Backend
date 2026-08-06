from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeliveryAssignmentCreate(BaseModel):
    order_barcodes: list[str]
    driver_id: str
    vehicle_id: str


class VerifyOTPRequest(BaseModel):
    otp: str


class DriverBrief(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class VehicleBrief(BaseModel):
    id: str
    type: str
    plate_number: str
    make: str
    model: str

    model_config = {"from_attributes": True}


from app.schemas.order import OrderOut, ConsigneeOut

class DeliveryAssignmentOut(BaseModel):
    id: str
    order_id: str
    consignee_id: str
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    driver_id: str
    vehicle_id: str
    delivery_address: Optional[str] = None
    otp_status: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    driver: Optional[DriverBrief] = None
    vehicle: Optional[VehicleBrief] = None
    order: Optional[OrderOut] = None
    consignee: Optional[ConsigneeOut] = None

    model_config = {"from_attributes": True}


class DeliveryAssignmentListResponse(BaseModel):
    total: int
    items: list[DeliveryAssignmentOut]
