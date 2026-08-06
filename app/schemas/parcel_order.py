from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class ParcelPaymentMethod(str, Enum):
    PREPAID = "Prepaid"
    COD = "COD"
    TO_PAY = "To Pay"
    CREDIT = "Credit"


class ParcelROV(str, Enum):
    OWNER_RISK = "owner_risk"
    CARRIER_RISK = "carrier_risk"


class ParcelServiceType(str, Enum):
    SURFACE = "Surface"
    AIR = "Air"
    EXPRESS = "Express"


# ── Nested sender / receiver ──────────────────────────────────────────────────

class ParcelSenderIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    mobile: Optional[str] = Field(None, max_length=20)
    alternate_mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address_line_1: Optional[str] = Field(None, max_length=500)
    address_line_2: Optional[str] = Field(None, max_length=500)
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class ParcelReceiverIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    mobile: Optional[str] = Field(None, max_length=20)
    alternate_mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address_line_1: Optional[str] = Field(None, max_length=500)
    address_line_2: Optional[str] = Field(None, max_length=500)
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


# ── Create ────────────────────────────────────────────────────────────────────

class ParcelOrderCreate(BaseModel):
    sender: Optional[ParcelSenderIn] = None
    receiver: Optional[ParcelReceiverIn] = None

    payment_method: Optional[ParcelPaymentMethod] = None
    cod_amount: Optional[float] = Field(None, ge=0)
    prepaid_amount: Optional[float] = Field(None, ge=0)
    to_pay_amount: Optional[float] = Field(None, ge=0)
    credit_amount: Optional[float] = Field(None, ge=0)

    rov: Optional[ParcelROV] = None
    order_value: Optional[float] = Field(0, ge=0)

    service_type: Optional[ParcelServiceType] = ParcelServiceType.SURFACE
    freight_charge: Optional[float] = Field(0, ge=0)
    freight_gst: Optional[float] = Field(0, ge=0)
    total_freight: Optional[float] = Field(0, ge=0)

    # Package info
    weight_kg: Optional[float] = Field(None, ge=0)
    length_cm: Optional[float] = Field(None, ge=0)
    breadth_cm: Optional[float] = Field(None, ge=0)
    height_cm: Optional[float] = Field(None, ge=0)
    total_boxes: Optional[int] = Field(1, ge=1)

    # Product
    product_name: Optional[str] = Field(None, max_length=255)
    qty: Optional[int] = Field(1, ge=1)

    # Misc
    gst_number: Optional[str] = Field(None, max_length=20)
    eway_bill_number: Optional[str] = Field(None, max_length=30)
    invoicenumber: Optional[int] = None
    insurance: Optional[float] = Field(None, ge=0)
    regional_area: Optional[float] = Field(0, ge=0)
    remarks: Optional[str] = Field(None, max_length=500)


# ── Update (all optional) ─────────────────────────────────────────────────────

class ParcelOrderUpdate(BaseModel):
    sender: Optional[ParcelSenderIn] = None
    receiver: Optional[ParcelReceiverIn] = None

    payment_method: Optional[ParcelPaymentMethod] = None
    cod_amount: Optional[float] = Field(None, ge=0)
    prepaid_amount: Optional[float] = Field(None, ge=0)
    to_pay_amount: Optional[float] = Field(None, ge=0)
    credit_amount: Optional[float] = Field(None, ge=0)

    rov: Optional[ParcelROV] = None
    order_value: Optional[float] = Field(None, ge=0)

    service_type: Optional[ParcelServiceType] = None
    freight_charge: Optional[float] = Field(None, ge=0)
    freight_gst: Optional[float] = Field(None, ge=0)
    total_freight: Optional[float] = Field(None, ge=0)

    weight_kg: Optional[float] = Field(None, ge=0)
    length_cm: Optional[float] = Field(None, ge=0)
    breadth_cm: Optional[float] = Field(None, ge=0)
    height_cm: Optional[float] = Field(None, ge=0)
    total_boxes: Optional[int] = Field(None, ge=1)

    product_name: Optional[str] = Field(None, max_length=255)
    qty: Optional[int] = Field(None, ge=1)

    gst_number: Optional[str] = Field(None, max_length=20)
    eway_bill_number: Optional[str] = Field(None, max_length=30)
    invoicenumber: Optional[int] = None
    insurance: Optional[float] = Field(None, ge=0)
    regional_area: Optional[float] = Field(None, ge=0)
    remarks: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, max_length=50)


# ── Out (response) ────────────────────────────────────────────────────────────

class CreatorOut(BaseModel):
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    model_config = {"from_attributes": True}


class ParcelOrderOut(BaseModel):
    id: str
    order_number: str
    barcode: Optional[str] = None
    status: str

    # Sender
    sender_name: Optional[str] = None
    sender_mobile: Optional[str] = None
    sender_alternate_mobile: Optional[str] = None
    sender_email: Optional[str] = None
    sender_address_line_1: Optional[str] = None
    sender_address_line_2: Optional[str] = None
    sender_pincode: Optional[str] = None
    sender_city: Optional[str] = None
    sender_state: Optional[str] = None

    # Receiver
    receiver_name: Optional[str] = None
    receiver_mobile: Optional[str] = None
    receiver_alternate_mobile: Optional[str] = None
    receiver_email: Optional[str] = None
    receiver_address_line_1: Optional[str] = None
    receiver_address_line_2: Optional[str] = None
    receiver_pincode: Optional[str] = None
    receiver_city: Optional[str] = None
    receiver_state: Optional[str] = None

    # Payment
    payment_method: Optional[str] = None
    cod_amount: Optional[float] = None
    prepaid_amount: Optional[float] = None
    to_pay_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    rov: Optional[str] = None
    order_value: Optional[float] = None

    # Freight
    service_type: Optional[str] = None
    freight_charge: Optional[float] = None
    freight_gst: Optional[float] = None
    total_freight: Optional[float] = None

    # Package
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    total_boxes: Optional[int] = None

    # Product
    product_name: Optional[str] = None
    sku: Optional[str] = None
    qty: Optional[int] = None

    # Misc
    gst_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    invoicenumber: Optional[int] = None
    insurance: Optional[float] = None
    regional_area: Optional[float] = None
    remarks: Optional[str] = None

    # Meta
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParcelOrderListResponse(BaseModel):
    items: List[ParcelOrderOut]
    total: int
    page: int
    limit: int
    pages: int
