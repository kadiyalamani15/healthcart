"""
HealthCart — Streamlit UI

Run with:
    streamlit run app.py
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import litellm

from agent.graph import run_agent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HealthCart",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 HealthCart")
st.caption(
    "Health-constrained grocery agent · "
    "Built with **LangGraph** + **LiteLLM** + **Langfuse**"
)

# ---------------------------------------------------------------------------
# Sidebar — Health Profile Form
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Your Health Profile")

    conditions = st.multiselect(
        "Medical conditions",
        options=[
            "Type 2 Diabetes", "Type 1 Diabetes", "Hypertension",
            "High Cholesterol", "Heart Disease", "Celiac Disease",
            "IBS", "GERD / Acid Reflux", "Chronic Kidney Disease",
            "PCOS", "Hypothyroidism", "Crohn's Disease",
        ],
        help="Select all that apply",
    )

    restrictions = st.multiselect(
        "Dietary restrictions",
        options=[
            "Vegetarian", "Vegan", "Gluten-free", "Dairy-free",
            "Keto", "Paleo", "Low-FODMAP", "Halal", "Kosher",
        ],
    )

    allergies = st.multiselect(
        "Allergies (strict avoidance)",
        options=[
            "Peanuts", "Tree nuts", "Shellfish", "Fish",
            "Eggs", "Dairy", "Wheat / Gluten", "Soy", "Sesame",
        ],
    )

    goals = st.multiselect(
        "Health goals",
        options=[
            "Blood sugar management", "Lower blood pressure",
            "Reduce cholesterol", "Weight loss", "Heart health",
            "Gut health", "Anti-inflammatory", "Increase energy",
            "Hormone balance", "Increase protein",
        ],
    )

    household_size = st.slider("Household size", min_value=1, max_value=6, value=2)
    budget = st.text_input("Weekly budget (optional)", placeholder="e.g. $100/week")

    st.divider()
    generate = st.button("🛒 Generate Shopping List", use_container_width=True, type="primary")

    st.divider()
    run_eval_btn = st.button("🧪 Run Eval Harness (5 cases)", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

if not generate and not run_eval_btn:
    st.info(
        "Fill in your health profile in the sidebar and click **Generate Shopping List**. "
        "The agent will derive food constraints from your conditions, generate grocery "
        "recommendations, and validate each item for compliance."
    )

    with st.expander("How it works"):
        st.markdown("""
**Pipeline (LangGraph — 5 nodes):**

| Node | Model | What it does |
|---|---|---|
| 1 · profile_analyzer | Claude Haiku | Normalizes your health conditions |
| 2 · constraint_extractor | Claude Haiku | Translates conditions → specific food rules |
| 3 · product_recommender | Claude Sonnet | Generates 15–20 grocery items |
| 4 · compliance_validator | Claude Haiku (judge) | Scores each item against the constraints |
| 5 · list_formatter | Pure Python | Groups by category, sorts passed first |

**North-star metric:** % of recommendations passing automated constraint compliance

**Langfuse:** Every pipeline run is traced — each node creates a child span.
Open your Langfuse dashboard to see the full trace tree.
        """)

# ---------------------------------------------------------------------------
# Generate shopping list
# ---------------------------------------------------------------------------

if generate:
    if not conditions and not restrictions and not allergies:
        st.warning("Add at least one condition, restriction, or allergy to get started.")
        st.stop()

    profile = {
        "conditions": conditions,
        "restrictions": restrictions,
        "allergies": allergies,
        "goals": goals,
        "household_size": household_size,
        "budget": budget or "flexible",
    }

    with st.spinner("Running agent pipeline..."):
        try:
            result = run_agent(profile)
        except Exception as exc:
            st.error(f"Agent error: {exc}")
            st.stop()

    shopping_list = result.get("shopping_list", [])
    constraints = result.get("food_constraints", [])
    compliance_rate = result.get("compliance_rate", 0.0)
    summary = result.get("summary", "")

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    total = len(shopping_list)
    passed = sum(1 for i in shopping_list if i.get("passed") is True)
    categories = len({i.get("category", "Other") for i in shopping_list})

    col1.metric("Total Items", total)
    col2.metric("Compliance Rate", f"{compliance_rate:.0%}", delta=f"{passed} passed")
    col3.metric("Categories", categories)

    # Derived constraints
    if constraints:
        with st.expander(f"📋 Derived food constraints ({len(constraints)})"):
            for c in constraints:
                st.markdown(f"- {c}")

    st.divider()

    # Grocery list grouped by category
    if not shopping_list:
        st.warning("No items generated. Check your profile and try again.")
        st.stop()

    by_category: dict = {}
    for item in shopping_list:
        cat = item.get("category", "Other")
        by_category.setdefault(cat, []).append(item)

    CATEGORY_EMOJI = {
        "Produce": "🥦", "Protein": "🥩", "Grains": "🌾",
        "Dairy/Alternatives": "🥛", "Pantry": "🫙", "Beverages": "🧃",
        "Frozen": "🧊", "Other": "📦",
    }

    for cat in sorted(by_category.keys()):
        emoji = CATEGORY_EMOJI.get(cat, "📦")
        st.subheader(f"{emoji} {cat}")

        for item in by_category[cat]:
            passed_flag = item.get("passed")
            if passed_flag is True:
                badge = "✅"
                badge_color = "green"
            elif passed_flag is False:
                badge = "❌"
                badge_color = "red"
            else:
                badge = "⚠️"
                badge_color = "orange"

            col_name, col_qty, col_badge, col_rationale = st.columns([2, 1, 0.4, 4])
            with col_name:
                st.write(f"**{item.get('name', '')}**")
            with col_qty:
                st.caption(item.get("quantity", ""))
            with col_badge:
                st.write(badge)
            with col_rationale:
                note = item.get("compliance_notes", "")
                rationale = item.get("rationale", "")
                if passed_flag is False and note:
                    st.caption(f"⚠️ {note}")
                else:
                    st.caption(rationale)

    st.divider()
    st.caption(summary)
    st.caption("💡 All LLM calls and node traces are visible in your Langfuse dashboard.")

# ---------------------------------------------------------------------------
# Eval harness tab
# ---------------------------------------------------------------------------

if run_eval_btn:
    st.subheader("🧪 Eval Harness — 5 Test Cases")
    st.caption("Running 5 pre-defined test cases through the full pipeline and scoring compliance.")

    from eval.runner import load_cases, run_eval
    from langfuse import Langfuse

    cases = load_cases(n=5)
    langfuse_client = Langfuse()

    results_placeholder = st.empty()
    progress = st.progress(0)
    eval_results = []

    with st.spinner("Running eval harness..."):
        try:
            summary = run_eval(cases, langfuse_client)
            eval_results = summary["results"]
        except Exception as exc:
            st.error(f"Eval error: {exc}")
            st.stop()

    progress.progress(1.0)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Cases Run", summary["total_cases"])
    col2.metric("Pass Rate", f"{summary['pass_rate']:.0%}",
                delta=f"{summary['passed']}/{summary['total_cases']} passed")
    col3.metric("Avg Compliance", f"{summary['avg_compliance_rate']:.0%}")

    # Per-case results
    st.markdown("**Per-case results:**")
    for r in eval_results:
        status = "✅" if r["passed"] else ("🔴" if r["error"] else "❌")
        color = "green" if r["passed"] else "red"
        with st.expander(
            f"{status} [{r['test_id']}] {r['name']} — "
            f"{r['compliance_rate']:.0%} (min {r['expected_min']:.0%})"
        ):
            if r["error"]:
                st.error(f"Error: {r['error']}")
            else:
                st.write(f"Compliance rate: **{r['compliance_rate']:.0%}**")
                st.write(f"Expected minimum: {r['expected_min']:.0%}")
                st.write(f"Items generated: {r['item_count']}")
                st.write(f"Result: {'**PASS**' if r['passed'] else '**FAIL**'}")

    st.caption("Full traces logged to Langfuse with `eval_pass_rate` and `avg_compliance_rate` scores.")
