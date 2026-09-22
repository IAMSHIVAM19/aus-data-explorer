"""
Schema Context Builder for Aus Gov Data Explorer
Provides compact, highly descriptive schema definitions, canonical values,
and query generation guidelines to inject into LLM prompts.
"""

from typing import Dict, Any

CANONICAL_REGIONS = [
    "Australia",
    "New South Wales",
    "Victoria",
    "Queensland",
    "South Australia",
    "Western Australia",
    "Tasmania",
    "Northern Territory",
    "Australian Capital Territory"
]

REGION_ALIASES = {
    "nsw": "New South Wales",
    "vic": "Victoria",
    "qld": "Queensland",
    "sa": "South Australia",
    "wa": "Western Australia",
    "tas": "Tasmania",
    "nt": "Northern Territory",
    "act": "Australian Capital Territory",
    "national": "Australia",
    "aus": "Australia",
    "country": "Australia",
    "overall": "Australia"
}

CANONICAL_METRICS = [
    "Unemployment rate",
    "Participation rate",
    "Employed total",
    "Unemployed total",
    "Employment to population ratio",
    "Labour force total"
]

METRIC_ALIASES = {
    "unemployment rate": "Unemployment rate",
    "unemployment": "Unemployment rate",
    "jobless rate": "Unemployment rate",
    "employment rate": "Employment to population ratio",
    "employment ratio": "Employment to population ratio",
    "employment to population": "Employment to population ratio",
    "employment to population ratio": "Employment to population ratio",
    "participation rate": "Participation rate",
    "participation": "Participation rate",
    "workforce participation": "Participation rate",
    "jobs": "Employed total",
    "employed total": "Employed total",
    "employed": "Employed total",
    "employment": "Employed total",
    "unemployed total": "Unemployed total",
    "unemployed": "Unemployed total"
}

SCHEMA_PROMPT_CONTEXT = f"""
You are an expert SQLite data analyst translating natural language questions into single SQLite queries.

### Database Engine: SQLite

### Available Tables & Views:

1. View `labour_force_monthly` (RECOMMENDED DEFAULT for all general metrics):
   - Already filtered to Seasonally Adjusted, Persons (headline national/state metrics).
   - Columns:
     - `region` TEXT: One of {CANONICAL_REGIONS}
     - `date` TEXT: Format 'YYYY-MM-DD' (monthly: 1978-02-01 to 2026-07-01)
     - `year` INTEGER: e.g. 2024, 2023
     - `month` INTEGER: 1 to 12
     - `metric_name` TEXT: One of {CANONICAL_METRICS}
     - `value` REAL: Numeric observation value (e.g. 4.1 for 4.1% unemployment rate)
     - `unit` TEXT: 'Percent' for rates, '000' for totals

2. View `regional_unemployment` (Convenient shortcut when querying specifically unemployment rate):
   - Columns:
     - `region` TEXT
     - `date` TEXT ('YYYY-MM-DD')
     - `year` INTEGER
     - `month` INTEGER
     - `unemployment_rate` REAL

3. View `youth_unemployment` (ABS Catalogue 6202.0 Table 012 - 15 to 19 year old youth cohort):
   - Already filtered to Seasonally Adjusted, Persons.
   - Note: Published at National level (`region = 'Australia'`).
   - Columns:
     - `region` TEXT ('Australia')
     - `date` TEXT ('YYYY-MM-DD')
     - `year` INTEGER
     - `month` INTEGER
     - `youth_unemployment_rate` REAL (e.g. 15.69 for 15.69%)

4. Table `labour_force` (Full raw table when sex or series_type breakdown is requested):
   - Columns: `region`, `date`, `year`, `month`, `metric_name`, `sex` ('Persons', 'Males', 'Females'), `series_type` ('Seasonally Adjusted', 'Trend', 'Original'), `unit`, `value`

### Cross-Dataset / Multi-Table Joins:
- To compare Youth Unemployment against Headline (Overall) Unemployment:
  - Join `youth_unemployment` with `labour_force_monthly` ON `date` (and `region` when both are Australia):
    ```sql
    SELECT 
        y.date, 
        y.youth_unemployment_rate, 
        h.value AS headline_unemployment_rate,
        ROUND(y.youth_unemployment_rate - h.value, 2) AS unemployment_gap
    FROM youth_unemployment y
    JOIN labour_force_monthly h ON y.date = h.date AND y.region = h.region
    WHERE h.metric_name = 'Unemployment rate' AND y.year >= 2020
    ORDER BY y.date ASC;
    ```
- When comparing youth unemployment with a specific state (e.g. Victoria), remember Table 12 youth data is national:
  ```sql
  SELECT 
      y.date, 
      y.youth_unemployment_rate AS national_youth_rate, 
      h.value AS victoria_headline_rate
  FROM youth_unemployment y
  JOIN labour_force_monthly h ON y.date = h.date
  WHERE h.metric_name = 'Unemployment rate' AND h.region = 'Victoria' AND y.year >= 2020
  ORDER BY y.date ASC;
  ```

### Rules & Dialect Guidelines:
- Return ONLY a single SQL SELECT query inside a ```sql ... ``` code block.
- DO NOT generate INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, or multiple statements.
- Default to `metric_name = 'Unemployment rate'` if the question asks about unemployment without specifying.
- Use exact canonical region names (e.g. use 'New South Wales' not 'NSW').
- For state-only rankings or comparisons, exclude national aggregate with `region != 'Australia'` unless Australia is explicitly requested.
- For time series, always `ORDER BY date ASC`.
- For rankings / 'highest' / 'lowest', `ORDER BY value DESC` (or ASC) `LIMIT N`.
- When asked for a specific year's average, use `AVG(value)` grouped by region or metric.
- Limit results to at most 1000 rows.
"""


def get_schema_context() -> str:
    return SCHEMA_PROMPT_CONTEXT.strip()


def normalize_region_name(raw_text: str) -> str:
    cleaned = raw_text.strip().lower()
    return REGION_ALIASES.get(cleaned, raw_text.strip())
