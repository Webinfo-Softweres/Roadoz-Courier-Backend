from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date


class FranchiseCreate(BaseModel):
    full_name: str
    date_of_birth: date
    gender: str
    mobile_number: str
    email_id: EmailStr
    password: str
    current_address: str
    permanent_address: Optional[str] = None

    proposed_location: str
    ownership_type: str
    detailed_business_address: str
    prior_experience: Optional[str] = None
    years_active: Optional[int] = None

    office_space_sqft: int
    office_ownership: str
    staff_count: int
    internet_availability: bool = False
    computer_laptop: bool = False

    investment_capacity: str
    source_of_funds: Optional[str] = None
    bank_name: str
    account_number: str
    existing_loans: bool = False
    existing_loan_details: Optional[str] = None

    preferred_service_area: str
    nearby_landmark: Optional[str] = None
    pin_codes_covered: str

    doc_id_proof: bool = False
    doc_address_proof: bool = False
    doc_photographs: bool = False
    doc_business_registration: bool = False
    doc_bank_statement: bool = False

    agree_to_terms: bool
    submission_place: Optional[str] = None
    submission_date: Optional[date] = None


class FranchiseUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    mobile_number: Optional[str] = None
    email_id: Optional[EmailStr] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None

    proposed_location: Optional[str] = None
    ownership_type: Optional[str] = None
    detailed_business_address: Optional[str] = None
    prior_experience: Optional[str] = None
    years_active: Optional[int] = None

    office_space_sqft: Optional[int] = None
    office_ownership: Optional[str] = None
    staff_count: Optional[int] = None
    internet_availability: Optional[bool] = None
    computer_laptop: Optional[bool] = None

    investment_capacity: Optional[str] = None
    source_of_funds: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    existing_loans: Optional[bool] = None
    existing_loan_details: Optional[str] = None

    preferred_service_area: Optional[str] = None
    nearby_landmark: Optional[str] = None
    pin_codes_covered: Optional[str] = None

    doc_id_proof: Optional[bool] = None
    doc_address_proof: Optional[bool] = None
    doc_photographs: Optional[bool] = None
    doc_business_registration: Optional[bool] = None
    doc_bank_statement: Optional[bool] = None

    agree_to_terms: Optional[bool] = None
    submission_place: Optional[str] = None
    submission_date: Optional[date] = None

    is_active: Optional[bool] = None


class FranchiseResponse(BaseModel):
    id: str
    user_id: str
    franchise_code: str
    full_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    mobile_number: Optional[str]
    email_id: str
    current_address: Optional[str]
    permanent_address: Optional[str]

    proposed_location: Optional[str]
    ownership_type: Optional[str]
    detailed_business_address: Optional[str]
    prior_experience: Optional[str]
    years_active: Optional[int]

    office_space_sqft: Optional[int]
    office_ownership: Optional[str]
    staff_count: Optional[int]
    internet_availability: bool
    computer_laptop: bool

    investment_capacity: Optional[str]
    source_of_funds: Optional[str]
    bank_name: Optional[str]
    account_number: Optional[str]
    existing_loans: bool
    existing_loan_details: Optional[str] = None

    preferred_service_area: Optional[str]
    nearby_landmark: Optional[str]
    pin_codes_covered: Optional[str]

    doc_id_proof: bool
    doc_address_proof: bool
    doc_photographs: bool
    doc_business_registration: bool
    doc_bank_statement: bool

    agree_to_terms: bool
    submission_place: Optional[str]
    submission_date: Optional[date]

    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FranchiseListResponse(BaseModel):
    items: List[FranchiseResponse]
    total: int
    page: int
    limit: int
    pages: int
