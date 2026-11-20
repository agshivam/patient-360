# Patient-360

A healthcare data platform built on **synthetic** patients (Synthea). No real patient data is used anywhere.

The goal is to mirror how a hospital using Epic organizes data: operational tables first (Clarity style), then a reporting star schema (Caboodle style), then reports. This repo is built in stages.

| Stage | Status |
|---|---|
| 1. Generate synthetic patients, load into DuckDB, build marts, publish a Streamlit report | Done in this starter |
| 2. dbt models and tests on DuckDB | Next |
| 3. Move to Snowflake (raw layer, dbt, masking policies, role-based access) | Week 2 |
| 4. Inject dirty data (duplicate patients, late labs, changed columns) and merge duplicates with fuzzy matching | Week 2 to 3 |
| 5. FHIR in MongoDB, loaded with Airbyte | Week 3 |

## Run it on your computer

You need Python 3.10 or newer and Java 11 or newer (check with `java -version`; if missing, install Temurin from https://adoptium.net).

```bash
git clone https://github.com/agshivam/patient-360.git
cd patient-360

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

python scripts/generate_synthea.py --patients 1000   # about 5 to 10 minutes, downloads Synthea once
python scripts/build_duckdb.py                        # loads CSVs, builds tables, exports app_data/
streamlit run app/streamlit_app.py                    # opens the report in your browser
```

`app_data/` already holds a small sample, so you can run the last command straight away to see the report.

## What each part does

- `scripts/generate_synthea.py` downloads Synthea and creates the patient CSV files in `data/raw/csv/`.
- `sql/marts.sql` holds the SQL for the cleaned tables (`dim_patient`, `fact_encounter`, `fact_condition`, `fact_admission`) and the small summary tables the app reads.
- `scripts/build_duckdb.py` loads the raw files as text, runs `sql/marts.sql`, and exports the summary tables as Parquet into `app_data/`.
- `app/streamlit_app.py` is the report. It reads only `app_data/`, so it needs no database and no raw data.

## Publish the report for free (Streamlit Community Cloud)

1. Push this repo to GitHub as a **public** repo named `patient-360`.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Choose **Create app**, pick the repo, set the main file to `app/streamlit_app.py`, and deploy.
4. Copy the app link into your portfolio.

Free apps can go to sleep when nobody visits and wake when someone opens the link.

## Decisions

- **Raw data loaded as text.** Every raw column is text and each cast is explicit in `sql/marts.sql`, so a changed source column fails loudly instead of silently changing a number.
- **Names and SSNs masked in the marts.** Analysts only ever see initials and the last four SSN digits.
- **The app reads small Parquet files.** The report keeps working after any warehouse trial ends, and it deploys without the raw data.
