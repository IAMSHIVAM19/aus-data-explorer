"""
ABS Labour Force Data Ingestion Pipeline
Source: Australian Bureau of Statistics (ABS), Catalogue 6202.0, Table 010
"Labour force status by Sex, State and Territory - Trend, Seasonally adjusted and Original"
URL: https://www.abs.gov.au/statistics/labour/employment-and-unemployment/labour-force-australia/
Data period: February 1978 to July 2026
"""

import os
import sqlite3
import pandas as pd
import openpyxl
from datetime import datetime

RAW_FILE_10 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/raw/62020010.xlsx"))
RAW_FILE_12 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/raw/62020012.xlsx"))
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
DB_PATH = os.path.join(DB_DIR, "aus_labour_force.db")
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
SAMPLE_CSV_PATH = os.path.join(PROCESSED_DIR, "aus_labour_force_sample.csv")


def clean_description(desc: str):
    """
    Parses hierarchical ABS descriptions into (metric, sex, region).
    
    Design Note:
    - Table 010 has 3 parts: 'Employed total ; Persons ; > New South Wales ;'
      giving metric='Employed total', sex='Persons', region='New South Wales'.
    - Table 012 has 2 parts: 'Unemployment rate ; Persons ;' with no region.
      ABS Table 012 is published exclusively for Australia at the national level.
      We explicitly map missing region to 'Australia' so that downstream join keys
      (region + date) align consistently across tables.
    """
    parts = [p.strip().lstrip('>').strip() for p in desc.split(';') if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1], "Australia"
    return parts[0] if parts else "Unknown", "Persons", "Australia"


def parse_workbook(file_path: str, default_cohort: str = "Total"):
    """
    Generic parser for ABS time-series workbooks (Index + Data sheets).
    Reuses header extraction and date normalization across Table 010 and Table 012.
    """
    print(f"Loading workbook: {file_path}")
    wb = openpyxl.load_workbook(file_path, data_only=True)

    index_sheet = wb['Index']
    series_meta = {}
    for i, r in enumerate(index_sheet.iter_rows(values_only=True)):
        if i > 9 and r[0] and r[4]:
            raw_desc = str(r[0]).strip()
            metric, sex, region = clean_description(raw_desc)
            series_type = str(r[3]).strip() if r[3] else "Original"
            series_id = str(r[4]).strip()
            unit = str(r[8]).strip() if len(r) > 8 and r[8] else ""
            
            series_meta[series_id] = {
                "series_id": series_id,
                "metric_name": metric,
                "sex": sex,
                "region": region,
                "series_type": series_type,
                "unit": unit,
                "cohort": default_cohort
            }

    print(f"  Indexed {len(series_meta)} series definitions for {default_cohort}.")

    records = []
    data_sheets = [s for s in ['Data1', 'Data2', 'Data3'] if s in wb.sheetnames]

    for sname in data_sheets:
        sheet = wb[sname]
        print(f"  Processing sheet: {sname}...")
        
        rows_iter = sheet.iter_rows(values_only=True)
        for _ in range(9):
            next(rows_iter)
        
        series_id_row = next(rows_iter)
        col_series = []
        for col_idx, cell in enumerate(series_id_row):
            if col_idx == 0:
                col_series.append("Date")
            elif cell and str(cell).strip() in series_meta:
                col_series.append(str(cell).strip())
            else:
                col_series.append(None)

        for row in rows_iter:
            date_val = row[0]
            if not date_val:
                continue
            
            if isinstance(date_val, datetime):
                date_str = date_val.strftime("%Y-%m-%d")
                year = date_val.year
                month = date_val.month
            else:
                try:
                    dt = pd.to_datetime(date_val)
                    date_str = dt.strftime("%Y-%m-%d")
                    year = dt.year
                    month = dt.month
                except Exception:
                    continue

            for col_idx in range(1, len(row)):
                sid = col_series[col_idx]
                val = row[col_idx]
                if sid and val is not None and isinstance(val, (int, float)):
                    meta = series_meta[sid]
                    records.append({
                        "region": meta["region"],
                        "date": date_str,
                        "year": year,
                        "month": month,
                        "metric_name": meta["metric_name"],
                        "sex": meta["sex"],
                        "series_type": meta["series_type"],
                        "unit": meta["unit"],
                        "value": round(float(val), 2),
                        "series_id": sid
                    })

    return pd.DataFrame(records)


def run_ingest():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 1. Ingest Table 010 (General Labour Force across All Regions)
    df_main = parse_workbook(RAW_FILE_10, default_cohort="Total")
    print(f"Table 010 observations: {len(df_main):,}")

    # 2. Ingest Table 012 (Youth Labour Force 15-19 Cohort)
    df_youth = pd.DataFrame()
    if os.path.exists(RAW_FILE_12):
        df_youth = parse_workbook(RAW_FILE_12, default_cohort="Youth (15-19)")
        print(f"Table 012 (Youth) observations: {len(df_youth):,}")
    else:
        print(f"Warning: Table 12 file not found at {RAW_FILE_12}")

    # 3. Write to SQLite
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Base table 1: labour_force (Table 010)
    df_main.to_sql("labour_force", conn, if_exists="replace", index=False)
    print("Creating indexes on labour_force table...")
    cur.execute("CREATE INDEX idx_lf_metric_reg_date ON labour_force(metric_name, region, date);")
    cur.execute("CREATE INDEX idx_lf_metric_date ON labour_force(metric_name, date);")
    cur.execute("CREATE INDEX idx_lf_year ON labour_force(year);")
    cur.execute("CREATE INDEX idx_lf_region ON labour_force(region);")

    # Canonical view: labour_force_monthly
    print("Creating canonical view: labour_force_monthly...")
    cur.execute("""
        CREATE VIEW labour_force_monthly AS
        SELECT 
            region, 
            date, 
            year, 
            month, 
            metric_name, 
            value,
            unit
        FROM labour_force
        WHERE sex = 'Persons' AND series_type = 'Seasonally Adjusted';
    """)

    # Pivoted view: regional_unemployment
    print("Creating summary view: regional_unemployment...")
    cur.execute("""
        CREATE VIEW regional_unemployment AS
        SELECT 
            region, 
            date, 
            year, 
            month, 
            value AS unemployment_rate
        FROM labour_force
        WHERE metric_name = 'Unemployment rate' 
          AND sex = 'Persons' 
          AND series_type = 'Seasonally Adjusted';
    """)

    # Base table 2 & canonical view for Table 012 (Youth)
    if not df_youth.empty:
        df_youth.to_sql("youth_labour_force", conn, if_exists="replace", index=False)
        print("Creating indexes on youth_labour_force table...")
        cur.execute("CREATE INDEX idx_ylf_metric_date ON youth_labour_force(metric_name, date);")
        cur.execute("CREATE INDEX idx_ylf_year ON youth_labour_force(year);")
        cur.execute("CREATE INDEX idx_ylf_region ON youth_labour_force(region);")

        # Canonical view: youth_unemployment (pre-filtered to Seasonally Adjusted Persons for clean joins)
        print("Creating canonical view: youth_unemployment...")
        cur.execute("""
            CREATE VIEW youth_unemployment AS
            SELECT 
                region, 
                date, 
                year, 
                month, 
                value AS youth_unemployment_rate
            FROM youth_labour_force
            WHERE metric_name = 'Unemployment rate' 
              AND sex = 'Persons' 
              AND series_type = 'Seasonally Adjusted';
        """)

    conn.commit()
    conn.close()
    print(f"Database successfully populated at {DB_PATH}")

    # 4. Save sample CSV
    sample_df = df_main[(df_main['sex'] == 'Persons') & (df_main['series_type'] == 'Seasonally Adjusted') & (df_main['year'] >= 2020)]
    sample_df.to_csv(SAMPLE_CSV_PATH, index=False)
    print(f"Saved audit sample CSV to {SAMPLE_CSV_PATH}")


if __name__ == "__main__":
    run_ingest()
