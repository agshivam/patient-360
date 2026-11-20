"""Patient-360 quality report: a Streamlit app over synthetic hospital data (Synthea).

Run locally:  streamlit run app/streamlit_app.py
The app reads small Parquet files from app_data/, so it needs no database and no raw data.
"""
from pathlib import Path

import altair as alt
import duckdb
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"

st.set_page_config(page_title="Patient-360 quality report", layout="wide")


@st.cache_data(show_spinner=False)
def load(name: str):
    path = (DATA_DIR / f"{name}.parquet").as_posix()
    return duckdb.sql(f"SELECT * FROM read_parquet('{path}')").df()


if not (DATA_DIR / "agg_kpis.parquet").exists():
    st.error("No report data found. Run: python scripts/export_app_data.py")
    st.stop()

kpis = load("agg_kpis").iloc[0]
by_year_class = load("agg_encounters_by_year_class")
admissions = load("agg_admissions_by_year")
disorders = load("agg_top_disorders")
age_gender = load("agg_age_gender")
payers = load("agg_payer_cost")
checks = load("agg_quality_checks")
masked = load("masked_patients")

st.title("Patient-360 quality report")
st.caption(
    "Synthetic patients generated with Synthea. No real patient data is used. "
    "Names and SSNs are masked, as an analyst would see them."
)

# Sidebar filter: years shown in the activity and admissions views.
years = sorted(by_year_class["year"].unique())
if len(years) > 1:
    recent_start = next(y for y in years if y >= years[-1] - 15)
    first, last = st.sidebar.select_slider(
        "Years to show", options=years, value=(recent_start, years[-1])
    )
else:
    first, last = years[0], years[0]
st.sidebar.caption("The filter applies to the Activity and Admissions tabs.")

cols = st.columns(5)
cols[0].metric("Patients", f"{int(kpis.patients):,}")
cols[1].metric("Encounters", f"{int(kpis.encounters):,}")
cols[2].metric("Hospital stays", f"{int(kpis.admissions):,}")
cols[3].metric("30-day readmission rate", f"{kpis.readmission_rate_pct}%")
cols[4].metric("Average stay", f"{kpis.avg_stay_days} days")

tab_activity, tab_adm, tab_cond, tab_cost, tab_quality, tab_mask = st.tabs(
    ["Activity", "Admissions", "Conditions", "Costs", "Data quality", "Masked patients"]
)

with tab_activity:
    st.subheader("Encounters per year, by type")
    sel = by_year_class[(by_year_class["year"] >= first) & (by_year_class["year"] <= last)]
    chart = (
        alt.Chart(sel)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("encounters:Q", title="Encounters"),
            color=alt.Color("encounter_class:N", title="Type"),
            tooltip=["year", "encounter_class", "encounters"],
        )
    )
    st.altair_chart(chart, width="stretch")

with tab_adm:
    sel = admissions[(admissions["year"] >= first) & (admissions["year"] <= last)]
    left, right = st.columns(2)
    with left:
        st.subheader("Hospital stays per year")
        st.altair_chart(
            alt.Chart(sel)
            .mark_bar(color="#1F6F8B")
            .encode(x=alt.X("year:O", title="Year"), y=alt.Y("admissions:Q", title="Stays"),
                    tooltip=["year", "admissions", "readmissions"]),
            width="stretch",
        )
    with right:
        st.subheader("30-day readmission rate (%)")
        st.altair_chart(
            alt.Chart(sel)
            .mark_line(point=True, color="#1F6F8B")
            .encode(x=alt.X("year:O", title="Year"),
                    y=alt.Y("readmission_rate_pct:Q", title="Readmitted within 30 days (%)"),
                    tooltip=["year", "readmission_rate_pct", "readmissions"]),
            width="stretch",
        )
    st.caption("A readmission is a new hospital stay that starts within 30 days of the patient's previous discharge.")

with tab_cond:
    left, right = st.columns(2)
    with left:
        st.subheader("Most common disorders")
        st.altair_chart(
            alt.Chart(disorders)
            .mark_bar(color="#1F6F8B")
            .encode(x=alt.X("patients:Q", title="Patients"),
                    y=alt.Y("disorder:N", sort="-x", title=None),
                    tooltip=["disorder", "patients"]),
            width="stretch",
        )
    with right:
        st.subheader("Living patients by age and gender")
        st.altair_chart(
            alt.Chart(age_gender)
            .mark_bar()
            .encode(x=alt.X("age_band:N", title="Age", sort=["0-17", "18-39", "40-64", "65+"]),
                    y=alt.Y("patients:Q", title="Patients"),
                    color=alt.Color("gender:N", title="Gender"),
                    xOffset="gender:N",
                    tooltip=["age_band", "gender", "patients"]),
            width="stretch",
        )

with tab_cost:
    st.subheader("Claim cost by payer")
    st.altair_chart(
        alt.Chart(payers)
        .mark_bar(color="#1F6F8B")
        .encode(x=alt.X("claim_cost:Q", title="Total claim cost (USD)"),
                y=alt.Y("payer:N", sort="-x", title=None),
                tooltip=["payer", "encounters", "claim_cost", "payer_paid"]),
        width="stretch",
    )
    st.dataframe(payers, width="stretch", hide_index=True)

with tab_quality:
    st.subheader("Data quality checks")
    failed = int((checks["status"] == "Failed").sum())
    if failed == 0:
        st.success(f"All {len(checks)} checks passed.")
    else:
        st.error(f"{failed} of {len(checks)} checks failed.")
    st.dataframe(checks, width="stretch", hide_index=True)
    st.caption("These checks run every time the data is rebuilt. Later versions will inject bad data on purpose to prove they catch it.")

with tab_mask:
    st.subheader("What an analyst sees")
    st.dataframe(masked, width="stretch", hide_index=True)
    st.caption("Names show only an initial, and the SSN shows only its last four digits. Clinicians with the right role will see full values in the Snowflake version.")
