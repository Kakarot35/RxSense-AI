import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

SAMPLE = "Amoxicillin 500mg twice daily for 7 days"

@pytest.mark.asyncio
async def test_text_endpoint_returns_explanation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/prescriptions/text", json={"text": SAMPLE})
    assert r.status_code == 200
    data = r.json()
    assert data["entities_found"] >= 1
    assert data["drugs"][0]["drug"].lower() == "amoxicillin"
    assert len(data["drugs"][0]["explanation"]) > 10 # Allow short response for stub/low confidence

@pytest.mark.asyncio
async def test_no_drugs_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/prescriptions/text", json={"text": "take it easy today"})
    assert r.status_code == 422

@pytest.mark.asyncio
async def test_interaction_detection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/prescriptions/text",
                         json={"text": "Warfarin 5mg once daily\nAspirin 75mg once daily"})
    data = r.json()
    assert any(a["severity"] == "Major" for a in data["interactions"])
