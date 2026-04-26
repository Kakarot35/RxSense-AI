"""
Drug interaction checker.
MVP: rule-based lookup table for the most critical interactions.
Phase 2: DrugBank API with Redis caching.
"""

# High-priority interaction pairs (drug_a, drug_b): severity, description
KNOWN_INTERACTIONS: dict[frozenset, dict] = {
    frozenset({"warfarin", "aspirin"}): {
        "severity": "Major",
        "description": "Combining warfarin and aspirin significantly increases bleeding risk.",
    },
    frozenset({"warfarin", "ibuprofen"}): {
        "severity": "Major",
        "description": "NSAIDs like ibuprofen can increase warfarin's blood-thinning effect.",
    },
    frozenset({"metformin", "alcohol"}): {
        "severity": "Moderate",
        "description": "Alcohol increases the risk of lactic acidosis with metformin.",
    },
    frozenset({"sertraline", "tramadol"}): {
        "severity": "Major",
        "description": "Risk of serotonin syndrome — potentially life-threatening.",
    },
    frozenset({"lisinopril", "potassium"}): {
        "severity": "Moderate",
        "description": "ACE inhibitors like lisinopril can raise potassium to dangerous levels.",
    },
    frozenset({"simvastatin", "amlodipine"}): {
        "severity": "Moderate",
        "description": "Amlodipine can increase simvastatin levels, raising muscle damage risk.",
    },
}
