from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.exc import SQLAlchemyError
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=1, le=9998)
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID is required")

    if (month is None) != (year is None):
        raise HTTPException(status_code=422, detail="Provide both month and year")

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    except (SQLAlchemyError, OSError) as e:
        raise HTTPException(
            status_code=503,
            detail="Revenue is temporarily unavailable"
        ) from e

    total_revenue = Decimal(revenue_data['total']).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": str(total_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count'],
        "month": month,
        "year": year
    }