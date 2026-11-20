# How to run Patient-360

Follow these steps in order. Each step says what you should see, so you know it worked.

## Before you start

You need three tools. Check each one in a terminal (Windows: PowerShell or Git Bash).

| Tool | Check with | Needed version | If missing |
| --- | --- | --- | --- |
| Python | `python --version` | 3.10 or newer | https://www.python.org/downloads |
| Java | `java -version` | 11 or newer | Install Temurin from https://adoptium.net, then reopen the terminal |
| Git | `git --version` | any | https://git-scm.com/downloads |

Java is only needed for step 3 (generating patients). You can skip steps 3 and 4 and still run the report on the sample data.

## Quick start: see the report in 5 minutes

```bash
git clone https://github.com/agshivam/patient-360.git
cd patient-360
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Your browser opens the report at http://localhost:8501 with the small sample data that is stored in `app_data/`.

## Full run: build everything from new data

### 1. Set up

```bash
cd patient-360
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

You should see the install finish without red error lines.

### 2. Choose how many patients

1,000 patients is a good size: about 5 to 10 minutes to generate and about 50,000 encounters. Use 200 for a fast test.

### 3. Generate synthetic patients (needs Java)

```bash
python scripts/generate_synthea.py --patients 1000
```

The first run downloads Synthea. You should see CSV files appear in `data/raw/csv/`, including `patients.csv` and `encounters.csv`.

### 4. Load the raw layer

```bash
python scripts/load_raw.py
```

You should see a row count for each of 7 tables, then "Done".

### 5. Build and test with dbt

```bash
cd dbt
dbt build
cd ..
```

You should see `PASS=39` (or more) and `ERROR=0` at the end. If a test fails, read its name: it says which rule broke. Do not delete the test.

Optional, to browse the model lineage graph:

```bash
cd dbt
dbt docs generate
dbt docs serve
```

### 6. Export the report data

```bash
python scripts/export_app_data.py
```

You should see eight lines starting with "exported app_data/".

### 7. Open the report

```bash
streamlit run app/streamlit_app.py
```

Click through all six tabs. The numbers now reflect the patients you generated.

### 8. Save your work to GitHub

```bash
git add app_data
git commit -m "Refresh report data with 1,000 patients"
git push
```

If the app is deployed on Streamlit Community Cloud, it updates itself within a minute.

## Deploy the report for free

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Choose **Create app**.
3. Repo: `agshivam/patient-360`. Branch: `main`. Main file: `app/streamlit_app.py`.
4. Click **Deploy**. Copy the link it gives you.

Free apps sleep when nobody visits. The first load after sleeping takes a little longer.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `java: command not found` | Install Java 11 or newer (see the table at the top), then reopen the terminal |
| `No CSV files found in data/raw/csv` | Run step 3 first |
| `No database found` | Run step 4, then step 5 |
| `No aggregate tables in the marts schema` | Run `dbt build` (step 5) |
| `No report data found` | Run step 6 |
| `dbt: command not found` | Activate the virtual environment, then run `pip install -r requirements-dev.txt` |
| A dbt test fails | Read the test name in the output. It tells you which rule broke and on which model |
| The app shows old numbers | Stop it with Ctrl+C, run step 6 again, then start it again |

## What each folder is

| Path | Purpose |
| --- | --- |
| `scripts/` | Generate patients, load the raw layer, export report data |
| `dbt/models/staging/` | Typed views over the raw tables |
| `dbt/models/marts/` | Star schema and report summary tables |
| `dbt/tests/` | Tests written in SQL |
| `app/` | The Streamlit report |
| `app_data/` | Small Parquet files the report reads |
| `data/` | Local only (not in Git): raw CSV files and the DuckDB database |
