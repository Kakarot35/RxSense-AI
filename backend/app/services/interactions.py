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

def check_interactions(drug_names: list[str]) -> list[dict]:
    """
    Check all pairs of drugs for known interactions.
    Returns list of interaction alerts, sorted by severity.
    """
    alerts = []
    names_lower = [d.lower() for d in drug_names]

    for i, drug_a in enumerate(names_lower):
        for drug_b in names_lower[i+1:]:
            key = frozenset({drug_a, drug_b})
            if key in KNOWN_INTERACTIONS:
                interaction = KNOWN_INTERACTIONS[key]
                alerts.append({
                    "drugs": [drug_a, drug_b],
                    "severity": interaction["severity"],
                    "description": interaction["description"],
                    "source": "MVP rule-based (upgrade to DrugBank in Phase 2)",
                })

    # Sort: Major first
    severity_order = {"Major": 0, "Moderate": 1, "Minor": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))
    return alerts
