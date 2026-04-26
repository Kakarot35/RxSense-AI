# RxSense AI 🩺

> AI-powered medical prescription explainer — decode any prescription into plain English, detect drug interactions, and listen to your medication instructions.

---

## What it does

Medical prescriptions are written in clinical shorthand most patients can't read. RxSense AI accepts a prescription image or text, extracts drug entities using NLP, retrieves verified medical information via a RAG pipeline, and generates a plain-language explanation covering dosage, side effects, and warnings — with audio playback and PDF export.

**WHO estimates 237 million medication errors occur annually.** RxSense AI is built to reduce that gap between clinical communication and patient understanding.

---

## Demo

```
Input:  "Amoxicillin 500mg twice daily for 7 days"

Output: {
  "drug": "amoxicillin",
  "dosage": "500mg",
  "frequency": "twice daily",
  "explanation": "You have been prescribed Amoxicillin, an antibiotic used to
                  treat bacterial infections. Take one 500mg capsule twice a day —
                  once in the morning and once in the evening — for 7 days.
                  Common side effects include nausea, diarrhoea, and skin rash.
                  Always complete the full course even if you feel better.
                  Always follow your doctor's specific instructions.",
  "confidence": 0.87,
  "sources": ["MedlinePlus"]
}
```

---

## System architecture

```
User Input (image / text)
        │
        ▼
┌─────────────────┐
│  L1 — Input     │  OpenCV preprocessing → Tesseract OCR (printed)
│                 │  TrOCR (handwritten) → raw text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L2 — Extract   │  spaCy NER → DRUG · DOSAGE · FREQUENCY · ROUTE
│                 │  Latin abbreviation expansion (b.d. → twice daily)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L3 — Retrieve  │  PubMedBERT embeddings → FAISS HNSW index
│                 │  Top-5 chunks from MedlinePlus / FDA knowledge base
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L4 — Generate  │  Gemini LLM (RAG-grounded, temp=0)
│                 │  Confidence threshold → safe fallback if score < 0.65
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L5 — Output    │  JSON · PDF (ReportLab) · MP3 (gTTS) · React UI
└─────────────────┘
```

---

## Features

| Feature | Status |
|---|---|
| Text prescription input | ✅ |
| Image prescription input (printed) | ✅ |
| Handwritten prescription (TrOCR) | ✅ |
| Medical NER extraction | ✅ |
| Latin abbreviation expansion | ✅ |
| RAG-grounded explanations | ✅ |
| Drug interaction detection | ✅ |
| Confidence thresholding + safe fallback | ✅ |
| Async job queue (Celery + Redis) | ✅ |
| Text-to-Speech audio output | ✅ |
| PDF summary report export | ✅ |
| React frontend with job polling | ✅ |
| BioBERT NER model | 🔜 Phase 3 |
| JWT authentication | 🔜 Phase 3 |
| EHR / FHIR integration | 🔜 Phase 3 |
| Multilingual support | 🔜 Phase 3 |

---

## Tech stack

**Backend**
- Python 3.11, FastAPI, Uvicorn
- LangChain — RAG orchestration
- FAISS — vector similarity search (HNSW index)
- Google Gemini API — LLM generation
- Celery + Redis — async task queue
- PostgreSQL — audit logging
- spaCy — NER and text processing
- sentence-transformers — embeddings (`all-MiniLM-L6-v2`)

**OCR**
- OpenCV — image preprocessing (deskew, binarise, denoise)
- Tesseract 5 — printed text OCR
- TrOCR (`microsoft/trocr-base-handwritten`) — handwritten OCR

**Output**
- gTTS — Text-to-Speech MP3 generation
- ReportLab — PDF report generation

**Frontend**
- React + TypeScript (Vite)
- Axios + custom polling hook

**Infrastructure**
- Docker + Docker Compose
- Redis (Celery broker + interaction cache)
- PostgreSQL 16

---

## Project structure

```
rxsense-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── core/
│   │   │   └── config.py            # pydantic-settings
│   │   ├── routers/
│   │   │   ├── prescriptions.py     # all prescription endpoints
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── ocr.py               # OCR pipeline
│   │   │   ├── ner.py               # NER extraction
│   │   │   ├── ner_legacy.py        # rule-based fallback
│   │   │   ├── rag.py               # RAG pipeline
│   │   │   ├── interactions.py      # drug interaction checker
│   │   │   ├── interactions_rules.py
│   │   │   ├── tts.py               # text-to-speech
│   │   │   └── pdf_export.py        # PDF generation
│   │   ├── db/
│   │   │   └── faiss_store.py       # FAISS vector store
│   │   └── workers/
│   │       ├── celery_app.py        # Celery configuration
│   │       └── tasks.py             # async tasks
│   ├── knowledge_base/
│   │   └── scripts/
│   │       └── ingest_medlineplus.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── hooks/
│   │       └── usePrescription.ts
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node 20+
- Docker Desktop
- Tesseract OCR 5.x ([Windows installer](https://github.com/UB-Mannheim/tesseract/wiki))
- Google Gemini API key ([free tier](https://aistudio.google.com/app/apikey))

### 1. Clone and configure

```bash
git clone https://github.com/your-username/rxsense-ai.git
cd rxsense-ai

cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY
```

### 2. Start infrastructure

```bash
docker compose up -d
# starts PostgreSQL + Redis
```

### 3. Install backend dependencies

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Ingest knowledge base

```bash
python -m knowledge_base.scripts.ingest_medlineplus
# Ingests ~47 chunks for 12 drugs into FAISS index
```

### 5. Start services

```bash
# Terminal 1 — Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --pool=solo

# Terminal 2 — API server
uvicorn app.main:app --reload --port 8000

# Terminal 3 — Frontend
cd ../frontend
npm install
npm run dev
```

### 6. Open the app

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Celery monitor: http://localhost:5555 (if Flower running)

---

## API reference

### Submit a prescription (async)
```http
POST /api/v1/prescriptions/submit
Content-Type: application/json

{ "text": "Amoxicillin 500mg twice daily for 7 days" }
```
```json
{ "job_id": "abc123", "status": "queued" }
```

### Poll job status
```http
GET /api/v1/prescriptions/jobs/{job_id}
```
```json
{
  "job_id": "abc123",
  "status": "complete",
  "result": {
    "entities_found": 1,
    "drugs": [...],
    "interactions": [],
    "disclaimer": "..."
  }
}
```

### Upload prescription image
```http
POST /api/v1/prescriptions/image
Content-Type: multipart/form-data

file: <image file>
handwritten: false
```

### Download PDF report
```http
GET /api/v1/prescriptions/jobs/{job_id}/pdf
```

### Health check
```http
GET /api/v1/health
```

---

## Environment variables

```env
# Required
GOOGLE_API_KEY=AIza...

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rxexplainer
REDIS_URL=redis://localhost:6379/0

# App
ENVIRONMENT=development
DEBUG=true
CHROMA_PERSIST_DIR=./chroma_db
LOG_LEVEL=INFO

# Optional
DRUGBANK_API_KEY=       # enables real interaction API (falls back to rules without it)
GOOGLE_TTS_KEY=         # enables WaveNet voices (falls back to gTTS without it)
```

---

## How RAG prevents hallucinations

Standard LLMs generate medical information from training data — which may be outdated, incomplete, or simply wrong for specific drug formulations. RxSense AI uses Retrieval-Augmented Generation:

1. Drug name is embedded and searched against the FAISS knowledge base
2. Top-5 most semantically similar passages are retrieved
3. Gemini is instructed to explain the drug using **only** the retrieved context
4. If cosine similarity score < 0.65, the system returns a safe fallback instead of generating

Every output is traceable to a source document. The model cannot fabricate information it wasn't given.

---

## Roadmap

- [ ] JWT authentication + per-user rate limiting
- [ ] Alembic database migrations + audit logging
- [ ] BioBERT / scispaCy NER model (removes drug name whitelist)
- [ ] DailyMed bulk ingestion (50,000+ drugs)
- [ ] Docker production deployment (Railway / Render)
- [ ] Prometheus + Grafana monitoring
- [ ] Multilingual NER + TTS
- [ ] EHR integration (HL7 FHIR)
- [ ] AR prescription overlay (mobile)

---

## Disclaimer

RxSense AI is a **patient education tool only**. It does not constitute medical advice, clinical decision support, or a substitute for pharmacist or physician consultation. Always follow your prescribing doctor's specific instructions.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built by Karan · 2026
