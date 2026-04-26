"""
Fetches drug summaries from MedlinePlus XML feed and ingests into ChromaDB.
Run once: python -m knowledge_base.scripts.ingest_medlineplus
"""
import requests
import xml.etree.ElementTree as ET
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import hashlib, re, time

DRUGS = [
    "amoxicillin", "metformin", "atorvastatin", "lisinopril",
    "omeprazole", "paracetamol", "ibuprofen", "amlodipine",
    "metoprolol", "sertraline", "levothyroxine", "pantoprazole",
]

MEDLINEPLUS_URL = "https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={drug}+drug"

def fetch_drug_summary(drug: str) -> list[dict]:
    """Fetch and parse MedlinePlus health topic XML for a drug."""
    try:
        r = requests.get(MEDLINEPLUS_URL.format(drug=drug), timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        chunks = []
        for doc in root.findall(".//document"):
            content_el = doc.find("content[@name='FullSummary']")
            title_el   = doc.find("content[@name='title']")
            if content_el is None or not content_el.text:
                continue
            # Strip HTML tags
            clean = re.sub(r"<[^>]+>", " ", content_el.text)
            clean = re.sub(r"\s+", " ", clean).strip()
            title = title_el.text if title_el is not None else drug
            # Chunk into ~400-word pieces with 50-word overlap
            words = clean.split()
            for i in range(0, len(words), 350):
                chunk = " ".join(words[max(0, i-50):i+400])
                if len(chunk) < 100:
                    continue
                chunks.append({
                    "text": chunk,
                    "drug": drug.lower(),
                    "title": title,
                    "source": "MedlinePlus",
                    "section": "general",
                })
        return chunks
    except Exception as e:
        print(f"  [WARN] Failed to fetch {drug}: {e}")
        return []

def main():
    chroma = chromadb.PersistentClient(path="./chroma_db")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = chroma.get_or_create_collection(
        name="drug_knowledge",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    all_docs, all_ids, all_metas = [], [], []

    for drug in DRUGS:
        print(f"Fetching: {drug}")
        chunks = fetch_drug_summary(drug)
        for chunk in chunks:
            doc_id = hashlib.md5(chunk["text"].encode()).hexdigest()
            all_docs.append(chunk["text"])
            all_ids.append(doc_id)
            all_metas.append({k: v for k, v in chunk.items() if k != "text"})
        time.sleep(0.5)  # be polite to NLM servers

    if all_docs:
        collection.upsert(documents=all_docs, ids=all_ids, metadatas=all_metas)
        print(f"\nIngested {len(all_docs)} chunks for {len(DRUGS)} drugs.")
    else:
        print("No documents fetched — check network access.")

if __name__ == "__main__":
    main()
