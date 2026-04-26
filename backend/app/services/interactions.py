import httpx, json, hashlib
from redis import Redis
from app.core.config import settings
from app.services.interactions_rules import KNOWN_INTERACTIONS  # keep Phase 1 rules as fallback
import structlog

log = structlog.get_logger()

CACHE_TTL = 60 * 60 * 24   # 24 hours — interaction data doesn't change daily

_redis = Redis.from_url(settings.redis_url, decode_responses=True)

def _cache_key(drug_a: str, drug_b: str) -> str:
    pair = "-".join(sorted([drug_a.lower(), drug_b.lower()]))
    return f"interaction:{hashlib.md5(pair.encode()).hexdigest()}"

async def _fetch_drugbank(drug_a: str, drug_b: str) -> list[dict]:
    """Call DrugBank API for a specific drug pair."""
    if not settings.drugbank_api_key:
        return []   # No key → fall through to rule-based

    cache_key = _cache_key(drug_a, drug_b)
    cached = _redis.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://api.drugbank.com/v1/drug_interactions",
                params={"drug_names": f"{drug_a},{drug_b}"},
                headers={"Authorization": f"Bearer {settings.drugbank_api_key}"},
            )
            r.raise_for_status()
            data = r.json().get("interactions", [])
    except (httpx.HTTPError, Exception) as e:
        log.warn("drugbank.api_error", error=str(e))
        return []

    _redis.setex(cache_key, CACHE_TTL, json.dumps(data))
    return data

async def check_interactions(drug_names: list[str]) -> list[dict]:
    """
    Check all drug pairs. Tries DrugBank API first, falls back to rule-based.
    Now async to support httpx calls.
    """
    alerts = []
    names_lower = [d.lower() for d in drug_names]

    for i, drug_a in enumerate(names_lower):
        for drug_b in names_lower[i+1:]:
            # Try API
            api_results = await _fetch_drugbank(drug_a, drug_b)
            if api_results:
                for item in api_results:
                    alerts.append({
                        "drugs": [drug_a, drug_b],
                        "severity": item.get("severity", "Unknown"),
                        "description": item.get("description", ""),
                        "source": "DrugBank",
                    })
                continue

            # Fallback: rule-based table
            key = frozenset({drug_a, drug_b})
            if key in KNOWN_INTERACTIONS:
                rule = KNOWN_INTERACTIONS[key]
                alerts.append({
                    "drugs": [drug_a, drug_b],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "source": "rule-based fallback",
                })

    severity_order = {"Major": 0, "Moderate": 1, "Minor": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))
    return alerts
