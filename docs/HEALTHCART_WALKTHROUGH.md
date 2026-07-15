# HealthCart — A Walkthrough

*What this is, how it's built, and what I found wrong with it by actually checking.*

---

## What is this project about

129 million Americans manage a chronic condition where diet is a primary lever — Type 2 Diabetes, Celiac Disease, Chronic Kidney Disease, Hypertension (CDC, cited in Rockefeller Foundation food-is-medicine research, 2026). The professional who's supposed to translate a diagnosis into a shopping list — a registered dietitian (RDN) — costs $70–$300 out of pocket per session, and Medicare's Medical Nutrition Therapy benefit only covers diabetes, chronic kidney disease, and post-transplant patients. Celiac, IBS, PCOS, GERD, and heart disease generally aren't reimbursed. Most people are on their own.

Grocery apps answer this with static category tags — vegan, gluten-free, keto — applied to products, not conditions applied to a person. And when people turn to general-purpose AI to close the gap instead, it fails in ways that are dangerous, not just wrong: Food Republic found 30–50% of AI-generated recipes contain at least one materially wrong quantity (Feb 2026), and in a documented 2026 incident, Google Gemini recommended a garlic-in-oil storage method that created textbook conditions for *Clostridium botulinum* growth.

HealthCart is my answer to a narrower question than "how do we personalize grocery shopping": **how do you make an AI-derived food recommendation verifiable before someone acts on it, without reintroducing the $70–300 cost barrier the AI is supposed to be routing around?** That's an architecture question, not a filter question — which is why the interesting part of this project isn't the shopping list, it's the second model call that checks the first one's work, and everything that turned out to be wrong with *that*.

---

## The agentic system

A 6-node LangGraph pipeline. Health profile in, validated shopping list out.

```
Health Profile
      │
      ▼
[1] profile_analyzer (Llama 3.1 8B via Groq) ─── normalizes conditions/restrictions/allergies into structured JSON
      │
      ▼
[2] constraint_extractor (8B) ─── translates conditions into specific rules
      │                             e.g. "avoid glycemic index > 55" for Type 2 Diabetes
      ▼
[3] product_recommender (Llama 3.3 70B) ─── generates 15–20 grocery items satisfying the constraints
      │
      ▼
[3.5] nutrient_grounding (USDA FoodData Central, no LLM) ─── looks up each item against
      │                    real government-verified nutrient data where a match exists
      ▼
[4] compliance_validator (8B, judge) ─── scores every item in one batched call,
      │                    using real USDA nutrients when available
      ▼
[5] list_formatter (pure Python) ─── groups by category, sorts passed items first
      │
      ▼
Langfuse trace tree — one root span per run, one child span per node
```

Three infrastructure pieces do the plumbing, none of them do the reasoning:

- **LangGraph** is the orchestration layer — a typed shared state object (`AgentState`) passed between nodes, each node reading what the previous one wrote. Right now the graph is a straight line, but the reason to model it as a graph rather than five sequential function calls is that adding a conditional edge later (e.g., routing uncertain judgments to a human-review node) doesn't require restructuring anything else.
- **LiteLLM** is the model gateway — `litellm.completion(model="groq/llama-3.1-8b-instant", ...)` works identically if you swap the model string for any of 100+ other providers. This is what makes `HAIKU`/`SONNET` just constants in `agent/nodes.py` rather than provider-specific SDK calls.
- **Langfuse** is observability — every node is wrapped in `@observe()`, which builds a trace tree you can actually open and inspect: what did node 3 generate, what did node 4 say about it, how long did each call take. It also accepts custom scores, which is how the eval harness and the human-feedback buttons both attach numbers to a specific run after the fact.

The reasoning — the actual "is this safe" judgment — happens entirely inside the two LLM calls (constraint extraction and compliance validation). Everything else exists to make those two calls checkable instead of trusted on faith.

---

## Evaluation — and what checking my own work actually turned up

There's a 20-case eval harness (`eval/runner.py` + `eval/test_cases.json`) covering single conditions, combined conditions, and one safety-critical case — Peanut + Tree Nut Allergy, `expected_min_compliance: 0.85`, elevated above the 0.70–0.80 range everywhere else because a false negative there isn't an annoyance, it's a safety failure.

Building and rereading that harness turned up three real bugs, in the order I found them.

**1. The judge's own instructions told it to be lenient, in the one place that mattered least.**

```
- Mark an item non-compliant ONLY if it directly contradicts a constraint
- When in doubt, mark compliant: true.
```

I wrote that — a reasonable default for most constraints (don't flag spinach as non-compliant for no reason), and the wrong default for the allergy case specifically. An eval harness that reports 90% average compliance tells you almost nothing if the judge's own prompt biases it toward "compliant" on exactly the failure class that matters most; the aggregate number looks healthy and hides the thing it exists to catch.

*Fix:* split the default. General constraints stay lenient. Allergen constraints flip to "when uncertain, non-compliant," and the judge now tags each item `allergen_relevant: true/false` so that population gets measured on its own, not blended into one number.

**2. Judgments were matched back to items by list position, not identity.**

```python
for item, judgment in zip(recommendations, judgments):
    validated.append({**item, "passed": bool(judgment.get("compliant", True)), ...})
```

An 8B-tier model has no structural guarantee it preserves input order — only a prompt instruction saying so. A dropped or reordered judgment would silently attach the wrong verdict to the wrong food, with no error.

*Fix:* the judge now echoes each item's `name`; matching happens by name, with position as a flagged fallback, not a silent default.

**3. The eval harness's own Langfuse logging had been broken since the first commit — found by testing, not reading.**

Building the human-feedback feature meant I needed to know the *actual* installed SDK's API, not the one implied by the README. So I checked:

```python
>>> from langfuse import Langfuse
>>> hasattr(Langfuse(public_key='x', secret_key='y'), 'trace')
False
```

`eval/runner.py` had been calling `langfuse.trace(...)` the whole time — a method that doesn't exist on the installed v3 SDK, which replaced it with `start_as_current_span()` + `score_current_trace()`. Every eval run's aggregate scores had been silently failing, caught by a broad `except Exception` that nobody was reading closely enough to notice. The harness's own claim about itself ("every run logs scores to Langfuse") was false, and nothing in the system would have surfaced that without deliberately going and checking.

---

## The part I got wrong, and how I found out

Wiring in USDA FoodData Central grounding (after confirming Instacart's Developer Platform is currently closed to new applications — 30–40 days to approve even when open, not something to build a portfolio project's architecture around) produced a strange result on first run: 0% allergen compliance, and only 5 of 16 items grounded against USDA at all.

My first explanation, stated with more confidence than I'd earned: *"USDA's plain scientific food names don't match the model's marketing-style item names like 'Wild-Caught Salmon.'"* Plausible. Also wrong — and the tell was that **Spinach, Lentils, and Quinoa** also failed to ground, and there's no naming-mismatch story that explains that.

So I tested it directly instead of writing the guess into the docs:

```python
>>> requests.get(FDC_SEARCH_URL, params={"query": "Spinach", "api_key": "DEMO_KEY", ...})
{"error": {"code": "OVER_RATE_LIMIT", "message": "You have exceeded your rate limit..."}}
```

The real cause: the free shared `DEMO_KEY` rate-limits hard, and one 16-item list makes 16 sequential USDA calls. Most of the run was hitting HTTP 429, not "no match." The code's `except Exception: return None` had been collapsing two very different situations — "USDA genuinely has nothing" and "we couldn't check" — into one signal.

*Fix:* `search_food()` now returns a real status — `"grounded"`, `"no_match"`, or `"lookup_failed"` — and the UI shows three icons instead of two (🏪 / ✨ / 🔌). Collapsing those into one "ungrounded" state would have been the exact same failure pattern this whole project is arguing against: a system reporting confidence it hasn't earned.

---

## What's still open

There's a thumbs up/down on every item now, logged via `create_score(trace_id=...)` against the exact trace that produced it. To be precise about what that does and doesn't do: **it records a human's agreement with the judge's verdict. It does not make the model learn.** Nothing in this stack — Langfuse included — retrains anything automatically. Turning accumulated labels into a better judge is a separate, unbuilt step (few-feedback prompt examples, or eventually fine-tuning on real volume), and claiming otherwise would be exactly the kind of unverified confidence the rest of this write-up is about catching.

The single largest gap, unchanged by any of this session's fixes: there's still no human-verified ground truth for whether the judge is actually right. Everything the eval harness reports is the judge's opinion of itself, now measured more honestly — split by allergen class, grounded against real nutrients where possible, matched by name instead of position — but still unvalidated against a real clinical baseline.

That's the next thing worth building, not another feature.
