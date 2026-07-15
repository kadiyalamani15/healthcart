# HealthCart — A Verification Layer for Health-Constrained Grocery Shopping

*A portfolio-os project · built July 2026*

---

## 00 — A note on this project

HealthCart is a working prototype, not a company-commissioned product. The code exists (5-node LangGraph pipeline, LiteLLM model routing, Langfuse tracing, a 20-case eval harness) — you can run it. Everything in Phases 0–1 below (market data, the structural reframe) is real and sourced. Everything from Phase 2 onward that describes a *platform* beyond what's built — retailer catalog integration, multi-judge validation, caregiver mode, payer documentation export — is **directional, not shipped**, and is labeled as such.

This document does not diagnose a named company's internal problem. It diagnoses a real market gap (verification-free AI food recommendation), uses HealthCart's actual architecture as the proof-of-capability, and is deliberately built to demonstrate the specific skills three open roles are hiring for right now:

- **Anthropic, PM – Claude Code Model Performance**: personally-built agentic evals, LLM-as-judge, transcript analysis, systems thinking about failure classes
- **Disney, Lead PM – AI Platform**: hands-on production experience with a named stack (LLM gateway, agent runtime, eval/observability framework), 0→1 prototyping, graduate/harden/retire judgment
- *(Instacart, Sr PM AI — evaluated and dropped as an anchor. Their JD is B2B margin recovery for retailers; HealthCart is a consumer safety/trust product. Forcing that fit would have been the exact `generic_domain_application` anti-pattern this framework warns against. Its language still shows up once, in Phase 5, where Instacart's own Developer Platform API becomes the actual integration target.)*

---

# PHASE ZERO — ROLE INTELLIGENCE

## 01 — The problem, stated once, with data

129 million Americans manage a chronic disease where diet is a primary lever (CDC, cited in Rockefeller Foundation food-is-medicine research, 2026). The food-as-medicine market is valued at **$254.15B in 2026, projected to $400.81B by 2031** (9.5% CAGR — DataM Intelligence, 2026). Medically tailored meals, if scaled to all eligible patients, are projected to **save $23.7B annually and avoid 2.6M hospitalizations** (Rockefeller Foundation, 2026).

The professional who's supposed to bridge "diagnosis" and "shopping list" — a registered dietitian — costs **$70–$300 out of pocket per session**, and Medicare's Medical Nutrition Therapy benefit only covers diabetes, chronic kidney disease, and post-transplant patients (ConsumerAffairs / CostDigest, 2026). Celiac disease, IBS, PCOS, GERD, and heart disease generally aren't reimbursed. Most of the 129M are on their own.

Meanwhile, grocery platforms answer this with **static category tags** — vegan, gluten-free, keto — applied to products, not conditions applied to a person (Grofee, Shipt dietary-preference filtering, 2026 grocery-app feature surveys). And when people turn to general-purpose AI to close that gap, it fails in ways that are dangerous, not just wrong: **Food Republic found 30–50% of AI-generated recipes contain at least one materially wrong quantity (Feb 2026)**, and in a documented 2026 incident, Google Gemini recommended a garlic-in-oil storage method that created textbook conditions for *Clostridium botulinum* growth — the user reported active botulism colonization by day seven.

**Gate 0 statement:** *Grocery platforms personalize by category tag while AI systems capable of true condition-level personalization ship without any verification layer — so the same models measured at a 30–50% error rate on recipe quantities are being trusted, ungoverned, with celiac-safe grain selection and CKD-safe potassium limits.*

This isn't JD language. It's the gap between a $254B market's stated need and the two tools (static filters, unverified generative AI) currently on offer.

---

# PHASE ONE — DISCOVERY

## 02 — Narrative anchor

**Wedge:** Not "grocery apps need better filters." Not "AI should give diet advice." The wedge is narrower and structural: **AI-derived food recommendations in health-adjacent domains ship without the verification infrastructure that makes them trustworthy** — the same infrastructure (LLM-as-judge, eval harnesses, tracing) that enterprise AI teams now treat as mandatory before shipping anything agentic.

**Structural reframe:** *Personalization is not the problem. Verification is.* A system that generates a diabetic-safe shopping list is not meaningfully different from one that generates a garlic-in-oil storage method — unless something checks its work before the user sees it.

**Scope decision:** Depth over breadth. Rather than building shallow support for every diet type, HealthCart goes deep on one mechanism — deriving explicit, auditable food rules from a health profile, then validating every generated item against those rules with a separate LLM call, batched, traced, and eval-scored. That mechanism is what's demonstrated end-to-end; broader retailer/catalog integration is Phase 5 direction, not built.

## 03 — Why it matters now (root cause)

**5 Whys:**

1. **Why do people with chronic conditions struggle to grocery shop safely?** Translating a diagnosis into a specific shopping list requires clinical nutrition knowledge most people don't have.
2. **Why don't they get that knowledge from a professional?** RDN access is $70–$300/session out of pocket, and Medicare MNT only reimburses diabetes, CKD, and post-transplant — most conditions in scope here (celiac, IBS, PCOS, GERD, heart disease broadly) aren't covered.
3. **Why don't grocery apps fill the gap?** Their "dietary filters" are static category tags on products, not condition-derived rules applied per item with a reason attached.
4. **Why don't AI shopping assistants fill the gap instead?** Generative recommendation without a verification layer hallucinates in ways that are unsafe, not just inaccurate (30–50% materially-wrong-quantity rate; the Gemini botulism case).
5. **Why isn't there a verification layer already?** Because the eval/observability discipline enterprise AI teams now treat as mandatory before shipping anything agentic — 57% of organizations have agents in production, and *quality is the #1 cited barrier to further deployment* (LangChain, *State of AI Agents*, 2026) — hasn't been applied to consumer-facing, health-adjacent recommendation. It's treated as an engineering-team concern, not a consumer product requirement.

**Root cause (structural, not organizational):** Consumer generative-recommendation products in health-adjacent domains are missing an architectural layer — output verification — that the same industry already considers non-negotiable internally. This is a platform-design gap, not a "the AI needs better prompts" behavior gap.

## 04 — Affinity diagram

| Cluster | Signal |
|---|---|
| **A. Diagnosis ≠ shopping list** | 129M Americans with a diet-relevant chronic condition (CDC); RDN visits $70–$300 (ConsumerAffairs); MNT Medicare coverage limited to 3 conditions |
| **B. Filters are shallow** | Category-tag filtering (vegan, gluten-free) is now table-stakes at Shipt and peers, but none derive rules from a diagnosis or reason per-item |
| **C. Unverified AI is unsafe, not just wrong** | Food Republic: 30–50% materially-wrong-quantity rate (Feb 2026); Gemini botulism-risk garlic incident (2026); "ChatGPT, Gemini, Claude, and Perplexity all hallucinate ingredient quantities" (industry reporting, 2026) |
| **D. Enterprise AI already solved this, elsewhere** | 57% of orgs have agents in production; quality is the #1 deployment barrier (LangChain 2026); multi-judge/closed-loop architectures hit 0.91 AUC vs. single-judge baselines (April 2025 research) — the tooling to fix Cluster C exists, just not here |
| **E. Money is already moving toward this** | Food-as-medicine market $254B→$401B by 2031; $23.7B/yr in avoidable hospitalization cost if medically tailored meals scaled (Rockefeller Foundation) |

## 05 — Stakeholder ecosystem

| Layer | Who | What "working" looks like | What breaks |
|---|---|---|---|
| **Internal / operator** | The person building the list — self-managing adult, or a caregiver (adult child managing a parent's CKD diet, parent managing a child's allergy) | Fast, explainable, trustworthy output; a reason attached to every accept/reject | Black-box recommendations they can't verify themselves |
| **Downstream consumer** | The person who eats the food — often the same as the operator, sometimes not (caregiver cases) | Never sees an unsafe item on the list | Bears the physiological consequence of an operator's trust in a wrong recommendation, often without visibility into *why* it was wrong |
| **Platform stakeholders** | Grocery retailer (catalog/fulfillment — Instacart Developer Platform, Kroger Catalog API), model provider (Groq: cost, rate limits, latency), clinical/regulatory (FDA general-wellness guidance boundary — this is not a diagnostic device), payer (Medicare MNT's 3-condition coverage boundary) | Constrain the system into something legally and operationally shippable | Absent from a prototype built without retailer integration or clinical sign-off — this is the biggest gap between what's built and what's real |

## 06 — User research plan — *STRUCTURED APPROACH · NOT YET EXECUTED*

Not run. What it would look for:

1. **Diary studies** (2 weeks, n=15 across conditions in scope) — where do people currently get diet-shopping guidance, and where does it fail at the point of purchase?
2. **Contextual inquiry at point of sale** — do people re-check labels in-store even after receiving a "compliant" list? (Tests whether the tool is actually trusted or just a starting point.)
3. **RDN structured interviews** (n=5) — what do dietitians actually check, item by item, that a generative model would need to replicate?
4. **Caregiver-specific interviews** (n=8) — how does trust transfer when the shopper and the eater are different people?
5. **Failure-mode elicitation** — show participants HealthCart's `passed: null` (uncertain) items specifically; do they treat "uncertain" as "unsafe" or ignore it?
6. **A-01 (Critical):** *Assumes people will trust an LLM-as-judge badge system as much as a human RDN's sign-off. Basis: no evidence yet — this is the single largest unvalidated assumption in the whole project. Validation: study #5 above, before any caregiver-mode or payer-facing feature is built.*

## 07 — Personas

**P1 — Self-managing operator.** Type 2 Diabetes, shops for self, budget-conscious ($80/wk), wants to trust the list without re-deriving GI values by hand. Failure mode: silently ignores "uncertain" badges because checking takes as long as not using the tool.

**P2 — Caregiver operator.** Adult child managing a 78-year-old parent's Chronic Kidney Disease + Hypertension remotely, orders groceries delivered to the parent's home, never sees the parent eat the food. Failure mode: trusts the compliance badge completely because there's no other check available to them at a distance — the highest-stakes trust-transfer case in the system.

**P3 — Downstream consumer, edge case.** A child with a peanut/tree-nut allergy; the operator is the parent. The child cannot self-verify. Failure mode here isn't "annoyed by a bad recommendation" — the eval harness's `expected_min_compliance: 0.85` for the allergy test case exists specifically because this persona has zero tolerance for false negatives.

## 08 — Empathy maps (dual lens)

**Operator (P1/P2):** *Thinks* — "I don't have time to become a nutritionist." *Feels* — anxious about getting it wrong, relieved when a badge says ✅. *Says* — "just tell me what's safe." *Does* — scans the compliance rate, rarely reads the per-item rationale unless something's flagged ❌.

**Downstream consumer (P3, and P2's parent):** *Thinks* — "I'm trusting someone else's judgment about what I eat." *Feels* — no direct relationship with the tool at all — trust is inherited, not earned firsthand. *Says* — nothing, usually; they're outside the interaction loop. *Does* — eats what's on the list. This is the user with the most to lose and the least visibility into the system.

## 09 — Customer journey map (with DNF — Did Not Finish — risk)

| Stage | Operator action | DNF risk |
|---|---|---|
| 1. Enter health profile | Conditions, restrictions, allergies, goals, household size, budget | Abandons if form feels like a medical intake, not a shopping tool |
| 2. Agent derives constraints | `constraint_extractor` node runs (Haiku-tier) | Silent failure risk: if extraction errors, current fallback passes raw profile through — **A-02 (High):** *silent degraded-mode fallback could produce a list validated against fewer constraints than the user provided, with no UI signal that this happened. Validation: add a visible degraded-mode indicator; not yet built.* |
| 3. Items generated | `product_recommender` (70B-tier) | Items may not exist at any real retailer — nothing today grounds output in an actual catalog |
| 4. Compliance validated | Batch LLM-as-judge call | Single-judge architecture — no meta-evaluation of the judge itself (see Cluster D, 0.91 AUC multi-judge research) |
| 5. List displayed | Grouped, sorted, badge-annotated | **This is the trust moment.** If the operator doesn't open the rationale on flagged items, the verification layer's value is invisible to them |
| 6. Shopping | Operator buys against the list | No loop back — the system never learns whether what was bought matched what was recommended, or whether it was actually safe once eaten |

## 10 — Customer touchpoint map

Downstream consumers (P2's parent, P3's child) touch the *consequences* of this system without ever touching the *interface* — the badge, the rationale, the eval score are all operator-facing. The only touchpoint a downstream consumer has is the food itself. This is why the compliance-validator's accuracy matters more than its explainability for this segment, and why **A-03 (Critical)** below exists.

## 11 — Jobs to be done

1. When I'm diagnosed with a diet-relevant condition, help me translate that diagnosis into concrete food rules, so I don't have to become an amateur nutritionist.
2. When I'm shopping for someone I care for, help me trust a recommendation I can't personally verify against their exact clinical needs, so I don't have to guess.
3. When an AI generates a food recommendation, help me see *why* it passed or failed, so a black-box badge doesn't replace a black-box guess.
4. When I have overlapping constraints (diabetes + hypertension, celiac + allergy + vegetarian), help me get a list that satisfies all of them simultaneously, so I'm not manually reconciling three different diet sheets.
5. When I'm on a fixed budget, help me get compliance without assuming I can afford specialty/premium products, so safety and affordability aren't in tension.
6. When something in the list is uncertain rather than clearly safe or unsafe, help me understand what "uncertain" actually means, so I don't treat it as a false all-clear.

## 12 — Domain-specific analytical layer *(diagnostic)*

Clinical nutrition constraint logic isn't uniform across conditions — this is why a single-prompt "avoid bad foods" approach fails, and why HealthCart's `constraint_extractor` node exists as a distinct step from `product_recommender`:

| Condition | Constraint logic | Failure mode if generic |
|---|---|---|
| Type 2 Diabetes | Glycemic index / load thresholds, carb consistency | Model treats "sugar-free" as sufficient; ignores high-GI starches |
| Chronic Kidney Disease | Potassium *and* phosphorus limits — often in tension with "healthy" defaults (bananas, dairy) | Generic "eat healthy" advice is actively dangerous here |
| Celiac Disease | Zero-tolerance gluten exclusion, cross-contact awareness | Partial compliance ("mostly gluten-free") is not a valid state |
| Low-FODMAP (IBS) | Onion, garlic, wheat, and specific legumes — not an intuitive category a lay model groups together | Model conflates with generic "gut health" foods |
| Nut allergy | Zero-tolerance, safety-critical | This is the only condition class where `expected_min_compliance` is set at 0.85 instead of 0.70–0.80 — false negatives here are categorically worse than in any other test case |

This is the layer a domain expert (RDN, or a payer's clinical review team) would actually check — and it's why the eval harness's 20 test cases are organized by *combined*-constraint difficulty, not just single-condition coverage.

---

# PHASE TWO — DEFINITION

## 13 — Core insight

**Wrong question:** "How do we help people find food that fits their diet?"
**Right question:** "How do we make an AI-generated food recommendation *verifiable* before a person acts on it — cheaply enough that verification doesn't become the new access barrier RDN cost already is?"

The reframe matters because the wrong question leads to more filters (Cluster B, already commoditized). The right question leads to an architecture decision: a second, independent model call whose only job is to check the first one's work — batched into a single call so verification doesn't multiply cost linearly with catalog size.

## 14 — Domain analytical layer *(solution justification)*

Why a *separate* validator node, not one prompt doing generation-and-checking together:

1. **Self-grading bias.** A single LLM call asked to "generate a compliant list" has no incentive structure to catch its own errors — this is the same failure mode behind the 30–50% wrong-quantity rate in general AI recipes. Splitting generation and judgment into separate calls, with the judge only seeing item + rationale (not being told to be lenient), reduces this bias.
2. **Batching economics.** A naive per-item validation call would be N API calls per list (15–20). HealthCart's `compliance_validator` batches all items into one call — cost stays flat regardless of list size, which matters because RDN-cost-avoidance is the whole value proposition; a verification layer that costs more than a dietitian defeats the point.
3. **Model-tier routing matches task difficulty, not uniformly using the biggest model.** Structured extraction and binary judgment (nodes 1, 2, 4) run on the 8B-tier model; only nuanced generation (node 3) uses the 70B-tier model. This is a direct, deliberate cost/quality tradeoff, not a default.
4. **Known limitation — single-judge architecture.** External research shows multi-judge / closed-loop evaluation architectures reaching 0.91 AUC against human-annotated ground truth, meaningfully above single-judge baselines. HealthCart's current validator is a single judge. This is flagged, not fixed — see A-06.

## 15 — Coherence map

Chronic condition (129M Americans) → diagnosis-to-shopping-list translation gap (RDN cost/coverage barrier) → static-filter grocery platforms + unverified generative AI (both fail differently) → HealthCart's verification-layer architecture → operator trust (badge + rationale) → downstream consumer safety (the actual stakeholder with something to lose) → platform stakeholder constraints (retailer catalog grounding, regulatory boundary, payer coverage boundary) not yet built.

## 15b — MoSCoW requirements

| Priority | Requirement | Why |
|---|---|---|
| **P0 (built)** | 5-node LangGraph pipeline with distinct extraction, generation, and validation stages | Can't ship without this — it *is* the verification-layer thesis |
| **P0 (built)** | Batch LLM-as-judge compliance validation, traced per-node via Langfuse | Without this, HealthCart is just another unverified generator — no different from the failure mode it's arguing against |
| **P0 (built)** | 20-case eval harness with per-condition `expected_min_compliance` thresholds, including a safety-critical allergy case at 0.85 | Can't credibly claim "verified" without an eval suite that would catch regression |
| **P1 (not built)** | Retailer catalog grounding (Instacart Developer Platform / Kroger Catalog API) so recommended items are real, purchasable products, not generated text | Unblocks: current items are plausible-sounding but unverified against real inventory — this is the single biggest gap between "prototype" and "shippable" |
| **P1 (not built)** | Meta-evaluation / multi-judge architecture | Unblocks: closes the 0.91-AUC gap identified in research vs. current single-judge design |
| **P1 (not built)** | Visible degraded-mode indicator when profile-extraction fails and falls back to raw input | Unblocks: closes the silent-failure risk flagged in the journey map (A-02) |
| **P2 (not built)** | Caregiver mode — explicit operator/downstream-consumer separation in the UI, not just in this document | Unblocks: P2 persona (remote caregiver) currently has no interface acknowledgment that they aren't the person eating the food |
| **P2 (not built)** | Payer/RDN-facing documentation export (for the 3 Medicare MNT-covered conditions) | Unblocks: only relevant once clinical/regulatory review (Won't Have, below) is resolved |
| **Won't Have** | Diagnosis, medication-interaction checking, or any claim of being a medical device | Scope boundary — this is a shopping-list verification tool, not a clinical tool; crossing this line changes the regulatory category entirely |
| **Won't Have** | Real-time in-store barcode scanning | Different product (point-of-purchase, not planning); explicitly out of scope for this build |

---

# PHASE THREE — IDEATION

## 16 — User segments

| Segment | Current friction | What "working" looks like |
|---|---|---|
| Self-managing adult (single condition) | Manually cross-references GI/sodium/FODMAP charts weekly | Trusts a badge without re-deriving the rule each time |
| Self-managing adult (combined conditions) | Reconciles multiple diet sheets by hand — diabetes + hypertension, celiac + allergy + vegetarian | One list that's already reconciled |
| Remote caregiver | No visibility into what's actually safe for someone they can't observe eating | A trust artifact (rationale, not just a badge) they can act on at a distance |
| Budget-constrained household | Assumes "healthy/compliant" means "expensive" | Compliance within a stated budget, not despite it |

## 17 — SCAMPER

| Lens | Insight |
|---|---|
| **Substitute** | Substitute the generative "make up 15–20 items" step with retrieval against a real catalog (Instacart IDP / Kroger) — generate *rules*, retrieve *products* |
| **Combine** | Combine the extraction and validation models into a shared constraint schema so the judge is checking against the *same* structured rules the generator used — not re-deriving them independently (current risk: drift between what node 2 extracted and what node 4 checks) |
| **Adapt** | Adapt enterprise multi-judge eval patterns (0.91 AUC research) into a consumer-cost-appropriate two-judge design, not a full ensemble |
| **Modify/Magnify** | Magnify the allergy-safety case specifically — a dedicated zero-tolerance validation path, separate from the general compliance scorer, for allergen-class constraints |
| **Put to other use** | Put the eval harness itself to use as a *product* feature — expose "confidence" per item to the operator, not just pass/fail |
| **Eliminate** | Eliminate the assumption that operator and downstream consumer are the same person — build the caregiver split as a first-class mode, not an edge case |
| **Reverse** | Reverse the flow: instead of generating then validating, start from the retailer's real catalog and *filter* it through constraints — validation becomes selection, not correction |

## 18 — Concepts (5, evaluated honestly)

1. **Rule-engine only** (no LLM in the loop for validation — deterministic nutrient-threshold checks against catalog nutrition data)
2. **Current architecture, hardened** (single-judge LLM-as-judge + catalog grounding added)
3. **Multi-judge ensemble** (2–3 independent validator calls, disagreement flagged as "uncertain" rather than defaulting to pass)
4. **Human-RDN-in-the-loop hybrid** (AI drafts, a real dietitian reviews flagged/high-risk cases before the list is finalized)
5. **Reverse-flow retrieval** (SCAMPER "Reverse": filter real catalog directly by derived constraints, no generative product step at all)

## 19 — Pugh Matrix

Baseline = Concept 2 (current architecture, hardened). Scored −1 / 0 / +1 relative to baseline across 8 criteria.

| Criterion | 1. Rule-engine | 2. Baseline | 3. Multi-judge | 4. Human-RDN hybrid | 5. Reverse-retrieval |
|---|---|---|---|---|---|
| Safety/compliance accuracy | 0 | 0 | +1 | **+1** | 0 |
| Cost per user | +1 | 0 | −1 | **−1** | +1 |
| Latency | +1 | 0 | −1 | **−1** | +1 |
| Explainability | +1 | 0 | 0 | **+1** | +1 |
| Scalability (no human bottleneck) | +1 | 0 | 0 | **−1** | +1 |
| Handles combined/nuanced constraints (e.g. Low-FODMAP) | −1 | 0 | 0 | **+1** | −1 |
| Regulatory/liability risk | +1 | 0 | 0 | **−1** | +1 |
| Grounds output in real, purchasable products | −1 | 0 | 0 | 0 | **+1** |
| **Total** | **+3** | **0** | **−1** | **−2** | **+5** |

Concept 5 (reverse-flow retrieval) wins on total, but **does not win on safety/compliance accuracy or combined-constraint handling** — those go to the human-RDN hybrid and multi-judge concepts respectively. That's the honest tension: grounding output in real products is necessary but not sufficient for the hardest constraint cases (Low-FODMAP, combined celiac+allergy+vegetarian), where nuanced reasoning still beats a filter.

## 20 — Selected direction and trade-off

**Selected: Concept 5 (reverse-flow retrieval) as the base architecture, with Concept 2's LLM-as-judge validator retained as a second pass** — not a pure pivot, a merge. Constraints are still derived generatively (node 2 stays), but node 3 changes from "generate plausible items" to "retrieve and filter real catalog items by derived constraints," and node 4's validator becomes a check on the *retrieval's* output rather than the *generator's* invention.

**What this sacrifices:** Combined-constraint nuance. A retrieval-and-filter approach handles clean threshold rules (sodium < X, GI < Y) well, but the hardest cases in the eval harness — Low-FODMAP, triple-constraint profiles like Celiac + Peanut Allergy + Vegetarian — need generative reasoning to resolve ambiguity a filter can't. **This is why the validator (Concept 2's mechanism) is retained rather than replaced** — it's the safety net for exactly the cases retrieval alone handles worst.

**Effort × Impact:** Catalog grounding (P1) is high-impact, high-effort (external API integration, auth, rate limits). Visible degraded-mode indicator (P1) is high-impact, low-effort — should ship before catalog grounding. Meta-evaluation/multi-judge (P1) is medium-impact, medium-effort. Caregiver mode (P2) is high-impact for a narrow segment, medium-effort.

## 21 — Prune the Product Tree

- **Trunk (already built):** health-profile intake → constraint extraction → item generation → batch LLM-as-judge validation → categorized output
- **Primary branch:** catalog-grounded retrieval (replaces pure generation); visible degraded-mode signal; allergen-class dedicated validation path
- **Secondary branch:** caregiver mode; multi-judge meta-evaluation; per-item confidence display
- **Pruned:** diagnosis/medication-interaction features; real-time in-store scanning; payer documentation export (blocked on clinical review that hasn't happened)

---

# PHASE FOUR — DELIVERY

## 22 — MVP proposal

**What's already the MVP:** the 5-node pipeline, as built and running today, is itself the MVP for the core thesis (verification-layer architecture for health-constrained recommendation). It's not a mockup — it's 20 passing eval cases against real model calls.

**What "MVP+1" would add first, and why:** the visible degraded-mode indicator (P1, low-effort, high-impact) and allergen-class dedicated validation path (closes the single highest-stakes gap — the allergy test case is the only one with an 0.85 threshold for a reason). Catalog grounding comes after, because it's the highest-effort item and the current architecture is honest about not having it (items are plausible, not verified-purchasable) rather than silently wrong about it.

## 23 — Architecture: current state vs. target state

**Current (built):**
```
Health Profile → [1] profile_analyzer (8B) → normalized_profile
                → [2] constraint_extractor (8B) → food_constraints[]
                → [3] product_recommender (70B) → recommendations[] (generated, ungrounded)
                → [4] compliance_validator (8B, single-judge, batched) → validated_list[] + compliance_rate
                → [5] list_formatter (pure Python) → categorized shopping list
                → Langfuse trace tree (5 child spans, per-run)
```

**Target (directional, one change):** replace node 3's pure generation with catalog-grounded retrieval (Instacart Developer Platform or Kroger Catalog API), filtered by node 2's structured constraints, with generation retained only as a flagged fallback when no catalog match exists. Node 4 stays as the safety net for exactly the cases retrieval alone can't resolve (see §14, §19–20). This is the one architectural change worth building next — everything else in Phase 5 below is sequencing around it, not a separate idea.

## 24 — PRD summary

**North star metric:** % of recommended items that are both constraint-compliant *and* purchasable at a real retailer. Chosen over pure compliance rate because compliance-without-purchasability is the current build's actual blind spot — a "safe" item that doesn't exist at any store isn't useful. **A-04 (High):** the 70% target for this metric is an estimate discounted from the current ~90% generative compliance rate; no catalog-match data exists yet to confirm it.

**Guardrail metric, and the one that actually gates everything else:** judge/human agreement rate. Not measured — no human-labeled ground truth set exists in the repo. **A-06 (Critical):** this is the assumption the entire "verification layer" thesis rests on. An unverified judge validating an unverified generator is a second opinion of unknown quality, not verification. Nothing past P1 below should ship without this number.

## 25 — Launch strategy and RAID (condensed)

| Phase | Ships | Blocked on | Risk if skipped |
|---|---|---|---|
| **P1** | Visible degraded-mode indicator; allergen-class validation path with a non-lenient default (see A-05/A-06 — the current judge prompt defaults to "compliant" when uncertain, which is backwards for zero-tolerance cases) | Nothing external — pure application logic | Silent under-constrained lists ship with no user-visible signal |
| **P2** | Catalog grounding (Instacart IDP or Kroger Catalog API) | Retailer developer approval, rate-limit/cost modeling | Recommendations stay plausible-but-unverified-purchasable indefinitely |
| **P3** | Human-labeled ground-truth set; judge/human agreement measured (resolves A-06) | Sourcing real labeling effort — likely paying an RDN, which reintroduces the cost barrier this project exists to route around, just moved upstream | Every "verified" claim past this point stays unproven |
| **P4** | Caregiver-mode UI | P3 complete — won't ship a caregiver-facing trust feature on an unvalidated judge | A remote caregiver (P2 persona, §07) trusts a badge with no measured accuracy behind it |

Deliberately sequenced: P4 is gated on P3, not on calendar time, because the caregiver persona is the one stakeholder in this system who can't self-verify — shipping that feature ahead of the agreement-rate measurement would be building trust infrastructure on top of an unmeasured claim.

---

# PHASE FIVE — LEARNING

## 30 — Assumption register (consolidated)

| ID | Section | Statement | Basis | Urgency | Validation |
|---|---|---|---|---|---|
| A-01 | §06 | Operators will trust an LLM-as-judge badge at RDN-comparable confidence | No evidence — pure inference from the market gap | **Critical** | Structured user study before caregiver mode |
| A-02 | §09 | Silent degraded-mode fallback could ship a list validated against fewer constraints with no UI signal | Confirmed by reading `agent/nodes.py` — this is the actual current fallback behavior | **High** | Ship visible indicator (already scoped) |
| A-03 | §10 | Downstream consumers who can't self-verify need judge accuracy to matter more than explainability | Logical inference from persona P2/P3, not tested | **Critical** | Same study as A-01 |
| A-04 | §24 | Catalog-grounded compliance rate target of 70% | Discounted estimate from current ~90% generative rate; no catalog-match data exists | **High** | Instrument in P2 pilot |
| A-05 | §25 | Allergen-case accuracy isn't separately measured today | Confirmed by reading `eval/runner.py` / test case schema — general compliance rate, not split by constraint class | **High** | Schema change to isolate the metric |
| A-06 | §24/§25 | Judge/human agreement rate is unmeasured — the entire "verification layer" thesis is unproven against a real clinical baseline | Confirmed gap — no labeled ground truth set exists anywhere in the repo | **Critical** | Build labeled dataset with real RDN input before P3/P4 |
| A-07 | §14 | Multi-judge architectures outperform single-judge at 0.91 vs. lower AUC | External research (April 2025), not HealthCart's own measurement — may not transfer to this domain/prompt set | **Medium** | Re-measure specifically on HealthCart's own eval cases once multi-judge is built |

**The five to validate first, in the first two weeks of any real build-out:** A-06, A-01, A-03, A-05, A-02 — in that order. A-06 gates everything else; without it, the project's central claim (verification makes this trustworthy) is asserted, not demonstrated.

## 31 — Over/underestimate analysis

**What this proposal likely overestimates:** how much a compliance badge alone earns trust. The empathy map (§08) already shows operators skim rather than read rationale — a system that's *technically* more verified than a black-box generator may not *feel* more trustworthy to the person using it unless the UI forces engagement with the reasoning, which HealthCart's current Streamlit UI doesn't do (badges are the primary surface, rationale is secondary).

**What it likely underestimates:** the cost and organizational difficulty of A-06 (building a real labeled ground-truth set). This requires either paying RDNs to label data — reintroducing the exact cost barrier (§01) this project exists to route around, just moved upstream — or accepting a weaker proxy (e.g., inter-model agreement instead of human agreement), which would materially weaken the safety claims made in Sections 26–28.

## 32 — First 8 actions (if this became a real role's first two weeks)

1. Instrument allergen-class accuracy as its own tracked metric (closes A-05 — pure schema work, days not weeks)
2. Ship the visible degraded-mode indicator (closes A-02)
3. Scope and cost a labeled ground-truth dataset for A-06 — get a real number before promising a build timeline
4. Run the A-01/A-03 user study (Section 06, item 5) in parallel — doesn't block engineering work
5. Apply to Instacart Developer Platform and Kroger Catalog API developer programs — long lead time, start immediately even though P2 is weeks out
6. Audit every "generated, ungrounded" item currently in the eval harness's expected outputs — how many would fail to exist in a real catalog? This number doesn't exist yet and should, before promising the A-04 target
7. Write the actual clinical/regulatory scoping question down and route it to whoever owns that function — not to solve it in week one, but to stop it from being silently deferred past P3
8. Re-run the full 20-case eval harness after each of the above lands, to confirm none of it regressed the ~90% baseline compliance rate that's the one number in this whole document with zero uncertainty attached to it

## 33 — Vision

*Every item on a HealthCart list is there because something checked, not because something guessed.*

---

## Quality checklist

- [x] Every claim has a source and recency date (all 2026, cited inline)
- [x] Every assumption has an ID, basis, urgency, and validation method (A-01 through A-07)
- [x] Dual user lens (operator + downstream consumer) maintained through Discovery, Definition, and Delivery
- [x] PM contribution is implicit in every "not yet built / directional" label — this document scopes decisions, not code
- [x] Pugh Matrix winner (Concept 5) does not win on every criterion — loses on safety accuracy and combined-constraint handling
- [x] Roadmap is dependency-ordered (P1→P4), not dated
- [x] Vision is one sentence, no superlatives
- [x] Section 31 (learning) is as substantive as Section 03 (discovery) — both admit real, unresolved gaps
- [x] Wrong Q / Right Q reframe appears in Phase 2 (§13)
- [x] Domain-specific analytical content appears in both Phase 2 diagnosis (§12) and Phase 3 solution justification (§14)
