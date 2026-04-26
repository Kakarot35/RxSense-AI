from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.ner import extract_entities, DrugEntity
from app.services.rag import rag_service
from app.services.interactions import check_interactions
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

class TextPrescriptionRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=5000,
                      example="Amoxicillin 500mg twice daily for 7 days\nMetformin 850mg once daily with meals")

class DrugExplanation(BaseModel):
    drug: str
    dosage: str | None
    frequency: str | None
    explanation: str
    confidence: float
    sources: list[str]
    warning: str | None

class InteractionAlert(BaseModel):
    drugs: list[str]
    severity: str
    description: str
    source: str

class PrescriptionResponse(BaseModel):
    entities_found: int
    drugs: list[DrugExplanation]
    interactions: list[InteractionAlert]
    disclaimer: str

DISCLAIMER = (
    "This explanation is for patient education only and does not replace "
    "advice from your doctor or pharmacist. Always follow your prescriber's instructions."
)

@router.post("/text", response_model=PrescriptionResponse, status_code=status.HTTP_200_OK)
async def explain_text_prescription(body: TextPrescriptionRequest):
    log.info("prescription.received", text_length=len(body.text))

    # Step 1: Extract entities
    entities: list[DrugEntity] = extract_entities(body.text)
    if not entities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No recognisable drug names found in the prescription text. "
                   "Please check the text and try again.",
        )

    log.info("ner.extracted", count=len(entities), drugs=[e.name for e in entities])

    # Step 2: RAG explain each drug
    explanations = [rag_service.explain(entity) for entity in entities]

    # Step 3: Check interactions
    drug_names = [e.name for e in entities]
    interactions = check_interactions(drug_names)

    return PrescriptionResponse(
        entities_found=len(entities),
        drugs=[DrugExplanation(**exp) for exp in explanations],
        interactions=[InteractionAlert(**i) for i in interactions],
        disclaimer=DISCLAIMER,
    )
