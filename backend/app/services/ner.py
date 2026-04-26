"""
NER service — extracts DRUG, DOSAGE, FREQUENCY entities from prescription text.
MVP uses spaCy + rule-based patterns. Phase 2 upgrades to BioBERT/scispaCy.
"""
import spacy
import re
from dataclasses import dataclass, field

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    # Fallback if model not found during implementation
    nlp = None

# --- Latin abbreviation expansion ---
ABBREV_MAP = {
    r"\bod\b": "once daily",
    r"\bbd\b": "twice daily",
    r"\btds\b": "three times daily",
    r"\bqds\b": "four times daily",
    r"\bprn\b": "as needed",
    r"\bpc\b": "after meals",
    r"\bac\b": "before meals",
    r"\bhs\b": "at bedtime",
    r"\bstat\b": "immediately",
    r"\bpo\b": "by mouth",
    r"\bsc\b": "subcutaneous",
    r"\bim\b": "intramuscular",
    r"\biv\b": "intravenous",
    r"\btab\b": "tablet",
    r"\bcap\b": "capsule",
    r"\btabs\b": "tablets",
    r"\bcaps\b": "capsules",
}

DOSAGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|ml|g|iu|units?|%)\b",
    re.IGNORECASE
)

FREQUENCY_PATTERN = re.compile(
    r"\b(once|twice|three times|four times|every \d+ hours?|"
    r"daily|weekly|monthly|at bedtime|as needed|with meals?)\b",
    re.IGNORECASE
)

# Common drug name signals (MVP heuristic — Phase 2 uses BioBERT)
KNOWN_DRUGS = {
    "amoxicillin", "metformin", "atorvastatin", "lisinopril",
    "omeprazole", "paracetamol", "ibuprofen", "amlodipine",
    "metoprolol", "sertraline", "levothyroxine", "pantoprazole",
    "aspirin", "warfarin", "digoxin", "ramipril", "simvastatin",
    "fluoxetine", "ciprofloxacin", "doxycycline", "prednisone",
    "salbutamol", "ventolin", "insulin", "glipizide", "clopidogrel",
}

@dataclass
class DrugEntity:
    name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    raw_text: str = ""

def expand_abbreviations(text: str) -> str:
    for pattern, expansion in ABBREV_MAP.items():
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
    return text

def extract_entities(raw_text: str) -> list[DrugEntity]:
    """
    Main extraction function.
    Returns a list of DrugEntity objects parsed from prescription text.
    """
    text = expand_abbreviations(raw_text)
    entities: list[DrugEntity] = []

    # Sentence-level parsing: each line or sentence may be one drug entry
    lines = [l.strip() for l in re.split(r"[\n;]", text) if l.strip()]

    for line in lines:
        drug = _find_drug(line)
        if not drug:
            continue
        dosage = _find_dosage(line)
        frequency = _find_frequency(line)
        entities.append(DrugEntity(
            name=drug,
            dosage=dosage,
            frequency=frequency,
            raw_text=line,
        ))

    # Deduplicate by drug name
    seen = set()
    unique = []
    for e in entities:
        if e.name not in seen:
            seen.add(e.name)
            unique.append(e)

    return unique

def _find_drug(text: str) -> str | None:
    lower = text.lower()
    for drug in KNOWN_DRUGS:
        if drug in lower:
            # Return properly-cased version
            idx = lower.index(drug)
            return text[idx:idx+len(drug)].strip()
    return None

def _find_dosage(text: str) -> str | None:
    match = DOSAGE_PATTERN.search(text)
    return match.group(0) if match else None

def _find_frequency(text: str) -> str | None:
    match = FREQUENCY_PATTERN.search(text)
    return match.group(0) if match else None
