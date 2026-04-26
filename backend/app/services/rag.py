"""
RAG pipeline — retrieves drug knowledge and generates patient-friendly explanations.
"""
import chromadb
from chromadb.utils import embedding_functions
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.services.ner import DrugEntity
import structlog

log = structlog.get_logger()

CONFIDENCE_THRESHOLD = 0.65  # cosine similarity floor (MVP is permissive)
TOP_K = 5

SYSTEM_PROMPT = """You are a patient-friendly medical assistant.
Your ONLY job is to explain the prescription information below to a patient in plain, simple English.

STRICT RULES:
1. Use ONLY the information provided in the CONTEXT below. Never add facts from your own memory.
2. Write in second person: "You should take...", "This medicine helps with..."
3. Always separate: (a) what the drug is for, (b) how to take it, (c) common side effects, (d) warnings.
4. If the context does not contain enough information, say exactly: "I don't have enough verified information about this. Please consult your pharmacist."
5. End every explanation with: "Always follow your doctor's specific instructions."
6. Do NOT mention brand names unless they appear in the context.
7. Keep the explanation under 200 words per drug."""

USER_PROMPT = """PATIENT PRESCRIPTION:
Drug: {drug_name}
Dosage: {dosage}
Frequency: {frequency}

VERIFIED CONTEXT FROM MEDICAL KNOWLEDGE BASE:
{context}

---
Write a clear, patient-friendly explanation for this prescription entry."""

class RAGService:
    def __init__(self):
        self._llm = None
        self._chain = None

    def _init(self):
        """Lazy init — don't load models at import time."""
        if self._llm is not None:
            return

        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",   # free tier, fast
            temperature=0,
            google_api_key=settings.google_api_key,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human",  USER_PROMPT),
        ])
        self._chain = prompt | self._llm | StrOutputParser()

    def retrieve(self, drug_name: str, n: int = TOP_K) -> tuple[str, float]:
        """
        Query FAISS for the most relevant chunks for a drug.
        Returns (assembled_context, best_similarity_score).
        """
        from app.db.faiss_store import faiss_store
        self._init()

        results = faiss_store.search(drug_name, k=n, drug_filter=drug_name.lower())

        if not results:
            # Fallback: search without drug filter (broader)
            results = faiss_store.search(drug_name, k=n)

        if not results:
            return "", 0.0

        # Assemble context with source attribution
        context_parts = []
        best_score = max(r["score"] for r in results)
        
        for r in results:
            source = r["metadata"].get("source", "Unknown")
            context_parts.append(f"[Source: {source}]\n{r['text']}")

        context = "\n\n---\n\n".join(context_parts)
        log.info("rag.retrieved", drug=drug_name, chunks=len(results), best_score=round(best_score, 3))
        return context, best_score

    def explain(self, entity: DrugEntity) -> dict:
        """
        Full RAG pipeline for one drug entity.
        Returns explanation dict with content, confidence, and sources.
        """
        self._init()

        context, score = self.retrieve(entity.name)

        if score < CONFIDENCE_THRESHOLD:
            log.warn("rag.low_confidence", drug=entity.name, score=score)
            return {
                "drug": entity.name,
                "dosage": entity.dosage,
                "frequency": entity.frequency,
                "explanation": (
                    "I don't have enough verified information about this medication. "
                    "Please consult your pharmacist or prescribing doctor."
                ),
                "confidence": round(score, 3),
                "sources": [],
                "warning": "low_confidence",
            }

        explanation = self._chain.invoke({
            "drug_name": entity.name,
            "dosage": entity.dosage or "not specified",
            "frequency": entity.frequency or "not specified",
            "context": context,
        })

        return {
            "drug": entity.name,
            "dosage": entity.dosage,
            "frequency": entity.frequency,
            "explanation": explanation.strip(),
            "confidence": round(score, 3),
            "sources": ["MedlinePlus"],
            "warning": None,
        }

# Singleton — one ChromaDB connection for the process lifetime
rag_service = RAGService()
