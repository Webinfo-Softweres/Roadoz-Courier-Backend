from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    dob: date
    phone: str = Field(..., min_length=5, max_length=30)
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None


class RegisterResponse(BaseModel):
    token: str
    refreshToken: str
    userId: str


class VehicleRequest(BaseModel):
    vehicleType: str = Field(..., min_length=1, max_length=50)
    registrationNumber: str = Field(..., min_length=1, max_length=50)
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: str = Field(..., min_length=4, max_length=10)
    color: Optional[str] = Field(None, max_length=50)


class SuccessMessageResponse(BaseModel):
    success: bool = True
    message: str


class UploadDocumentResponse(BaseModel):
    success: bool = True
    documentUrl: str


class BankDetailsRequest(BaseModel):
    accountHolderName: str = Field(..., min_length=1, max_length=200)
    bankName: str = Field(..., min_length=1, max_length=200)
    accountNumber: str = Field(..., min_length=1, max_length=50)
    ifscOrRoutingCode: str = Field(..., min_length=1, max_length=50)


DocumentType = Literal["vehicle_insurance", "license_front", "license_back"]
OnboardingStatus = Literal["incomplete", "pending_verification", "approved", "rejected"]


class DocumentSteps(BaseModel):
    vehicle_insurance: bool
    license_front: bool
    license_back: bool


class OnboardingSteps(BaseModel):
    personal: bool
    vehicle: bool
    documents: DocumentSteps
    payout: bool


class StatusResponse(BaseModel):
    status: OnboardingStatus
    submittedAt: Optional[datetime] = None
    steps: OnboardingSteps
