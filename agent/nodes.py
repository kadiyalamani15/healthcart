"""
LangGraph node functions for the HealthCart agent pipeline.

Node order: profile_analyzer → constraint_extractor → product_recommender
           → compliance_validator → list_formatter

LiteLLM model routing:
  llama-3.1-8b-instant   → nodes 1, 2, 4  (structured extraction + binary judgment)
  llama-3.3-70b-versatile → node 3         (nuanced recommendation generation)
  Set GROQ_API_KEY in .env; LiteLLM routes automatically.

Langfuse tracing:
  Each node is decorated with @observe(), creating a child span inside the
  root trace established by run_agent() in graph.py.
"""

import json
import re
import os
import time
import litellm
from langfuse import observe

from agent.state import AgentState
from agent.prompts import (
    PROFILE_ANALYZER_PROMPT,
    CONSTRAINT_EXTRACTOR_PROMPT,
    PRODUCT_RECOMMENDER_PROMPT,
    COMPLIANCE_VALIDATOR_PROMPT,
)

# LiteLLM routes to Groq when GROQ_API_KEY is set
HAIKU = "groq/llama-3.1-8b-instant"     # structured extraction + binary judgment
SONNET = "groq/llama-3.3-70b-versatile" # nuanced recommendation generation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_llm(model: str, prompt: str, retries: int = 3) -> str:
    """Call LLM via LiteLLM with exponential backoff on rate-limit errors."""
    for attempt in range(retries):
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except litellm.RateLimitError as exc:
            if attempt == retries - 1:
                raise
            wait = 15 * (2 ** attempt)   # 15s, 30s, 60s
            time.sleep(wait)
    return ""


def _parse_json(content: str):
    """Parse JSON from an LLM response, handling markdown fences and trailing text."""
    # Extract only the first fenced code block if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()
    else:
        content = content.strip()

    # Determine whether the outermost structure is an array or object
    first_bracket = content.find("[")
    first_brace = content.find("{")
    if first_bracket == -1 and first_brace == -1:
        return json.loads(content)
    if first_bracket == -1 or (first_brace != -1 and first_brace < first_bracket):
        start_char, end_char = "{", "}"
        start = first_brace
    else:
        start_char, end_char = "[", "]"
        start = first_bracket

    # Walk to the matching closing bracket
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(content[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    return json.loads(content[start : i + 1])
    return json.loads(content)


# ---------------------------------------------------------------------------
# Node 1 — Profile Analyzer  (Haiku)
# ---------------------------------------------------------------------------

@observe(name="profile_analyzer")
def profile_analyzer_node(state: AgentState) -> dict:
    """Normalize and validate the raw health profile."""
    profile = state["health_profile"]

    prompt = PROFILE_ANALYZER_PROMPT.format(
        conditions=", ".join(profile.get("conditions", [])) or "None",
        restrictions=", ".join(profile.get("restrictions", [])) or "None",
        allergies=", ".join(profile.get("allergies", [])) or "None",
        goals=", ".join(profile.get("goals", [])) or "None",
    )

    try:
        content = _call_llm(HAIKU, prompt)
        normalized = _parse_json(content)
    except Exception as exc:
        # Graceful fallback: pass the raw profile through as-is
        normalized = {
            "conditions": profile.get("conditions", []),
            "restrictions": profile.get("restrictions", []),
            "allergies": profile.get("allergies", []),
            "severity_notes": [],
            "_parse_error": str(exc),
        }

    return {"normalized_profile": normalized}


# ---------------------------------------------------------------------------
# Node 2 — Constraint Extractor  (Haiku)
# ---------------------------------------------------------------------------

@observe(name="constraint_extractor")
def constraint_extractor_node(state: AgentState) -> dict:
    """Translate normalized health profile into specific food rules."""
    normalized = state.get("normalized_profile") or state["health_profile"]

    prompt = CONSTRAINT_EXTRACTOR_PROMPT.format(
        conditions=json.dumps(normalized.get("conditions", [])),
        restrictions=json.dumps(normalized.get("restrictions", [])),
        allergies=json.dumps(normalized.get("allergies", [])),
    )

    try:
        content = _call_llm(HAIKU, prompt)
        result = _parse_json(content)
        constraints = result.get("constraints", []) if isinstance(result, dict) else result
    except Exception as exc:
        constraints = [f"[extraction error: {exc}]"]

    if not isinstance(constraints, list):
        constraints = []

    return {"food_constraints": constraints}


# ---------------------------------------------------------------------------
# Node 3 — Product Recommender  (Sonnet)
# ---------------------------------------------------------------------------

@observe(name="product_recommender")
def product_recommender_node(state: AgentState) -> dict:
    """Generate grocery recommendations that satisfy the food constraints."""
    constraints = state.get("food_constraints", [])
    profile = state.get("health_profile", {})

    prompt = PRODUCT_RECOMMENDER_PROMPT.format(
        constraints=json.dumps(constraints, indent=2),
        goals=", ".join(profile.get("goals", [])) or "general health",
        household_size=profile.get("household_size", 2),
        budget=profile.get("budget", "flexible"),
    )

    try:
        content = _call_llm(SONNET, prompt)
        result = _parse_json(content)
        items = result.get("items", []) if isinstance(result, dict) else result
    except Exception as exc:
        items = [{"name": f"[generation error: {exc}]", "category": "Error",
                  "quantity": "—", "rationale": "—"}]

    if not isinstance(items, list):
        items = []

    return {"recommendations": items}


# ---------------------------------------------------------------------------
# Node 4 — Compliance Validator  (Haiku as judge)
# ---------------------------------------------------------------------------

@observe(name="compliance_validator")
def compliance_validator_node(state: AgentState) -> dict:
    """Score all recommendations in a single batch LLM call."""
    recommendations = state.get("recommendations", [])
    constraints = state.get("food_constraints", [])

    if not recommendations:
        return {"validated_list": [], "compliance_rate": 0.0}

    items_for_prompt = [
        {"name": item.get("name", ""), "rationale": item.get("rationale", "")}
        for item in recommendations
    ]

    prompt = COMPLIANCE_VALIDATOR_PROMPT.format(
        constraints=json.dumps(constraints, indent=2),
        items_json=json.dumps(items_for_prompt, indent=2),
    )

    try:
        content = _call_llm(HAIKU, prompt)
        judgments = _parse_json(content)
        if not isinstance(judgments, list):
            raise ValueError("Expected a JSON array from validator")

        # Map results back by position (same order guaranteed by prompt)
        validated = []
        for item, judgment in zip(recommendations, judgments):
            validated.append({
                **item,
                "passed": bool(judgment.get("compliant", True)),
                "compliance_notes": judgment.get("reason", ""),
                "constraint_violated": judgment.get("constraint_violated"),
            })

        # If LLM returned fewer items than expected, mark the rest as uncertain
        for item in recommendations[len(validated):]:
            validated.append({**item, "passed": None,
                               "compliance_notes": "Not evaluated", "constraint_violated": None})

    except Exception as exc:
        validated = [
            {**item, "passed": None,
             "compliance_notes": f"Validation error: {exc}", "constraint_violated": None}
            for item in recommendations
        ]

    passed_count = sum(1 for i in validated if i.get("passed") is True)
    rate = passed_count / len(validated) if validated else 0.0

    return {"validated_list": validated, "compliance_rate": rate}


# ---------------------------------------------------------------------------
# Node 5 — List Formatter  (pure Python, no LLM)
# ---------------------------------------------------------------------------

def list_formatter_node(state: AgentState) -> dict:
    """Group by category, sort passed items first, build summary."""
    validated = state.get("validated_list", [])
    rate = state.get("compliance_rate", 0.0)

    # Group by category
    by_category: dict = {}
    for item in validated:
        cat = item.get("category", "Other")
        by_category.setdefault(cat, []).append(item)

    # Within each category: passed first, then uncertain, then failed
    def sort_key(item):
        passed = item.get("passed")
        if passed is True:
            return 0
        if passed is None:
            return 1
        return 2

    shopping_list = []
    for cat in sorted(by_category.keys()):
        items = sorted(by_category[cat], key=sort_key)
        shopping_list.extend(items)

    total = len(validated)
    passed = sum(1 for i in validated if i.get("passed") is True)
    summary = (
        f"{total} items · {passed} passed compliance validation "
        f"({rate:.0%} compliance rate)"
    )

    return {"shopping_list": shopping_list, "summary": summary}
