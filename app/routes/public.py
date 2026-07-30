"""
Public routes — NO authentication required.
These endpoints are safe to call without any Bearer token.
"""

from fastapi import APIRouter, Depends, Query,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.franchise import Franchise
from app.models.order import Order
from app.schemas.franchise import FranchiseMapItem, FranchiseMapResponse, FranchisePublicListResponse, FranchisePublicItem,CustomerEmailRequest
from sqlalchemy import func
from collections import defaultdict
from app.models.rate_master import RateMaster




router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/franchise/map", response_model=FranchiseMapResponse)
async def get_franchises_for_map(
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active status. Pass true for active only, false for inactive only. Omit to get all.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all franchises with their location data for map display.

    Returns: id, name, franchise_code, latitude, longitude,
             city, state, country, pincode, address, phone, is_active.

    **No authentication required.**
    """
    query = select(Franchise)
    if is_active is not None:
        query = query.where(Franchise.is_active == is_active)

    result = await db.execute(query)
    franchises = result.scalars().all()

    items = [FranchiseMapItem.model_validate(f) for f in franchises]
    return FranchiseMapResponse(total=len(items), items=items)


@router.get("/franchise/list", response_model=FranchisePublicListResponse)
async def get_public_franchises(
    state: Optional[str] = Query(None, description="Filter franchises by state"),
    country: Optional[str] = Query(None, description="Filter franchises by country"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of franchises with their total order count.
    Can be filtered by state and country.
    
    **No authentication required.**
    """
    # Create a subquery to count orders per franchise
    order_counts_subq = (
        select(Order.franchise_id, func.count(Order.id).label("total_orders_count"))
        .group_by(Order.franchise_id)
        .subquery()
    )

    query = (
        select(
            Franchise,
            func.coalesce(order_counts_subq.c.total_orders_count, 0).label("total_orders_count")
        )
        .outerjoin(order_counts_subq, Franchise.id == order_counts_subq.c.franchise_id)
        .where(Franchise.is_active == True)
    )

    if state:
        query = query.where(Franchise.state == state)
    if country:
        query = query.where(Franchise.country == country)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for franchise, total_orders_count in rows:
        item_data = FranchisePublicItem.model_validate(franchise).model_dump()
        item_data["total_orders_count"] = total_orders_count
        items.append(FranchisePublicItem(**item_data))

    return FranchisePublicListResponse(total=len(items), items=items)




@router.get("/rate-master")
async def get_public_rate_master(
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RateMaster).order_by(RateMaster.service_type,RateMaster.zone,RateMaster.weight_up_to))
    rates = result.scalars().all()
    data = {"Surface": defaultdict(list),"Express": defaultdict(list)}
    for rate in rates:
        data[rate.service_type][rate.zone].append({"id": rate.id,"weight_up_to": float(rate.weight_up_to),"base_rate": float(rate.base_rate),})
    return {"Surface": dict(data["Surface"]),"Express": dict(data["Express"])}






from pydantic import BaseModel, EmailStr


class CustomerEmailRequest(BaseModel):
    full_name: str
    customer_email: EmailStr
    phone_number: str
    inquiry_type: str
    subject: str
    message: str
    

@router.post("/send-email")
async def send_customer_email(request: CustomerEmailRequest):
    from app.utils.smtp import send_email
    target_email = "sreejeshmattannoor4203@gmail.com"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>📩 New Contact Form Submission</h2>
        <table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse;">
            <tr>
                <td><strong>Full Name</strong></td>
                <td>{request.full_name}</td>
            </tr>
            <tr>
                <td><strong>Email</strong></td>
                <td>{request.customer_email}</td>
            </tr>
            <tr>
                <td><strong>Phone Number</strong></td>
                <td>{request.phone_number}</td>
            </tr>
            <tr>
                <td><strong>Inquiry Type</strong></td>
                <td>{request.inquiry_type}</td>
            </tr>
            <tr>
                <td><strong>Subject</strong></td>
                <td>{request.subject}</td>
            </tr>
        </table>
        <br>
        <h3>Message</h3>
        <p>{request.message}</p>
        <hr>
        <p>
            <strong>Reply directly to this email</strong> to respond to
            <strong>{request.customer_email}</strong>.
        </p>
    </body>
    </html>
    """
    success = await send_email(
        to_email=target_email,
        subject=f"Contact Form - {request.subject}",
        body=html_body,
        reply_to=request.customer_email,
    )
    if success:
        return {"message": "Email sent successfully"}
    raise HTTPException(status_code=500, detail="Failed to send email")