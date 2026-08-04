from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal
from app.schemas.order import OrderType, PaymentMethod, ROV, ServiceType, OrderItemCreate, OrderPackageCreate
from app.schemas.order import PickupAddressCreate, ConsigneeCreate


class ConsigneeOrderCreatePayload(BaseModel):
    # Customer must choose exactly one destination: franchise OR warehouse
    franchise_id: Optional[str] = Field(None, description="ID of the franchise chosen to process this order")
    warehouse_id: Optional[str] = Field(None, description="ID of the warehouse chosen to process this order")
    
    # Pick existing by ID...
    pickup_address_id: Optional[str] = Field(None, description="ID of existing sender's pickup address")
    consignee_id: Optional[str] = Field(None, description="ID of existing receiver's consignee record")
    
    # ...OR create new
    sender_details: Optional[PickupAddressCreate] = None
    receiver_details: Optional[ConsigneeCreate] = None
    
    order_type: OrderType
    payment_method: PaymentMethod
    cod_amount: Optional[float] = Field(None, ge=0, description="Required when payment_method is COD")
    to_pay_amount: Optional[float] = Field(None, ge=0, description="Required when payment_method is To Pay")
    credit_amount: Optional[float] = Field(None, ge=0, description="Required when payment_method is Credit")
    prepaid_amount: Optional[float] = Field(None, ge=0, description="Required when payment_method is Prepaid")
    rov: ROV
    order_value: float = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_addresses_and_payments(self):
        # Exactly one of franchise_id or warehouse_id must be provided
        if not self.franchise_id and not self.warehouse_id:
            raise ValueError("Either franchise_id or warehouse_id must be provided")
        if self.franchise_id and self.warehouse_id:
            raise ValueError("Provide only one of franchise_id or warehouse_id, not both")

        if not self.pickup_address_id and not self.sender_details:
            raise ValueError("Either pickup_address_id or sender_details must be provided")
        if not self.consignee_id and not self.receiver_details:
            raise ValueError("Either consignee_id or receiver_details must be provided")
            
        if self.payment_method == PaymentMethod.COD and self.cod_amount is None:
            raise ValueError("cod_amount is required when payment_method is COD")
        if self.payment_method == PaymentMethod.TO_PAY and self.to_pay_amount is None:
            raise ValueError("to_pay_amount is required when payment_method is To Pay")
        if self.payment_method == PaymentMethod.CREDIT and self.credit_amount is None:
            raise ValueError("credit_amount is required when payment_method is Credit")
        if self.payment_method == PaymentMethod.PREPAID and self.prepaid_amount is None:
            raise ValueError("prepaid_amount is required when payment_method is Prepaid")
            
        if self.payment_method == PaymentMethod.COD:
            self.to_pay_amount = None
            self.credit_amount = None
            self.prepaid_amount = None
        elif self.payment_method == PaymentMethod.TO_PAY:
            self.cod_amount = None
            self.credit_amount = None
            self.prepaid_amount = None
        elif self.payment_method == PaymentMethod.CREDIT:
            self.cod_amount = None
            self.to_pay_amount = None
            self.prepaid_amount = None
        elif self.payment_method == PaymentMethod.PREPAID:
            self.cod_amount = None
            self.to_pay_amount = None
            self.credit_amount = None
        return self

    items: List[OrderItemCreate] = Field(..., min_length=1)
    packages: List[OrderPackageCreate] = Field(..., min_length=1)

    service_type: ServiceType = Field(ServiceType.SURFACE)

    gst_number: Optional[str] = Field(None, max_length=20)
    eway_bill_number: Optional[str] = Field(None, max_length=30)
    invoicenumber: Optional[int] = None
    amount: Optional[int] = None
    insurance: bool = False
    regional_area: float | None = 0
    
    is_doc: bool = False
    delivery_type: Literal["office", "home"] | None = None
