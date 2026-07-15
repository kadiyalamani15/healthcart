# Build Log: Finding (and Getting Wrong, Then Right) Three Bugs in HealthCart

*A chronological account of one debugging session, not a framework document. Every code snippet below is real — pulled from the actual diffs — and the wrong turn in the middle is left in on purpose.*

---

## Starting point

HealthCart already worked: a 5-node LangGraph pipeline, 20 eval cases, ~90% average compliance. The obvious next move for a portfolio piece is to write up what's there and call it done. Instead I went looking for what was wrong with it — on the theory that a system that validates AI output should itself be checked, not taken on faith.

## Bug 1 — the judge was told to be lenient, on purpose, in the wrong place

Rereading `agent/prompts.py`, the compliance validator's own instructions said:

```
- Mark an item non-compliant ONLY if it directly contradicts a constraint
- When in doubt, mark compliant: true.
```

I wrote that. The reasoning at the time was sound for most of the system — you don't want the judge flagging spinach as non-compliant because it couldn't find an explicit rule permitting it. But the harness has one test case with an elevated threshold — `tc008`, Peanut + Tree Nut Allergy, `expected_min_compliance: 0.85` versus 0.70–0.80 everywhere else — specifically because a false "compliant" there isn't an annoyance, it's a safety failure. One leniency default was doing two incompatible jobs.

**Fix:** split the default. General constraints keep "when in doubt, compliant." Allergen constraints flip to "when in doubt, non-compliant," with the judge also tagging each item `allergen_relevant: true/false` so the two populations can be measured separately instead of blending into one number that hides the one that matters.

## Bug 2 — trusting that the judge preserves order

```python
# before
for item, judgment in zip(recommendations, judgments):
    validated.append({**item, "passed": bool(judgment.get("compliant", True)), ...})
```

This assumes the 8B-tier judge returns exactly N judgments in the same order as the N items it was given — enforced only by a prompt instruction, not a structural guarantee. If it drops, reorders, or merges items, `zip()` silently attaches the wrong verdict to the wrong food. No crash, no error, just a mislabeled item.

**Fix:** have the judge echo each item's `name` in its response, match by normalized name, and fall back to position only for genuinely unmatched leftovers — logged as a fallback, not silently trusted.

## Bug 3 — found by testing, not reading

This one I didn't spot by inspection. Building the human-in-the-loop feedback feature meant I needed to know the *real* Langfuse SDK API, not the one I assumed from the README. So I imported the installed client and asked it directly what methods it had:

```python
>>> from langfuse import Langfuse
>>> c = Langfuse(public_key='pk-test', secret_key='sk-test')
>>> hasattr(c, 'trace')
False
```

`eval/runner.py` had been calling `langfuse.trace(name="healthcart_eval_run", ...)` since the project's first commit. That method doesn't exist on the installed v3 SDK (`langfuse>=3.0.0,<4.0.0` — it replaced the old `.trace()` builder with `start_as_current_span()` + `score_current_trace()`). Every eval run's aggregate scores had been silently failing to log, caught by a broad `except Exception: print("Could not log to Langfuse")` that nobody was reading closely enough to notice.

**The lesson, not just the fix:** the eval harness's own claim about itself — "every run logs `eval_pass_rate` and `avg_compliance_rate` to Langfuse" — was false, and had been false the whole time, and nothing in the system would have told me if I hadn't gone and checked the client's actual method list by hand.

## The architecture pivot — a plan meeting a closed door

The original plan (from an earlier pass at this project) was to ground generated grocery items against a real retailer catalog — Instacart's Developer Platform, specifically, since it's the exact kind of "LLM gateway / real integration" work a platform PM role asks for. I went to check the actual application process before building toward it.

```
Instacart is currently not accepting new applications.
```

Even when open, average approval time was 30–40 days. That's not a foundation to build a portfolio project's core architecture on. Rather than leave the plan as aspirational vaporware, I pivoted to USDA FoodData Central — free, no approval process, 380k+ foods, government-verified. Different trade: I lose retailer purchasability (is this actually buyable right now), but I gain something arguably more important to the actual thesis — real nutrient numbers to check numeric thresholds against, instead of the model's guess at what a food "probably" contains.

## The wrong guess — and getting caught by my own verification habit

After wiring up USDA grounding, I ran the allergy test case and got a genuinely strange result: **0% allergen compliance rate**, and only ~30% of items grounded against USDA at all (5 of 16). My first explanation, which I stated with more confidence than I'd earned:

> "USDA's Foundation/SR Legacy datasets use plain scientific food descriptions, while the LLM generates consumer-marketing names like 'Grass-Fed Ground Beef' or 'Wild-Caught Salmon' — that naming mismatch is why so few items grounded."

Plausible-sounding. Also wrong. The tell was that items like **Spinach, Lentils, Quinoa** — about as generic as food names get — also failed to ground, and there's no naming-mismatch story that explains that. So instead of writing that explanation into the docs, I tested it:

```python
>>> requests.get(FDC_SEARCH_URL, params={"query": "Spinach", "api_key": "DEMO_KEY", ...})
{"error": {"code": "OVER_RATE_LIMIT", "message": "You have exceeded your rate limit..."}}
```

The real cause: the free shared `DEMO_KEY` rate-limits hard, and a single 16-item list makes 16 sequential USDA calls — most of the run was hitting HTTP 429, not "no match found." My code's `except Exception: return None` had been silently collapsing "we got rate-limited" and "USDA genuinely has nothing" into the same signal.

**Fix — and this is the one I'd actually flag as the interesting decision, not the bug itself:** `search_food()` now returns a real status —

```python
"grounded"       # real match, nutrients attached
"no_match"       # USDA genuinely has no entry
"lookup_failed"  # rate-limited / network error — the food may still exist
```

— and the UI shows three icons, not two: 🏪 grounded, ✨ no match, 🔌 lookup failed. Collapsing those into one "ungrounded" state would have been a second instance of exactly the failure pattern this whole project exists to argue against: a system quietly reporting confidence it hasn't earned.

## What's still open, on purpose

The human-in-the-loop thumbs up/down button is built and logs real scores against the exact trace that produced each verdict. It does **not** make the model learn — nothing in this stack does that automatically. It builds a labeled dataset. Turning that dataset into a better judge is a separate, unbuilt step (few-shot injection from corrected examples, or eventually fine-tuning), and I'm not claiming otherwise anywhere in these docs. The single largest unresolved gap in the whole project is still what it was before any of this session's fixes: there is no human-verified ground truth for what the judge gets right, only the judge's opinion of itself, now measured more honestly than it was this morning.

## Why this is the artifact, not the writeup about it

Everything above happened in the order it's written, including the wrong guess. A framework document can claim "assumption hygiene" as a section heading; this is what it actually looks like in practice — stating a belief, testing it, being wrong, and fixing the thing the evidence pointed to instead of the thing the first guess pointed to. That loop, run against a real eval harness instead of a hypothetical company's roadmap, is the whole pitch for treating this as a technical AI PM project rather than a strategy document with code attached.
