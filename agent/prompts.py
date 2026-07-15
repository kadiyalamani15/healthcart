PROFILE_ANALYZER_PROMPT = """\
Analyze and normalize this health profile. Return valid JSON only — no explanation, no markdown.

Input:
- Conditions: {conditions}
- Dietary restrictions: {restrictions}
- Allergies: {allergies}
- Health goals: {goals}

Return exactly this JSON structure:
{{
  "conditions": ["list of standardized medical condition names"],
  "restrictions": ["list of dietary restrictions"],
  "allergies": ["list of allergens to avoid completely"],
  "severity_notes": ["any critical safety flags, e.g. 'Nut allergy — anaphylaxis risk'"]
}}

Return ONLY valid JSON."""


CONSTRAINT_EXTRACTOR_PROMPT = """\
Translate these health conditions and restrictions into specific, actionable food rules.

Conditions: {conditions}
Dietary restrictions: {restrictions}
Allergies: {allergies}

Return exactly this JSON structure:
{{
  "constraints": [
    "rule 1 — e.g. 'Avoid foods with glycemic index above 55'",
    "rule 2 — e.g. 'Limit sodium to under 1500mg per day'",
    "rule 3 — e.g. 'Exclude all gluten-containing grains: wheat, barley, rye, spelt'",
    "rule 4 — e.g. 'Avoid all peanut and peanut-derived products (allergy risk)'"
  ]
}}

Be specific and actionable. Cover both avoid and prefer rules.
Return ONLY valid JSON — no markdown, no explanation."""


PRODUCT_RECOMMENDER_PROMPT = """\
Generate a weekly grocery shopping list for a household following these dietary constraints.

Constraints:
{constraints}

Context:
- Health goals: {goals}
- Household size: {household_size} people
- Weekly budget: {budget}

Return exactly this JSON structure:
{{
  "items": [
    {{
      "name": "Spinach",
      "category": "Produce",
      "quantity": "1 large bag (5 oz)",
      "rationale": "Low-GI leafy green rich in magnesium, supports blood sugar regulation"
    }}
  ]
}}

Categories must be one of: Produce, Protein, Grains, Dairy/Alternatives, Pantry, Beverages, Frozen

Rules:
- Generate 15–20 items across at least 4 categories
- Every item must directly satisfy at least one constraint
- Quantities should reflect household size and weekly needs
- Rationale must explicitly connect the item to a health constraint or goal

Return ONLY valid JSON — no markdown, no explanation."""


COMPLIANCE_VALIDATOR_PROMPT = """\
You are a dietary compliance checker. Evaluate each grocery item against the constraints and allergies below.

Constraints:
{constraints}

Allergies (zero-tolerance — the user cannot safely consume these under any circumstances):
{allergies}

Items to evaluate:
{items_json}

Evaluation rules:
- Each item may include "usda_nutrients_per_100g" — real government-verified nutrient values from USDA FoodData Central. When present, use those actual numbers to check numeric thresholds (sodium, potassium, phosphorus, sugar, saturated fat) instead of your general knowledge of what the food "usually" contains. When absent (null), the item is ungrounded — use your best general knowledge, but treat numeric-threshold judgments on ungrounded items as less certain.
- Daily-total constraints (e.g. "sodium under 1500mg/day") mean: is this item LOW in that nutrient, not whether the item alone exceeds the daily limit.
- General constraints (non-allergen): mark an item non-compliant ONLY if it directly contradicts a constraint (e.g. high-GI food for a diabetic, wheat product for celiac). When uncertain, mark compliant: true — don't over-flag borderline items.
- Allergies are different and stricter: if there is ANY reasonable chance an item contains, was made with, or carries cross-contact risk with a listed allergen, mark compliant: false. When uncertain about an allergen specifically, default to non-compliant — this is a safety judgment, not a dietary preference, and a false "compliant" here is far worse than a false "non-compliant".
- Set "allergen_relevant": true if this item was evaluated against any listed allergy (i.e. it is a plausible source of one of the allergens above), regardless of the compliance verdict you gave it. Otherwise false.

Return a JSON array — one object per item, in the SAME ORDER as the input, and echo the exact "name" from the input so results can be matched reliably even if order isn't preserved:
[
  {{"name": "item name", "compliant": true, "reason": "one sentence", "constraint_violated": null, "allergen_relevant": false}},
  ...
]

Return ONLY valid JSON — no markdown, no explanation."""
