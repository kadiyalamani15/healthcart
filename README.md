# HealthCart 🛒

A health-constrained grocery agent that translates your medical conditions, dietary restrictions, and allergies into a validated weekly shopping list — with every item scored by an LLM-as-judge compliance validator.

**Stack:** LangGraph · LiteLLM · Langfuse · Groq · Streamlit · Python

---

## What it does

1. You enter your health profile (conditions, restrictions, allergies, goals, household size, budget)
2. The agent derives specific food rules from your conditions (e.g. "avoid glycemic index > 55 for Type 2 Diabetes")
3. It generates 15–20 grocery items that satisfy those rules
4. Every item is validated by an LLM-as-judge in a single batch call
5. Results are grouped by category, sorted by compliance, and displayed with ✅/❌/⚠️ badges

---

## Pipeline Architecture

| Node | Model | Responsibility |
|------|-------|---------------|
| 1 · profile_analyzer | llama-3.1-8b-instant | Normalize raw health profile → structured JSON |
| 2 · constraint_extractor | llama-3.1-8b-instant | Translate conditions → specific food rules |
| 3 · product_recommender | llama-3.3-70b-versatile | Generate 15–20 grocery items satisfying all constraints |
| 4 · compliance_validator | llama-3.1-8b-instant | LLM-as-judge: batch-validate all items in one call |
| 5 · list_formatter | Pure Python | Group by category, sort passed items first, compute rate |

Each node is decorated with `@observe()` — every run creates a full trace tree in Langfuse with child spans per node.

**North-star metric:** % of recommendations passing automated constraint compliance

---

## Eval Harness

`eval/test_cases.json` contains 20 pre-defined test profiles covering:
- Single conditions: Type 2 Diabetes, Hypertension, Celiac Disease, Heart Disease, High Cholesterol, IBS, PCOS, Chronic Kidney Disease
- Combined conditions: Diabetes + Hypertension, Celiac + Lactose Intolerant, Vegan + Diabetes, and more
- Allergy safety: Peanut + Tree Nut (expected ≥85% compliance)

Each case has an `expected_min_compliance` threshold. The harness logs `eval_pass_rate` and `avg_compliance_rate` as Langfuse scores, creating a feedback loop for prompt iteration.

```bash
# Run all 20 cases
python -m eval.runner

# Run first 5
python -m eval.runner --n 5

# Run a specific case
python -m eval.runner --id tc008
```

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/kadiyalamani15/healthcart.git
cd healthcart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Groq — free tier (no credit card required)
# Sign up at console.groq.com → API Keys
GROQ_API_KEY=gsk_...

# Langfuse — trace observability
# Sign up at cloud.langfuse.com or us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### 3. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501), fill in your health profile, and click **Generate Shopping List**.

---

## Project Structure

```
healthcart/
├── agent/
│   ├── graph.py        # LangGraph StateGraph — 5-node linear pipeline
│   ├── nodes.py        # Node functions with @observe() tracing
│   ├── prompts.py      # Prompt templates for each node
│   └── state.py        # AgentState TypedDict
├── eval/
│   ├── runner.py       # CLI eval harness — runs cases, logs to Langfuse
│   └── test_cases.json # 20 test profiles with expected compliance thresholds
├── app.py              # Streamlit UI
├── requirements.txt
└── .env.example
```

---

## LLMOps Observability

Every pipeline run is traced in Langfuse:

- Root trace: `healthcart_agent`
- Child spans: `profile_analyzer`, `constraint_extractor`, `product_recommender`, `compliance_validator`, `list_formatter`
- Eval scores: `eval_pass_rate`, `avg_compliance_rate` (logged by the eval harness)

---

## Model Routing

LiteLLM routes by task type:

| Alias | Model | Used for |
|-------|-------|----------|
| `HAIKU` | `groq/llama-3.1-8b-instant` | Structured extraction, binary judgment |
| `SONNET` | `groq/llama-3.3-70b-versatile` | Nuanced recommendation generation |

To swap providers, change the two constants in `agent/nodes.py`. LiteLLM supports Anthropic, OpenAI, Gemini, and 100+ others.

---

## Supported Health Profiles

Conditions: Type 2 Diabetes, Type 1 Diabetes, Hypertension, High Cholesterol, Heart Disease, Celiac Disease, IBS, GERD, Chronic Kidney Disease, PCOS, Hypothyroidism, Crohn's Disease

Restrictions: Vegetarian, Vegan, Gluten-free, Dairy-free, Keto, Paleo, Low-FODMAP, Halal, Kosher

Allergies: Peanuts, Tree nuts, Shellfish, Fish, Eggs, Dairy, Wheat/Gluten, Soy, Sesame

---

## License

MIT
