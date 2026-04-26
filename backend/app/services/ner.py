import spacy
from app.services.ner_legacy import extract_entities as extract_entities_legacy
from app.services.ner_legacy import DrugEntity, expand_abbreviations, _find_dosage, _find_frequency

# Try loading the medical model; fall back to rule-based if not installed
try:
    nlp_medical = spacy.load("en_ner_bc5cdr_md")
    BIOBERT_AVAILABLE = True
except OSError:
    BIOBERT_AVAILABLE = False
    import structlog
    structlog.get_logger().warn("ner.biobert_unavailable", fallback="rule-based")

def extract_entities(raw_text: str) -> list[DrugEntity]:
    """
    Uses BioBERT-based scispaCy NER if available, otherwise falls back
    to the rule-based extractor from Phase 1.
    """
    if not BIOBERT_AVAILABLE:
        return extract_entities_legacy(raw_text)

    text = expand_abbreviations(raw_text)
    doc = nlp_medical(text)

    # BC5CDR model labels: CHEMICAL (drugs), DISEASE
    drug_spans = [ent for ent in doc.ents if ent.label_ == "CHEMICAL"]

    entities = []
    for span in drug_spans:
        # Get the sentence containing this span for dosage/frequency context
        sent_text = span.sent.text
        entities.append(DrugEntity(
            name=span.text.lower(),
            dosage=_find_dosage(sent_text),
            frequency=_find_frequency(sent_text),
            raw_text=sent_text,
        ))

    # Deduplicate
    seen = set()
    unique = []
    for e in entities:
        if e.name not in seen:
            seen.add(e.name)
            unique.append(e)
    return unique
