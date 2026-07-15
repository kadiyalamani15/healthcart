from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    # Input — provided by caller
    health_profile: dict            # {conditions, restrictions, allergies, goals, household_size, budget}

    # After profile_analyzer
    normalized_profile: dict        # standardized conditions, safety flags

    # After constraint_extractor
    food_constraints: list          # ["Avoid foods with GI > 70", "Limit sodium < 1500mg/day", ...]

    # After product_recommender
    recommendations: list           # [{name, category, quantity, rationale}, ...]

    # After compliance_validator
    validated_list: list            # recommendations + compliance_score, compliance_notes, passed fields
    compliance_rate: float          # 0.0–1.0
    allergen_compliance_rate: Optional[float]  # 0.0–1.0, or None if no allergen-relevant items

    # After list_formatter
    shopping_list: list             # sorted by category, passed items first
    summary: str                    # "18 items · 15 passed compliance (83%)"

    # Set by run_agent() after the graph completes — the Langfuse trace ID
    # for this run, so a later human-feedback action can attach a score to
    # the exact run it's judging.
    trace_id: Optional[str]

    # Error passthrough
    error: Optional[str]
