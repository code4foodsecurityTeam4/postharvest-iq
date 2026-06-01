"""
dashboard/streamlit_app.py

PostHarvest IQ — operations dashboard for WFP officers.

Shows the current sell/store recommendation for every district x crop,
pulled live from the deployed FastAPI service, with an offline fallback
sample so the dashboard always renders during a demo even if the API is
asleep or unreachable.

Run locally:
    streamlit run dashboard/streamlit_app.py
"""

import datetime as _dt

import pandas as pd
import requests
import streamlit as st

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
API_BASE = "https://postharvest-iq.onrender.com"
SUMMARY_ENDPOINT = f"{API_BASE}/dashboard/summary"
REQUEST_TIMEOUT = 20  # Render free tier can be slow to wake from sleep

DECISION_STYLE = {
    "STORE":        ("#1b7837", "Store"),
    "SELL_NOW":     ("#b2182b", "Sell now"),
    "SELL_PARTIAL": ("#d9820b", "Sell half, store half"),
    "UNAVAILABLE":  ("#777777", "Unavailable"),
}

# Offline fallback — a representative snapshot used only if the live API
# cannot be reached. Clearly labelled as sample data in the UI.
FALLBACK_SUMMARY = [
    {"district": "Sagnarigu", "crop": "Maize",   "decision": "SELL_NOW", "net_total": -180.0, "current_price": 538.46, "forecast_price": 495.38},
    {"district": "Sagnarigu", "crop": "Millet",  "decision": "SELL_NOW", "net_total": -64.0,  "current_price": 180.00, "forecast_price": 165.60},
    {"district": "Sagnarigu", "crop": "Sorghum", "decision": "SELL_NOW", "net_total": -248.0, "current_price": 741.20, "forecast_price": 681.90},
    {"district": "Tolon",     "crop": "Maize",   "decision": "SELL_NOW", "net_total": -180.0, "current_price": 538.46, "forecast_price": 495.38},
    {"district": "Tolon",     "crop": "Millet",  "decision": "SELL_NOW", "net_total": -64.0,  "current_price": 180.00, "forecast_price": 165.60},
    {"district": "Tolon",     "crop": "Sorghum", "decision": "SELL_NOW", "net_total": -248.0, "current_price": 741.20, "forecast_price": 681.90},
    {"district": "Kumbungu",  "crop": "Maize",   "decision": "SELL_NOW", "net_total": -150.0, "current_price": 510.00, "forecast_price": 469.20},
    {"district": "Kumbungu",  "crop": "Millet",  "decision": "SELL_NOW", "net_total": -64.0,  "current_price": 180.00, "forecast_price": 165.60},
    {"district": "Kumbungu",  "crop": "Sorghum", "decision": "SELL_NOW", "net_total": -240.0, "current_price": 720.00, "forecast_price": 662.40},
    {"district": "Tamale",    "crop": "Maize",   "decision": "SELL_NOW", "net_total": -180.0, "current_price": 538.46, "forecast_price": 495.38},
    {"district": "Tamale",    "crop": "Millet",  "decision": "SELL_NOW", "net_total": -64.0,  "current_price": 180.00, "forecast_price": 165.60},
    {"district": "Tamale",    "crop": "Sorghum", "decision": "SELL_NOW", "net_total": -248.0, "current_price": 741.20, "forecast_price": 681.90},
]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_summary():
    """
    Return (rows, source) where source is 'live' or 'offline'.
    Falls back to the sample snapshot if the API can't be reached.
    """
    try:
        resp = requests.get(SUMMARY_ENDPOINT, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json().get("summary", [])
        if rows:
            return rows, "live"
        return FALLBACK_SUMMARY, "offline"
    except Exception:
        return FALLBACK_SUMMARY, "offline"


def decision_badge(decision: str) -> str:
    color, label = DECISION_STYLE.get(decision, DECISION_STYLE["UNAVAILABLE"])
    return (
        f"<span style='background:{color};color:#fff;padding:3px 10px;"
        f"border-radius:4px;font-size:0.85rem;font-weight:600;'>{label}</span>"
    )


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="PostHarvest IQ — Operations Dashboard",
    page_icon="🌾",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1100px;}
      h1 {font-weight: 700; letter-spacing: -0.5px;}
      .stDataFrame {border: 1px solid #e6e6e6;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌾 PostHarvest IQ")
st.caption(
    "Sell-or-store decision intelligence for Northern Ghana cereal farmers — "
    "operations view"
)

rows, source = load_summary()
df = pd.DataFrame(rows)

# Source + provenance banner
col_a, col_b = st.columns([3, 1])
with col_a:
    if source == "live":
        st.success(f"Live data from API · refreshed {_dt.datetime.now():%H:%M:%S}")
    else:
        st.warning(
            "Showing sample snapshot — live API not reachable. "
            "Figures are representative, not live."
        )
with col_b:
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()

st.info(
    "Recommendations use a documented seasonal price model. The trained "
    "ML pipeline (XGBoost + LSTM) is built and validated; live forecasting "
    "awaits price data past 2023.",
    icon="ℹ️",
)

if df.empty:
    st.error("No data available.")
    st.stop()

# --------------------------------------------------------------------------
# Headline metrics
# --------------------------------------------------------------------------
def _decision_count(d):
    return int((df["decision"] == d).sum()) if "decision" in df else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("District × crop pairs", len(df))
m2.metric("Store", _decision_count("STORE"))
m3.metric("Sell now", _decision_count("SELL_NOW"))
m4.metric("Sell partial", _decision_count("SELL_PARTIAL"))

st.divider()

# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
f1, f2 = st.columns(2)
districts = ["All"] + sorted(df["district"].dropna().unique().tolist())
crops = ["All"] + sorted(df["crop"].dropna().unique().tolist())
sel_district = f1.selectbox("District", districts)
sel_crop = f2.selectbox("Crop", crops)

view = df.copy()
if sel_district != "All":
    view = view[view["district"] == sel_district]
if sel_crop != "All":
    view = view[view["crop"] == sel_crop]

# --------------------------------------------------------------------------
# Recommendation table (rendered as HTML for the coloured badges)
# --------------------------------------------------------------------------
st.subheader("Current recommendations")

def _fmt_cedis(v):
    try:
        return f"GHS {round(float(v)):,}"
    except (TypeError, ValueError):
        return "—"

rows_html = []
for _, r in view.iterrows():
    rows_html.append(
        "<tr>"
        f"<td style='padding:8px 12px;'>{r.get('district','')}</td>"
        f"<td style='padding:8px 12px;'>{r.get('crop','')}</td>"
        f"<td style='padding:8px 12px;'>{decision_badge(r.get('decision',''))}</td>"
        f"<td style='padding:8px 12px;text-align:right;'>{_fmt_cedis(r.get('current_price'))}</td>"
        f"<td style='padding:8px 12px;text-align:right;'>{_fmt_cedis(r.get('forecast_price'))}</td>"
        f"<td style='padding:8px 12px;text-align:right;'>{_fmt_cedis(r.get('net_total'))}</td>"
        "</tr>"
    )

table_html = (
    "<table style='width:100%;border-collapse:collapse;font-size:0.95rem;'>"
    "<thead><tr style='border-bottom:2px solid #333;text-align:left;'>"
    "<th style='padding:8px 12px;'>District</th>"
    "<th style='padding:8px 12px;'>Crop</th>"
    "<th style='padding:8px 12px;'>Recommendation</th>"
    "<th style='padding:8px 12px;text-align:right;'>Current</th>"
    "<th style='padding:8px 12px;text-align:right;'>Forecast</th>"
    "<th style='padding:8px 12px;text-align:right;'>Net (20 bags)</th>"
    "</tr></thead><tbody>"
    + "".join(rows_html)
    + "</tbody></table>"
)
st.markdown(table_html, unsafe_allow_html=True)

st.caption(
    "Net is the modelled gain or loss on 20 bags after storage cost. "
    "A negative net means storing would lose money — sell now."
)

# --------------------------------------------------------------------------
# Price comparison chart
# --------------------------------------------------------------------------
if {"current_price", "forecast_price"}.issubset(view.columns) and not view.empty:
    st.subheader("Current vs forecast price")
    chart_df = view.copy()
    chart_df["label"] = chart_df["district"] + " · " + chart_df["crop"]
    chart_df = chart_df.set_index("label")[["current_price", "forecast_price"]]
    chart_df.columns = ["Current", "Forecast"]
    st.bar_chart(chart_df)