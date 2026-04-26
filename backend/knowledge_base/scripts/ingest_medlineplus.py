"""
Fetches drug summaries from MedlinePlus and ingests into FAISS store.
Run once: python -m knowledge_base.scripts.ingest_medlineplus
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import requests
import xml.etree.ElementTree as ET
import re, time
from app.db.faiss_store import faiss_store

DRUGS = [
    "amoxicillin", "metformin", "atorvastatin", "lisinopril",
    "omeprazole", "paracetamol", "ibuprofen", "amlodipine",
    "metoprolol", "sertraline", "levothyroxine", "pantoprazole",
]

MEDLINEPLUS_URL = "https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={drug}+drug"

def fetch_drug_summary(drug: str) -> list[dict]:
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
            clean = re.sub(r"<[^>]+>", " ", content_el.text)
            clean = re.sub(r"\s+", " ", clean).strip()
            title = title_el.text if title_el is not None else drug
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
    all_docs, all_metas = [], []

    for drug in DRUGS:
        print(f"Fetching: {drug}")
        chunks = fetch_drug_summary(drug)
        for chunk in chunks:
            all_docs.append(chunk["text"])
            all_metas.append({k: v for k, v in chunk.items() if k != "text"})
        time.sleep(0.5)

    if all_docs:
        faiss_store.add(all_docs, all_metas)
        faiss_store.save()
        print(f"\nIngested {len(all_docs)} chunks for {len(DRUGS)} drugs.")
    else:
        print("No documents fetched.")

if __name__ == "__main__":
    main()
