import json
import logging
import redis.asyncio as redis
from redis.exceptions import RedisError
from typing import Dict, Any, Optional
from app.config import settings
from app.services.reservations import calculate_total_revenue

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    settings.redis_url,
    socket_connect_timeout=2,
    socket_timeout=2
)

async def get_revenue_summary(property_id: str, tenant_id: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    if not tenant_id:
        raise ValueError("Tenant ID is required")

    cache_key = "revenue:v2:" + json.dumps([tenant_id, property_id, year, month])

    # Try to get from cache
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except (RedisError, ValueError):
        logger.warning("Revenue cache unavailable; querying database")

    # Revenue calculation is delegated to the reservation service.
    result = await calculate_total_revenue(
        property_id,
        tenant_id,
        month=month,
        year=year
    )

    # Cache the result for 5 minutes
    try:
        await redis_client.setex(cache_key, 300, json.dumps(result))
    except RedisError:
        logger.warning("Revenue cache write failed")

    return result