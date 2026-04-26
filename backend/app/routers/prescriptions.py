from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.services.ner import extract_entities, DrugEntity
from app.services.rag import rag_service
from app.services.interactions import check_interactions
from app.services.ocr import ocr_service
from app.workers.tasks import process_prescription
from celery.result import AsyncResult
from app.services.pdf_export import generate_pdf
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
    interactions = await check_interactions(drug_names)

    return PrescriptionResponse(
        entities_found=len(entities),
        drugs=[DrugExplanation(**exp) for exp in explanations],
        interactions=[InteractionAlert(**i) for i in interactions],
        disclaimer=DISCLAIMER,
    )

@router.post("/image")
async def explain_image_prescription(
    file: UploadFile = File(...),
    handwritten: bool = Form(False),
):
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WebP, or PDF accepted.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File must be under 10MB.")

    ocr_result = ocr_service.process_image(image_bytes, force_handwritten=handwritten)

    if ocr_result.confidence < 0.4 and not ocr_result.is_handwritten: # Handwrittten OCR conf is 0.7 by default in our mvp
        raise HTTPException(
            status_code=422,
            detail=f"Image quality too low for reliable text extraction "
                   f"(confidence: {ocr_result.confidence:.0%}). "
                   f"Please upload a clearer image."
        )

    # Reuse the text pipeline from here
    entities = extract_entities(ocr_result.text)
    if not entities:
        raise HTTPException(status_code=422, detail="No drug names found in the prescription image.")

    explanations = [rag_service.explain(e) for e in entities]
    interactions = await check_interactions([e.name for e in entities])

    return PrescriptionResponse(
        entities_found=len(entities),
        drugs=[DrugExplanation(**exp) for exp in explanations],
        interactions=[InteractionAlert(**i) for i in interactions],
        disclaimer=DISCLAIMER,
    )

@router.post("/submit")
async def submit_prescription(body: TextPrescriptionRequest):
    """Submit a job and return a job ID immediately."""
    task = process_prescription.delay(body.text, include_audio=False)
    return {"job_id": task.id, "status": "queued"}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll job status and retrieve result when complete."""
    result = AsyncResult(job_id)
    if result.state == "PENDING":
        return {"job_id": job_id, "status": "queued", "step": None}
    if result.state in ("EXTRACTING", "EXPLAINING", "INTERACTIONS", "TTS"):
        return {"job_id": job_id, "status": "processing", "step": result.info.get("step") if result.info else None}
    if result.state == "SUCCESS":
        return {"job_id": job_id, "status": "complete", "result": result.result}
    if result.state == "FAILURE":
        return {"job_id": job_id, "status": "failed", "error": str(result.result)}
    return {"job_id": job_id, "status": result.state}

@router.get("/jobs/{job_id}/pdf")
async def download_pdf(job_id: str):
    result = AsyncResult(job_id)
    if result.state != "SUCCESS":
        raise HTTPException(status_code=404, detail="Job not complete or not found.")
    pdf_bytes = generate_pdf(result.result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prescription_{job_id[:8]}.pdf"},
    )
