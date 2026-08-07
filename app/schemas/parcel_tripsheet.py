from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


class ParcelTripSheetCreate(BaseModel):
    # Store all order barcodes assigned to this trip
    barcodes: List[str] = Field(..., description="List of parcel order barcodes")
    
    # Driver details
    driver_name: Optional[str] = Field(None, max_length=150)
    mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    
    # Vehicle details
    vehicle_number: Optional[str] = Field(None, max_length=50)
    vehicle_type: Optional[str] = Field(None, max_length=100)
    vehicle_model: Optional[str] = Field(None, max_length=100)
    fuel_type: Optional[str] = Field(None, max_length=50)
    
    city_routes: Optional[List[Any]] = Field(None, description="List of routes")
    city_destination: Optional[str] = Field(None, description="Destination city")
    
    # Odometer readings
    starting_kilometer: Optional[float] = Field(None, description="Starting KM reading")
    ending_kilometer: Optional[float] = Field(None, description="Ending KM reading")


class ParcelTripSheetUpdate(BaseModel):
    barcodes: Optional[List[str]] = Field(None, description="List of parcel order barcodes")
    driver_name: Optional[str] = Field(None, max_length=150)
    mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None)
    vehicle_number: Optional[str] = Field(None, max_length=50)
    vehicle_type: Optional[str] = Field(None, max_length=100)
    vehicle_model: Optional[str] = Field(None, max_length=100)
    fuel_type: Optional[str] = Field(None, max_length=50)
    city_routes: Optional[List[Any]] = Field(None, description="List of routes")
    city_destination: Optional[str] = Field(None, description="Destination city")
    starting_kilometer: Optional[float] = Field(None, description="Starting KM reading")
    ending_kilometer: Optional[float] = Field(None, description="Ending KM reading")
    status: Optional[str] = Field(None, description="Tripsheet status")


class ParcelTripSheetOut(BaseModel):
    id: str
    
    # Driver details
    driver_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    
    # Vehicle details
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_model: Optional[str] = None
    fuel_type: Optional[str] = None
    
    city_routes: Optional[List[Any]] = None
    city_destination: Optional[str] = None
    starting_kilometer: Optional[float] = None
    ending_kilometer: Optional[float] = None
    status: str
    
    created_by: str
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ParcelTripSheetDetail(ParcelTripSheetOut):
    parcel_orders: List[Any] = Field(..., description="List of parcel order details")

class ParcelTripSheetListResponse(BaseModel):
    items: List[ParcelTripSheetOut]
    total: int
    page: int
    limit: int
    pages: int
