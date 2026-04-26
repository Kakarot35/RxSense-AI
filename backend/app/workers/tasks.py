from app.workers.celery_app import celery_app
from app.services.ner import extract_entities
from app.services.rag import rag_service
from app.services.interactions import check_interactions
from app.services.tts import tts_service
import asyncio

@celery_app.task(bind=True, max_retries=2)
def process_prescription(self, text: str, include_audio: bool = False) -> dict:
    """
    Full async pipeline task. Called by the API; result polled via job ID.
    """
    try:
        self.update_state(state="EXTRACTING", meta={"step": "Identifying medications..."})
        entities = extract_entities(text)

        self.update_state(state="EXPLAINING", meta={"step": "Generating explanations..."})
        explanations = [rag_service.explain(e) for e in entities]

        self.update_state(state="INTERACTIONS", meta={"step": "Checking interactions..."})
        # Run async function in sync Celery context
        interactions = asyncio.run(check_interactions([e.name for e in entities]))

        audio_url = None
        if include_audio:
            self.update_state(state="TTS", meta={"step": "Generating audio..."})
            summary_text = " ".join(e["explanation"] for e in explanations)
            audio_url = tts_service.synthesise(summary_text)

        return {
            "status": "complete",
            "entities_found": len(entities),
            "drugs": explanations,
            "interactions": interactions,
            "audio_url": audio_url,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
