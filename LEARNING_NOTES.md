# Aus Gov Data Explorer — Engineering & Architecture Learning Notes (`LEARNING_NOTES.md`)

This document is written for engineers and data scientists who understand Python and basic machine learning, but are exploring how to build **disciplined, production-grade AI data systems**. It documents the architectural decisions, mathematical foundations, and real-world failure modes encountered while implementing the three scoped extensions to the **Aus Gov Data Explorer**:

1. **Multi-Table Ingestion & Cross-Dataset NL→SQL Joins** (ABS Table 012 Youth Unemployment)
2. **Opt-in Statistical Forecasting vs. Observational Guardrails** (Holt-Winters with Bounded Confidence Intervals)
3. **Self-Healing SQL Reflection Loops** (Error Feedback, Retry Capping, and Anti-Papering Defenses)

---

## 1. Multi-Table Ingestion & Cross-Dataset NL→SQL Joins

### The Problem
Real-world enterprise data rarely lives in a single clean table. An AI system that can only query one denormalized table is essentially a glorified filter. To support meaningful economic analysis, the system must answer questions like: *"How does youth unemployment compare to headline unemployment in Australia?"* or *"What is the gap between youth and overall rates?"*

This requires ingesting a secondary ABS dataset (Catalogue 6202.0 Table 012) and enabling the natural language layer to construct multi-table SQL `JOIN` operations.

---

### Header Parsing: Table 010 vs. Table 012

In ABS time-series workbooks, metadata is embedded inside hierarchical header strings in the `Index` sheet. When extending the ingestion pipeline from Table 010 to Table 012, we discovered an immediate structural difference:

* **Table 010 (State & National General Labour Force)**:
  ```
  "Employed total ; Persons ; > New South Wales ;"
  ```
  This string splits into **three** discrete segments: `[Metric, Sex, Region]`.

* **Table 012 (Youth Labour Force, 15–19 Year Old Cohort)**:
  ```
  "Unemployment rate ; Persons ;"
  ```
  This string splits into only **two** segments: `[Metric, Sex]`. There is no region segment!

#### Why did this difference matter?
If we naively applied Table 010's parser to Table 012 without modification, `region` would be assigned `None` or `Unknown`. 

Why does Table 012 omit the region? Because the ABS publishes Table 012 **exclusively at the National level (Australia)** for the 15–19 age cohort. It does not publish separate state-by-state monthly series for this table.

#### The Architectural Fix
In `backend/data_ingest.py`, we generalized `clean_description()`:
```python
def clean_description(desc: str):
    parts = [p.strip().lstrip('>').strip() for p in desc.split(';') if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        # Crucial normalization: missing region is explicitly mapped to 'Australia'
        return parts[0], parts[1], "Australia"
    return parts[0] if parts else "Unknown", "Persons", "Australia"
```
By mapping the missing geographic dimension to `"Australia"`, Table 012 rows share identical key conventions (`date`, `region`) with Table 010.

---

### Why Multi-Table NL→SQL is Dramatically Harder than Single-Table

Moving from single-table to multi-table text-to-SQL introduces three major failure vectors:

#### 1. Schema Context Budget & Attention Dilution
In single-table queries, the LLM only needs to remember column names for `labour_force_monthly`. In multi-table environments, the schema context doubles. If the prompt fails to explicitly specify which table contains which metric, LLMs frequently invent columns on the wrong table (e.g. generating `SELECT h.youth_unemployment_rate FROM labour_force_monthly h`).

#### 2. Join Key Disambiguation & Cartesian Traps
To join Table 010 (`labour_force_monthly`) and Table 012 (`youth_unemployment`), the model must join on **both** `date` and `region`:
```sql
FROM youth_unemployment y
JOIN labour_force_monthly h 
  ON y.date = h.date AND y.region = h.region
```
If the model joins only on `date` without filtering `h.region = 'Australia'`, SQLite produces a **Cartesian product**—matching 1 youth row with 9 state rows for every single month. Aggregations (like averages or sums) calculated on this Cartesian explosion become silently incorrect by an order of magnitude.

#### 3. AST Allowlist Validation on Table Aliases
Our security layer (`backend/sql_validator.py`) uses `sqlglot` to parse generated SQL into an Abstract Syntax Tree (AST) to ensure queries only touch approved tables. In multi-table queries with aliases:
```sql
SELECT y.date, y.youth_unemployment_rate FROM youth_unemployment AS y
```
A naive AST validator might inspect the table name `y` and reject the query because `y` is not in `ALLOWED_TABLES`. The validator must explicitly inspect table definitions and CTE scopes before validating against the security allowlist.

---

## 2. Opt-in Statistical Forecasting vs. Observational Guardrails

### The Core AI Safety Concept: Refusal vs. Bounded Uncertainty

In naive "Chat with your data" prototypes, when a user asks:
> *"What will the unemployment rate in Australia be in 2035?"*

The LLM will happily hallucinate an authoritative-sounding answer (e.g. *"In 2035, Australia's unemployment rate is projected to be 4.1% due to green energy investments..."*). This is fundamentally dangerous in policy or financial contexts:
1. The ABS dataset contains **purely observational historical records** (1978–2026). It contains zero future data.
2. The language model has no economic general equilibrium model running in its weights—it is simply generating believable prose tokens.

#### Guardrail 1: Strict Default Refusal
We preserve our non-negotiable refusal guardrail: general future questions asked in standard conversational mode are refused immediately:
> *"Refusal: This application does not predict future events as official facts. The ABS dataset contains actual historical observations up to July 2026."*

#### Guardrail 2: Explicit Opt-in Statistical Projection
Rather than permanently blinding the user to forward projections, we provide an **explicit, opt-in statistical forecasting mode**:
- The user must deliberately request a projection (e.g. *"Project unemployment in NSW for the next 12 months"*).
- If the question is ambiguous (e.g. *"What's next for unemployment in NSW?"*), the system does **not** guess; it returns an interactive clarification asking whether the user wants historical momentum or an opt-in projection.
- When activated, calculations are executed by a **deterministic time-series model (Holt-Winters)**, accompanied by **80% and 95% confidence intervals**, visually styled as a dashed projection line, and stamped with a prominent disclaimer:
  > **"Statistical projection, not an official forecast."**

---

### Algorithm Choice: Why Holt-Winters instead of ARIMA?

When selecting an explainable forecasting algorithm, we compared **ARIMA** (Autoregressive Integrated Moving Average) and **Holt-Winters Triple Exponential Smoothing**:

| Criteria | ARIMA $(p, d, q) \times (P, D, Q)_m$ | Holt-Winters Exponential Smoothing |
| :--- | :--- | :--- |
| **Mechanics** | Iterative numerical search over lag polynomials; AIC/BIC minimization. | Recursive state equations updating Level ($l_t$), Trend ($b_t$), and Seasonality ($s_t$). |
| **Stability on Shocks** | Fragile. Macro shocks (e.g. COVID-19 spike in April 2020) cause stationarity test failures or non-invertible MA roots. | Robust. Closed-form exponential decay naturally incorporates shocks while dampening their long-term distortion. |
| **Latency & Dependencies**| Heavy (`scipy`/`statsmodels`, slow optimization loops). | Zero heavy dependencies. Microsecond execution in pure Python/NumPy. |
| **Pedagogical Clarity** | Difficult for non-statisticians to debug or explain. | Intuitive decomposition: *Baseline + (Horizon $\times$ Slope) + Monthly Seasonal Swing*. |

#### The Holt-Winters Recurrence Relations
For monthly data with yearly seasonality ($m = 12$):
1. **Level**: $l_t = \alpha (y_t - s_{t-m}) + (1 - \alpha)(l_{t-1} + b_{t-1})$
2. **Trend**: $b_t = \beta (l_t - l_{t-1}) + (1 - \beta)b_{t-1}$
3. **Seasonality**: $s_t = \gamma (y_t - l_t) + (1 - \gamma)s_{t-m}$
4. **Point Forecast ($h$ months ahead)**: $\hat{y}_{t+h} = l_t + h \cdot b_t + s_{t+h-m}$

---

### Plain-English Guide to Confidence Intervals (80% vs. 95%)

A common mistake in ML is treating point predictions ($\hat{y}$) as certainties. In time-series forecasting, uncertainty **fans out** as the horizon $h$ increases.

#### What does an 80% Confidence Interval actually mean?
Assuming the historical residual error distribution holds, if we ran this projection across 100 historical periods, the true observed rate would fall between the lower and upper bounds in **80 of those 100 periods** (leaving a 10% chance of exceeding the upper bound and a 10% chance of dipping below the lower bound).
- **Z-score multiplier**: $z_{0.10} \approx 1.282$

#### What does a 95% Confidence Interval mean?
A 95% interval is wider and more conservative. The true rate would fall within these bounds in **95 out of 100 periods** (only a 2.5% chance in each tail).
- **Z-score multiplier**: $z_{0.025} \approx 1.960$

#### Why do the confidence bounds expand over time?
In step $h=1$ (next month), uncertainty is driven primarily by one-step random noise ($\sigma$). But in step $h=12$ (one year out), error in the estimated slope ($b_t$) compounds over 12 consecutive months.
We calculate multi-step prediction standard error as:
$$\sigma_h = \sigma \sqrt{1 + \sum_{j=1}^{h-1} (1 + j \cdot \beta)^2}$$
This mathematical fanning-out prevents the user from being lulled into false precision.

---

## 3. Self-Healing SQL Reflection Loops & Failure Dynamics

### The Anatomy of Reflection
In traditional LLM pipelines, if a generated SQL query produces a database syntax error or returns zero rows, the user is greeted with an ugly stack trace or an empty chart.

A **reflection loop** intercepts failure, constructs a structured diagnostic prompt containing:
1. The original question
2. The exact SQL query that was attempted
3. The specific error message or warning (e.g. SQLite compiler error or empty result notification)
4. Relevant schema hints

The LLM is then prompted to reflect on its mistake and generate an updated query.

```
[User Query] ──> [Initial SQL Generation]
                        │
                        ▼
               [Execute in SQLite]
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
    [Success: Rows > 0]       [Failure / 0 Rows]
         │                             │
    [Render UI]             [Attempt < MAX_RETRIES (2)?]
                                 ├── Yes ──> [Feedback Error to LLM] ──> (Loop back)
                                 └── No  ──> [Clean Safe Fallback / Refusal]
```

---

### Why Capping Retries (at 2) is Critical

Why not let the agent retry 5 or 10 times until it gets it right?

#### 1. Latency & Token Economics
Every reflection loop requires an external LLM round-trip (~1.5–3.0 seconds). A 5-retry loop creates a 15-second delay where the web interface appears frozen.

#### 2. The Hallucination Spiral ("Trying Harder" in the Wrong Direction)
Empirical observation in LLM evaluation reveals that if a model cannot correct its SQL error within **two attempts**, further retries almost always make the problem worse:
* On attempt 1, the model makes a simple typo: `WHERE region = 'Vic'`
* On attempt 2, with error feedback, the model fixes it: `WHERE region = 'Victoria'`
* But if the query failed because the underlying concept doesn't exist (e.g. asking for "astronaut employment"), a model forced to retry 4 or 5 times will begin **hallucinating fictitious tables, writing convoluted nested subqueries, or inventing synthetic math** to produce *some* output rather than admitting it cannot fulfill the request.

---

### Empirical Observations: What Reflection Fixes vs. Where it Fails

During our evaluation suite tests across 25 benchmark queries, we logged every reflection attempt:

| Test Case | Initial Error Trigger | Reflection Attempt 1 Action | Final Result |
| :--- | :--- | :--- | :--- |
| **1. Regional Alias Mismatch** (`"unemployment rate in Vic for 2024"`) | Query executed but returned **0 rows** because SQLite stores `'Victoria'`, not `'Vic'`. | Reflection recognized `'Vic'` as an uncanonical alias, replaced it with `'Victoria'`, and re-executed. | ✅ **Self-Healed** (12 rows returned in 1 retry). |
| **2. Column Name Mismatch** (`"jobless rate in NSW since 2023"`) | SQLite threw error: `no such column: jobless_rate`. | Reflection inspected schema context, mapped `jobless_rate` to `value AS unemployment_rate WHERE metric_name = 'Unemployment rate'`. | ✅ **Self-Healed** (43 rows returned in 1 retry). |
| **3. Geographic Scope Mismatch** (`"youth unemployment in Victoria"`) | Joined on `y.region = 'Victoria'`, returning 0 rows because Table 12 youth data is national. | Reflection detected empty result, relaxed youth region constraint to `y.region = 'Australia'` while keeping headline region as Victoria. | ✅ **Self-Healed** (79 rows returned in 1 retry). |
| **4. Unrepairable Query** (`"astronaut employment in Sydney"`) | AST Validator blocked query because table `astronaut_space_force` is not in allowlist. | Reflection recognized query asks for out-of-scope domain; retries reached cap (2). | 🛡️ **Clean Fallback** (Validation error preserved; zero hallucinated data). |

### The Critical Rule: Never Paper Over Bad Queries
Notice Test Case 4 above: if an unrepairable query exhausts its retries, the reflection loop **must fail cleanly**. 

A naive fallback that defaults to returning general Australia unemployment data would "paper over" the error, deceiving the user into believing their question was answered. In safety-critical data engineering, **an explicit, honest failure is infinitely superior to a fabricated success.**

---

## Summary Checklist for Developers

When building similar systems in production:
1. **Always normalize cross-table dimensions** during ingestion so join keys align (`date`, `region`).
2. **Explicitly document join paths and cardinalities** in the schema context prompt.
3. **Never allow LLMs to calculate numbers or forecast the future unconstrained.**
4. **Use deterministic, bounded statistical models (Holt-Winters)** with confidence bands for forward projections.
5. **Always cap reflection retries (at 1–2)** and log every repair attempt in telemetry.
6. **Prefer clean refusal over silent fallback** when queries are unrepairable.
