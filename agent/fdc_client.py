"""
USDA FoodData Central client — real nutrient data grounding.

Free, no-approval API (unlike Instacart's Developer Platform, which is
currently closed to new applications with a 30-40 day review even when
open — not usable for this project). FDC covers 380k+ foods with
government-verified nutrient values, public domain (CC0).

This does NOT provide retailer purchasability/pricing — only nutrition
facts. It grounds the compliance_validator's numeric-threshold judgments
(sodium, potassium, phosphorus, etc.) in real data instead of the model's
general knowledge of what a food "probably" contains.

Get a free key at https://fdc.nal.usda.gov/api-key-signup/ — falls back to
the shared "DEMO_KEY" (heavily rate-limited, fine for local testing only).
"""

import os
import requests

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Nutrient names as they appear in FDC's foodNutrients — mapped to the
# short keys the compliance_validator prompt actually needs, scoped to
# the conditions HealthCart supports (diabetes, CKD, hypertension, high
# cholesterol, celiac cross-reference via fiber/carbs).
NUTRIENT_MAP = {
    "Sodium, Na": "sodium_mg",
    "Potassium, K": "potassium_mg",
    "Phosphorus, P": "phosphorus_mg",
    "Sugars, total including NLEA": "sugars_g",
    "Fiber, total dietary": "fiber_g",
    "Total lipid (fat)": "fat_g",
    "Fatty acids, total saturated": "saturated_fat_g",
    "Carbohydrate, by difference": "carbs_g",
}


def _extract_nutrients(food: dict) -> dict:
    result = {}
    for n in food.get("foodNutrients", []):
        name = n.get("nutrientName")
        if name in NUTRIENT_MAP:
            result[NUTRIENT_MAP[name]] = n.get("value")
    return result


def search_food(query: str, timeout: float = 5.0) -> dict:
    """
    Look up a food item by name. Always returns a dict with a "status" key:

      "grounded"       -> real match, "fdc_description" + "nutrients" set
      "no_match"       -> USDA genuinely has no matching food
      "lookup_failed"  -> rate-limited / network / malformed response —
                           NOT the same as "no_match": the food may well
                           exist, we just couldn't check. Callers must not
                           conflate this with a genuine no-match, or the
                           grounding-rate metric silently misrepresents
                           API reliability as data coverage.

    Note: the shared "DEMO_KEY" fallback (used when USDA_FDC_API_KEY is
    unset) has an aggressive rate limit — expect "lookup_failed" after a
    handful of calls in one pipeline run. A free personal key from
    https://fdc.nal.usda.gov/api-key-signup/ removes this ceiling.
    """
    api_key = os.getenv("USDA_FDC_API_KEY", "DEMO_KEY")

    try:
        resp = requests.get(
            FDC_SEARCH_URL,
            params={
                "query": query,
                "api_key": api_key,
                "pageSize": 1,
                "dataType": ["Foundation", "SR Legacy"],  # skip branded/UPC noise
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        foods = resp.json().get("foods", [])
        if not foods:
            return {"status": "no_match"}

        food = foods[0]
        nutrients = _extract_nutrients(food)
        if not nutrients:
            return {"status": "no_match"}

        return {
            "status": "grounded",
            "fdc_description": food.get("description", query),
            "nutrients": nutrients,
        }

    except Exception as exc:
        # Network error, rate limit (429), malformed response — this is
        # an API-reliability failure, not evidence the food is missing
        # from USDA's database.
        return {"status": "lookup_failed", "error": str(exc)}
