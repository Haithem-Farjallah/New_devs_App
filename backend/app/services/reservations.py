from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from app.core.database_pool import db_pool

async def calculate_monthly_revenue(property_id: str, month: int, year: int, db_session=None, *, tenant_id: str) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    result = await calculate_total_revenue(
        property_id,
        tenant_id,
        month=month,
        year=year,
        db_session=db_session
    )
    return Decimal(result["total"])

async def calculate_total_revenue(property_id: str, tenant_id: str, month: Optional[int] = None, year: Optional[int] = None, db_session=None) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    if not tenant_id:
        raise ValueError("Tenant ID is required")

    if (month is None) != (year is None):
        raise ValueError("Provide both month and year")

    if month is not None:
        if not 1 <= month <= 12 or not 1 <= year <= 9998:
            raise ValueError("Invalid reporting month or year")

    try:
        # Initialize pool if needed
        await db_pool.initialize()

        if db_pool.session_factory:
            async with db_pool.get_session() as pooled_session:
                session = db_session if db_session is not None else pooled_session

                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text

                query = """
                    SELECT
                        r.property_id,
                        SUM(r.total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations r
                    JOIN properties p
                      ON p.id = r.property_id
                     AND p.tenant_id = r.tenant_id
                    WHERE r.property_id = :property_id
                      AND r.tenant_id = :tenant_id
                """

                params = {
                    "property_id": property_id,
                    "tenant_id": tenant_id
                }

                if month is not None:
                    query += """
                        AND EXTRACT(
                            MONTH FROM r.check_in_date AT TIME ZONE p.timezone
                        ) = :month
                        AND EXTRACT(
                            YEAR FROM r.check_in_date AT TIME ZONE p.timezone
                        ) = :year
                    """
                    params["month"] = month
                    params["year"] = year

                query += " GROUP BY r.property_id"

                result = await session.execute(text(query), params)
                row = result.fetchone()

                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD",
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")

    except Exception as e:
        print(f"Database error for {property_id} (tenant: {tenant_id}): {e}")
        raise