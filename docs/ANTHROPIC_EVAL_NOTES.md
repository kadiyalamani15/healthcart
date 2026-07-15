# Eval Notes: What My Own LLM-as-Judge Got Wrong

*Written for the Claude Code Model Performance role. This is not a product pitch — it's a walkthrough of one agentic eval harness I built, one real bug I found in it by rereading my own prompts, and what I'd change.*

---

## The setup

HealthCart is a 5-node LangGraph pipeline: it takes a health profile, derives food constraints, generates a grocery list, and validates every item against the constraints with a second, independent LLM call — an LLM-as-judge. I built a 20-case eval harness (`eval/runner.py` + `eval/test_cases.json`) that runs the full pipeline against pre-defined profiles and checks the reported compliance rate against a per-case expected minimum. Everything below is from reading the actual code and prompts, not from a retrospective narrative.

```
python -m eval.runner            # all 20 cases
python -m eval.runner --id tc008 # single case — Peanut + Tree Nut allergy, expected ≥85%
```

## The bug I found by rereading my own judge prompt

The compliance validator's system prompt (`agent/prompts.py`) contains this:

```
Evaluation rules:
- Mark an item non-compliant ONLY if it directly contradicts a constraint
- Neutral or beneficial items should be marked compliant: true.
- When in doubt, mark compliant: true.
```

I wrote "when in doubt, mark compliant: true" to reduce false positives on the compliance rate — a reasonable instinct if the failure mode I was optimizing against was *annoying* false rejections (marking a safe spinach item non-compliant for no reason). But it's the wrong default for the one test case where it matters most: **tc008, Peanut + Tree Nut allergy, `expected_min_compliance: 0.85`** — the only case in the harness with an elevated threshold, specifically because false negatives there aren't an annoyance, they're a safety failure.

An eval harness that passes 90% average compliance across 20 cases tells you almost nothing if the judge's own instructions bias it toward "compliant" on exactly the class of error that matters most. The aggregate number looks good and hides the failure mode it exists to catch. This is the same shape of problem as a coding eval that rewards "code that compiles" without checking whether it does the right thing — a metric that's *directionally* correct but silently wrong on the tail that matters.

**What I'd change:** allergen-class constraints need a separate validation path with the opposite default — "when in doubt, mark non-compliant" — and a metric that tracks allergen-case accuracy in isolation, not folded into the general compliance rate. Right now the harness can't even tell me if this happened, because `eval/runner.py` reports one `compliance_rate` per case, not a per-constraint-class breakdown. That's a measurement gap, not just a prompt gap.

## The second thing I noticed: positional mapping is fragile

`compliance_validator_node` maps the judge's output back to the original items by list position:

```python
for item, judgment in zip(recommendations, judgments):
    validated.append({**item, "passed": bool(judgment.get("compliant", True)), ...})
```

This assumes the judge returns exactly N judgments, in the same order as the N items it was given — enforced only by a prompt instruction ("same order as the input"), not by any structural guarantee. On an 8B-parameter model (llama-3.1-8b-instant, chosen for cost on this node), that's a real assumption to be making silently. If the judge drops an item, reorders, or merges two items into one judgment, `zip()` will silently misalign item N's name with item N+1's judgment — no error, no crash, just a wrong compliance label attached to the wrong food. I haven't yet instrumented the harness to detect this specific failure mode (it would show up as a coherence check: does `judgment["name"]` match `item["name"]` before trusting the alignment) — that's a concrete next step, not a hypothetical one.

Also worth naming: `judgment.get("compliant", True)` — the *default* if the key is missing at all is also `True`. Two independent leniency defaults stacked on top of each other, both in the direction of false-pass.

## Why the aggregate metric was the wrong first thing to optimize

The harness's own summary output (`print_summary`) surfaces pass rate and average compliance rate front and center. Those are the numbers I'd naturally watch during prompt iteration — and they're exactly the numbers that don't move when the underlying problem is "the judge is lenient on the one case class where leniency is dangerous." A single scalar metric across heterogeneous constraint classes (glycemic index thresholds, zero-tolerance allergen exclusion, potassium/phosphorus limits for kidney disease) hides more than it shows, because a model that's excellent at threshold-based nutrient rules and weak at zero-tolerance exclusion rules will still show a healthy-looking blended average.

This is the actual reason I think eval design for agentic systems is harder than it looks from the outside: the metric you pick shapes what you go looking for, and a metric that averages across failure classes of very different severity will always undersell the class you should be most afraid of.

## What I'd build next, in order

1. **Split the compliance metric by constraint class** (allergen/zero-tolerance vs. threshold-based) before touching anything else — this is a schema change to `eval/runner.py` and `test_cases.json`, not a new capability, and it's the only way to know if problem #1 above is actually fixed after I fix the prompt.
2. **Flip the allergen-path default** from "when in doubt, compliant" to "when in doubt, non-compliant" — and re-run the harness to confirm tc008's real (not blended) accuracy, which I currently can't isolate.
3. **Add a name-match sanity check** between judge output and input items before trusting positional alignment — cheap, catches the silent-misalignment failure mode without needing a bigger model.
4. **Build a small human-labeled set** (even 20–30 items, hand-checked against real dietary guidance) to measure judge/human agreement directly — right now the only ground truth in this system is the judge's own opinion of itself, which is not ground truth at all. I don't have this yet, and I think it's the single highest-leverage thing missing from the project, more than any UI or integration work.

## Why this is the part I'd want to talk about

None of the above is about the product idea. It's about what happens when you build the eval harness meant to catch a model's mistakes, and then find a mistake in the eval harness itself by rereading the prompt you wrote it with. That loop — build the eval, distrust the eval, reread the transcript-level detail, find the actual bug — is the same loop I'd expect to run daily against Claude Code: not "did the pass rate go up," but "what is this metric actually letting through, and would I have caught it if I hadn't gone looking."
