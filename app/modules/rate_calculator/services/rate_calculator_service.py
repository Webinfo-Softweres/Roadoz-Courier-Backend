import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.modules.rate_calculator.schemas.rate_calculator import (
    RateCalculationData,
    RateCalculationRequest,
    RateCalculationResponse,
    PricingBreakdown,
)
from app.modules.rate_calculator.services.weight_engine import WeightEngine
from app.modules.rate_calculator.utils.validators import validate_calculation_request
from app.services.rate_calculator.pincode_service import get_pincode_details
from app.models.rate_master import RateMaster

logger = logging.getLogger(__name__)


# ── Helper: Linear Interpolation Rate Calculator ───────────────────────────

def calculate_exact_rate(applicable_weight: float, rate_rows: list) -> tuple[float, float]:
    """
    Calculate exact freight charge using linear interpolation between slabs.

    Rules:
      1. weight <= first slab  → return first slab rate (minimum rate)
      2. weight == exact slab  → return that slab rate directly
      3. weight between slabs  → linear interpolation between lower and upper slab
      4. weight > last slab    → returns (0.0, 0.0) — caller must set is_manual_freight=True

    Args:
        applicable_weight: The chargeable weight in kg.
        rate_rows: List of RateMaster rows sorted by weight_up_to ascending.

    Returns:
        (freight_charge, applied_weight_slab)
    """
    if not rate_rows:
        return 0.0, 0.0

    # Sort defensively (already sorted, but ensures correctness)
    rows = sorted(rate_rows, key=lambda r: float(r.weight_up_to))

    first = rows[0]
    last = rows[-1]

    # Rule 1: weight is at or below the first slab → minimum rate
    if applicable_weight <= float(first.weight_up_to):
        return round(float(first.base_rate), 2), float(first.weight_up_to)

    # Rule 4: weight is above the largest slab → extrapolate using last two slabs
    if applicable_weight > float(last.weight_up_to):
        second_last      = rows[-2]
        last_weight      = float(last.weight_up_to)
        last_rate        = float(last.base_rate)
        second_last_weight = float(second_last.weight_up_to)
        second_last_rate   = float(second_last.base_rate)

        price_per_kg = (last_rate - second_last_rate) / (last_weight - second_last_weight)
        extra        = applicable_weight - last_weight
        exact_rate   = last_rate + (extra * price_per_kg)

        return round(exact_rate, 2), last_weight

    # Rules 2 & 3: find the correct pair of slabs
    for i in range(len(rows) - 1):
        lower = rows[i]
        upper = rows[i + 1]

        lower_weight = float(lower.weight_up_to)
        upper_weight = float(upper.weight_up_to)
        lower_rate   = float(lower.base_rate)
        upper_rate   = float(upper.base_rate)

        if lower_weight < applicable_weight <= upper_weight:
            # Rule 2: exactly on the upper slab
            if applicable_weight == upper_weight:
                return round(upper_rate, 2), upper_weight

            # Rule 3: between two slabs — linear interpolation
            price_per_kg = (upper_rate - lower_rate) / (upper_weight - lower_weight)
            extra        = applicable_weight - lower_weight
            exact_rate   = lower_rate + (extra * price_per_kg)

            return round(exact_rate, 2), upper_weight

    # Fallback (should never reach here)
    return round(float(last.base_rate), 2), float(last.weight_up_to)


# ── Rate Calculator Service ────────────────────────────────────────────────

class RateCalculatorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.weight_engine = WeightEngine()

    async def calculate(self, payload: RateCalculationRequest) -> RateCalculationResponse:
        logger.info("Incoming rate calculation payload: %s", payload.model_dump())
        validate_calculation_request(payload)

        pickup = await self._validate_serviceability(payload.pickup_pincode, "pickup")
        delivery = await self._validate_serviceability(payload.delivery_pincode, "delivery")
        logger.info(
            "Serviceability validated pickup=%s/%s delivery=%s/%s",
            pickup.city,
            pickup.state,
            delivery.city,
            delivery.state,
        )

        weights = self.weight_engine.calculate(payload, divisor=2700.0)
        
        zone = self._determine_zone(
            payload.service_type.value, pickup.state, delivery.state
        )
        
        is_manual_freight = False

        # Fetch ALL rate rows for this service + zone (sorted ascending)
        rate_rows = await self._get_all_rates_from_db(payload.service_type.value, zone)

        if not rate_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No rate defined for Service: {payload.service_type.value}, Zone: {zone}",
            )

        base_rate, applied_slab = calculate_exact_rate(weights.chargeable_weight, rate_rows)

        logger.info(
            "Rate calculated weight=%.3fkg zone=%s base_rate=%.2f applied_slab=%.1f",
            weights.chargeable_weight, zone, base_rate, applied_slab,
        )
            
        if is_manual_freight:
            gst_amount = 0.0
            final_amount = 0.0
        else:
            if payload.is_gst_exempt:
                gst_amount = 0.0
            else:
                gst_amount = round(base_rate * 0.18, 2)
            final_amount = round(base_rate + gst_amount, 2)

        pricing = PricingBreakdown(
            freight_charge=base_rate,
            freight_gst=gst_amount,
            total_freight=final_amount,
            is_manual_freight=is_manual_freight,
            zone=zone,
            applied_weight_slab=applied_slab,
        )

        return RateCalculationResponse(
            data=RateCalculationData(
                calculator_type=payload.calculator_type,
                physical_weight=weights.physical_weight,
                volumetric_weight=weights.volumetric_weight,
                chargeable_weight=weights.chargeable_weight,
                pricing=pricing,
            )
        )

    def _determine_zone(self, service_type: str, pickup_state: str, delivery_state: str) -> str:
        from app.constants.tariff_rates import SOUTH_INDIA_STATES
        
        p_state = (pickup_state or "").strip().lower()
        d_state = (delivery_state or "").strip().lower()

        is_south_india = p_state in SOUTH_INDIA_STATES and d_state in SOUTH_INDIA_STATES
        is_kerala = p_state == "kerala" and d_state == "kerala"

        if service_type == "Surface":
            if is_kerala:
                return "Kerala within State"
            if is_south_india:
                return "South India"
            return "Rest of India"
        elif service_type == "Express":
            if is_south_india:
                return "South India Express"
            return "All India Express"
            
        return "Rest of India"

    async def _get_all_rates_from_db(self, service_type: str, zone: str) -> list:
        """Fetch all RateMaster rows for a service + zone, sorted by weight_up_to ascending."""
        result = await self.db.execute(
            select(RateMaster).where(
                and_(
                    RateMaster.service_type == service_type,
                    RateMaster.zone == zone,
                )
            ).order_by(RateMaster.weight_up_to.asc())
        )
        return result.scalars().all()

    async def _validate_serviceability(self, pincode: str, label: str):
        try:
            return await get_pincode_details(self.db, pincode)
        except HTTPException as exc:
            logger.warning("Failed %s pincode serviceability check pincode=%s detail=%s", label, pincode, exc.detail)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label.title()} pincode is not serviceable.",
            ) from exc


async def calculate_rate(db: AsyncSession, request: RateCalculationRequest) -> RateCalculationResponse:
    try:
        return await RateCalculatorService(db).calculate(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Internal rate calculation error", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal calculation failure.",
        ) from exc
