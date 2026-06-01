"""
PostHarvest IQ — WFP Officer Dashboard
Streamlit app for WFP officers and evaluators.
All data comes from the FastAPI backend.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os

# ── CONFIG ────────────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "https://postharvest-iq.onrender.com")

st.set_page_config(
    page_title="PostHarvest IQ — WFP Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── STYLES ────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
  }

  /* hide default streamlit header */
  #MainMenu, footer, header { visibility: hidden; }

  /* page background */
  .stApp { background-color: #F0F4F8; }

  /* sidebar */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D2137 0%, #1A3A5C 100%);
    border-right: none;
  }
  section[data-testid="stSidebar"] * { color: #E8F4FD !important; }
  section[data-testid="stSidebar"] .stSelectbox label { color: #9FC5E8 !important; }

  /* metric cards */
  .metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border-left: 4px solid #1A9DAA;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 16px;
  }
  .metric-card.green  { border-left-color: #00A878; }
  .metric-card.amber  { border-left-color: #E8940A; }
  .metric-card.red    { border-left-color: #C0392B; }
  .metric-card.navy   { border-left-color: #0D2137; }

  .metric-label {
    font-size: 12px;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }
  .metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #0D2137;
    line-height: 1.1;
  }
  .metric-sub {
    font-size: 13px;
    color: #9CA3AF;
    margin-top: 4px;
  }

  /* decision badges */
  .badge-store   { background:#E6F9F4; color:#00A878; border:1px solid #00A878; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .badge-partial { background:#FEF3E2; color:#E8940A; border:1px solid #E8940A; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .badge-sell    { background:#FEEAEA; color:#C0392B; border:1px solid #C0392B; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }

  /* storage card */
  .storage-card {
    background: white;
    border-radius: 10px;
    padding: 16px 20px;
    border: 1px solid #E5E7EB;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  }
  .storage-name { font-size:15px; font-weight:700; color:#0D2137; }
  .storage-meta { font-size:13px; color:#6B7280; margin-top:4px; }
  .storage-contact { font-size:13px; font-weight:600; color:#1A9DAA; margin-top:6px; }

  /* section headers */
  .section-title {
    font-size: 18px;
    font-weight: 700;
    color: #0D2137;
    margin-bottom: 4px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E5E7EB;
  }
  .section-sub {
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 20px;
  }

  /* top header bar */
  .top-header {
    background: linear-gradient(135deg, #0D2137 0%, #1A3A5C 60%, #1A9DAA 100%);
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .top-header-title {
    font-size: 26px;
    font-weight: 700;
    color: white;
    margin: 0;
  }
  .top-header-sub {
    font-size: 13px;
    color: #9FC5E8;
    margin-top: 4px;
  }
  .top-header-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 20px;
    padding: 6px 16px;
    color: white;
    font-size: 12px;
    font-weight: 600;
  }

  /* table styling */
  .dataframe { font-size: 13px !important; }

  /* alert box */
  .alert-box {
    background: #EAF7FA;
    border-left: 4px solid #1A9DAA;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 13px;
    color: #0D2137;
    margin-bottom: 16px;
  }

  /* wfp paragraph box */
  .wfp-box {
    background: linear-gradient(135deg, #0D2137, #1A3A5C);
    border-radius: 12px;
    padding: 24px 28px;
    color: white;
    font-size: 14px;
    line-height: 1.7;
    font-style: italic;
    margin-top: 16px;
  }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────
def api_get(path: str, timeout: int = 15):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def api_post(path: str, data: dict, timeout: int = 20):
    try:
        r = requests.post(f"{API_URL}{path}", json=data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def decision_badge(decision: str) -> str:
    if decision == "STORE":
        return '<span class="badge-store">STORE</span>'
    elif decision == "SELL_PARTIAL":
        return '<span class="badge-partial">SELL PARTIAL</span>'
    elif decision == "SELL_NOW":
        return '<span class="badge-sell">SELL NOW</span>'
    return f'<span>{decision}</span>'

def fmt_ghs(val) -> str:
    if val is None:
        return "—"
    return f"GHS {val:,.0f}"

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 PostHarvest IQ")
    st.markdown("**WFP Code4FoodSecurity 2026**")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Overview", "🔮 Price Forecast", "🏪 Storage Locations", "📋 Recommendations Log", "ℹ️ About"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**Filters**")

    district = st.selectbox(
        "District",
        ["Tamale", "Sagnarigu", "Tolon", "Kumbungu"],
        index=0
    )

    crop = st.selectbox(
        "Crop",
        ["Maize", "Millet", "Sorghum"],
        index=0
    )

    quantity = st.slider("Quantity (bags)", 5, 100, 20, 5)

    st.markdown("---")
    st.markdown(f"**API:** `{API_URL}`")
    st.markdown(f"**USSD:** `*384*33939#`")
    st.markdown(f"**Updated:** {datetime.now().strftime('%d %b %Y %H:%M')}")

# ── TOP HEADER ────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-header">
  <div>
    <p class="top-header-title">🌾 PostHarvest IQ</p>
    <p class="top-header-sub">WFP Officer Intelligence Dashboard · {district} · {crop}</p>
  </div>
  <span class="top-header-badge">WFP Code4FoodSecurity 2026</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════
if page == "📊 Overview":

    # ── Live recommendation ──────────────────────────────────────
    with st.spinner(f"Getting recommendation for {district} {crop}..."):
        rec = api_post("/recommendations/", {
            "crop": crop,
            "district": district,
            "quantity_bags": quantity,
            "language": "en"
        })

    if rec:
        decision = rec.get("decision", "—")
        current  = rec.get("current_price", 0)
        forecast = rec.get("forecast_price", 0)
        gain     = rec.get("expected_gain", 0)
        net_bag  = rec.get("net_per_bag", 0)
        net_tot  = rec.get("net_total", 0)
        storage  = rec.get("storage")
        method   = rec.get("method", "seasonal_estimate")

        # Top metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            color = "green" if decision == "STORE" else "amber" if decision == "SELL_PARTIAL" else "red"
            st.markdown(f"""
            <div class="metric-card {color}">
              <div class="metric-label">Recommendation</div>
              <div class="metric-value">{decision.replace("_"," ")}</div>
              <div class="metric-sub">{district} · {crop}</div>
            </div>""", unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card navy">
              <div class="metric-label">Current Market Price</div>
              <div class="metric-value">{fmt_ghs(current)}</div>
              <div class="metric-sub">per 100kg bag · Wholesale</div>
            </div>""", unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Forecast Price</div>
              <div class="metric-value">{fmt_ghs(forecast)}</div>
              <div class="metric-sub">Expected next month</div>
            </div>""", unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card green">
              <div class="metric-label">Net Gain ({quantity} bags)</div>
              <div class="metric-value">{fmt_ghs(net_tot)}</div>
              <div class="metric-sub">After storage & transport costs</div>
            </div>""", unsafe_allow_html=True)

        # Net return breakdown
        st.markdown("---")
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown('<p class="section-title">Net Return Calculation</p>', unsafe_allow_html=True)
            st.markdown('<p class="section-sub">How PostHarvest IQ calculates the farmer recommendation</p>', unsafe_allow_html=True)

            fig = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["Forecast Price", "− Current Price", "− Storage Cost", "− Transport", "Net per Bag"],
                y=[forecast, -current, -1.20, -2.00, 0],
                connector={"line": {"color": "#E5E7EB"}},
                decreasing={"marker": {"color": "#C0392B"}},
                increasing={"marker": {"color": "#00A878"}},
                totals={"marker": {"color": "#1A9DAA"}},
                text=[fmt_ghs(forecast), fmt_ghs(-current), "GHS 1.20", "GHS 2.00", fmt_ghs(net_bag)],
                textposition="outside",
            ))
            fig.update_layout(
                height=320,
                margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="DM Sans", size=12),
                showlegend=False,
                yaxis=dict(showgrid=True, gridcolor="#F3F4F6", zeroline=True, zerolinecolor="#E5E7EB"),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"""
            <div class="alert-box">
              <strong>Formula:</strong> Forecast Price − Current Price − Storage Cost (GHS 0.80 × 1.5 months) − Transport (GHS 2.00) = <strong>{fmt_ghs(net_bag)} per bag</strong><br>
              <strong>For {quantity} bags:</strong> {fmt_ghs(net_bag)} × {quantity} = <strong>{fmt_ghs(net_tot)}</strong><br>
              <strong>Forecast method:</strong> {method.replace("_", " ").title()}
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown('<p class="section-title">Nearest Storage Location</p>', unsafe_allow_html=True)
            st.markdown('<p class="section-sub">GPS-matched verified GCX warehouse</p>', unsafe_allow_html=True)

            if storage:
                st.markdown(f"""
                <div class="storage-card">
                  <div class="storage-name">🏪 {storage['name']}</div>
                  <div class="storage-meta">
                    📍 {storage['distance_km']} km from {district} district centre<br>
                    💰 GHS {storage['cost_per_bag']}/bag/month (Ghana Commodity Exchange rate)<br>
                    🌾 Accepts: Maize, Sorghum<br>
                    ✅ Verified · Active
                  </div>
                  <div class="storage-contact">📞 {storage['contact_number']}</div>
                </div>
                """, unsafe_allow_html=True)

                # Map
                st.markdown("**Warehouse Location**")
                warehouse_coords = {
                    "GCX Tamale Warehouse":   (9.4034, -0.8424),
                    "GCX Bolga Warehouse":    (10.7833, -0.8500),
                    "GCX Sandema Warehouse":  (10.8566, -1.2553),
                    "GCX Wa Warehouse":       (10.0601, -2.5099),
                    "GCX Tumu Warehouse":     (10.9000, -1.9833),
                }
                district_coords = {
                    "Tamale":    (9.40, -0.83),
                    "Sagnarigu": (9.45, -0.88),
                    "Tolon":     (9.45, -1.00),
                    "Kumbungu":  (9.56, -0.95),
                }

                wh_name = storage['name']
                wh_lat, wh_lng = warehouse_coords.get(wh_name, (9.40, -0.83))
                d_lat, d_lng   = district_coords.get(district, (9.40, -0.83))

                map_df = pd.DataFrame([
                    {"name": district + " (Farmer)", "lat": d_lat, "lon": d_lng, "type": "Farmer"},
                    {"name": wh_name, "lat": wh_lat, "lon": wh_lng, "type": "Warehouse"},
                ])

                fig_map = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon",
                    color="type",
                    color_discrete_map={"Farmer": "#1A9DAA", "Warehouse": "#00A878"},
                    hover_name="name",
                    zoom=9, height=220,
                    size_max=15,
                )
                fig_map.update_layout(
                    mapbox_style="carto-positron",
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(orientation="h", y=1, x=0),
                )
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("No verified storage found for this crop and district. Contact MoFA: 118")

    else:
        st.error("Could not reach the PostHarvest IQ API. Check your connection.")

    # ── District summary table ───────────────────────────────────
    st.markdown("---")
    st.markdown('<p class="section-title">All District Recommendations</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Current sell-or-store recommendation for all districts and crops</p>', unsafe_allow_html=True)

    with st.spinner("Loading district summary..."):
        summary = api_get("/dashboard/summary")

    if summary and "summary" in summary:
        rows = summary["summary"]
        df_sum = pd.DataFrame(rows)

        def style_decision(val):
            if val == "STORE":
                return "background-color: #E6F9F4; color: #00A878; font-weight: 600"
            elif val == "SELL_PARTIAL":
                return "background-color: #FEF3E2; color: #E8940A; font-weight: 600"
            elif val == "SELL_NOW":
                return "background-color: #FEEAEA; color: #C0392B; font-weight: 600"
            return ""

        df_display = df_sum.copy()
        df_display.columns = ["District", "Crop", "Decision", "Net Gain (GHS)", "Forecast Price", "Current Price"]
        df_display["Net Gain (GHS)"] = df_display["Net Gain (GHS)"].apply(lambda x: f"GHS {x:,.0f}" if x else "—")
        df_display["Forecast Price"] = df_display["Forecast Price"].apply(lambda x: f"GHS {x:,.0f}" if x else "—")
        df_display["Current Price"]  = df_display["Current Price"].apply(lambda x: f"GHS {x:,.0f}" if x else "—")

        styled = df_display.style.applymap(style_decision, subset=["Decision"])
        st.dataframe(styled, use_container_width=True, height=400)
    else:
        st.warning("Could not load district summary.")

# ══════════════════════════════════════════════════════════════════
# PAGE: PRICE FORECAST
# ══════════════════════════════════════════════════════════════════
elif page == "🔮 Price Forecast":

    st.markdown('<p class="section-title">Price Forecast & Historical Trends</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">WFP VAM price data 2006-2023 · Seasonal pattern analysis · Northern Ghana cereals</p>', unsafe_allow_html=True)

    # Load forecast
    with st.spinner("Loading forecast..."):
        forecast_data = api_get(f"/forecasts/{district}/{crop}")

    if forecast_data and "forecast" in forecast_data:
        f = forecast_data["forecast"]
        current  = f.get("current_price", 0)
        forecast = f.get("forecast_price", 0)
        method   = f.get("method", "seasonal_estimate")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card navy">
              <div class="metric-label">Current Price</div>
              <div class="metric-value">{fmt_ghs(current)}</div>
              <div class="metric-sub">Latest WFP VAM reading</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card green">
              <div class="metric-label">Forecast Price</div>
              <div class="metric-value">{fmt_ghs(forecast)}</div>
              <div class="metric-sub">Next month estimate</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            gain = forecast - current if forecast and current else 0
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Expected Gain/Bag</div>
              <div class="metric-value">{fmt_ghs(gain)}</div>
              <div class="metric-sub">Method: {method.replace("_"," ").title()}</div>
            </div>""", unsafe_allow_html=True)

    # EDA charts from notebooks/figures/
    st.markdown("---")
    st.markdown("### Historical Price Analysis")
    st.caption("Source: WFP VAM Ghana · 2006-2023 · Tamale, Bolga, Wa wholesale prices")

    figures_path = "notebooks/figures"
    chart_files = {
        "01_harvest_price_crash.png": "Harvest Season Price Crash — October floor and January recovery",
        "02_longrun_price_trends.png": "Long-run Price Trends 2006-2023 — 18 years of cereal price history",
        "03_market_comparison.png": "Market Comparison — Tamale, Bolga, Wa price correlation",
        "05_fx_vs_price.png": "Exchange Rate vs Price — Cedi depreciation impact on cereal prices",
        "06_correlation_matrix.png": "Feature Correlation Matrix — Model input relationships",
    }

    available = []
    for fname, title in chart_files.items():
        fpath = os.path.join(figures_path, fname)
        if os.path.exists(fpath):
            available.append((fpath, title))

    if available:
        for i in range(0, len(available), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(available):
                    fpath, title = available[i + j]
                    with col:
                        st.image(fpath, caption=title, use_column_width=True)
    else:
        st.info("EDA charts not found locally. Run the notebook to generate them.")
        st.markdown("""
        **Seasonal Pattern (documented):**
        - October harvest: prices crash to annual floor
        - November-December: prices remain low as supply floods markets
        - January-February: lean season begins — prices recover 40-60%
        - March-September: prices rise steadily until next harvest

        This 18-year pattern is the foundation of the PostHarvest IQ recommendation.
        """)

    # Seasonal pattern chart (always shown)
    st.markdown("---")
    st.markdown("### Documented Seasonal Price Pattern — Northern Ghana Cereals")

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    seasonal_index = [1.35, 1.40, 1.38, 1.30, 1.20, 1.10,
                      1.05, 1.00, 0.95, 0.75, 0.70, 0.80]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=[v * 100 for v in seasonal_index],
        mode="lines+markers",
        line=dict(color="#1A9DAA", width=3),
        marker=dict(size=8, color="#1A9DAA"),
        fill="tozeroy",
        fillcolor="rgba(26,157,170,0.1)",
        name="Price Index (Oct=100%)",
    ))
    fig.add_vrect(x0="Oct", x1="Dec", fillcolor="#C0392B", opacity=0.08,
                  annotation_text="Harvest Season", annotation_position="top left")
    fig.add_vrect(x0="Jan", x1="Mar", fillcolor="#00A878", opacity=0.08,
                  annotation_text="Lean Season Peak", annotation_position="top left")
    fig.add_hline(y=100, line_dash="dash", line_color="#E5E7EB",
                  annotation_text="October baseline")
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="DM Sans", size=12),
        yaxis=dict(title="Price Index (%)", showgrid=True, gridcolor="#F3F4F6"),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Based on 18 years of WFP VAM wholesale price data for Tamale, Bolga, and Wa markets. "
               "The October harvest crash and January lean-season recovery repeat consistently every year. "
               "A farmer who stores at harvest and sells in January captures 40-60% additional income.")

# ══════════════════════════════════════════════════════════════════
# PAGE: STORAGE LOCATIONS
# ══════════════════════════════════════════════════════════════════
elif page == "🏪 Storage Locations":

    st.markdown('<p class="section-title">Verified Storage Locations</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Ghana Commodity Exchange verified warehouses · GPS matched by Haversine formula</p>', unsafe_allow_html=True)

    with st.spinner("Loading storage locations..."):
        storage_data = api_get(f"/storage/{district}/{crop}")

    if storage_data and "storage_locations" in storage_data:
        locations = storage_data["storage_locations"]

        if locations:
            st.success(f"Found {len(locations)} verified storage locations near {district} for {crop}")

            # Map of all locations
            all_locs = api_get(f"/storage/Tamale/Maize")
            if all_locs and "storage_locations" in all_locs:
                all_locations = all_locs["storage_locations"]

                warehouse_coords = {
                    "GCX Tamale Warehouse":   (9.4034, -0.8424),
                    "GCX Bolga Warehouse":    (10.7833, -0.8500),
                    "GCX Sandema Warehouse":  (10.8566, -1.2553),
                    "GCX Wa Warehouse":       (10.0601, -2.5099),
                    "GCX Tumu Warehouse":     (10.9000, -1.9833),
                }

                map_rows = []
                for loc in all_locs["storage_locations"]:
                    lat, lng = warehouse_coords.get(loc['name'], (9.40, -0.83))
                    map_rows.append({
                        "name": loc['name'],
                        "lat": lat,
                        "lon": lng,
                        "cost": loc['cost_per_bag'],
                        "contact": loc['contact_number'],
                    })

                df_map = pd.DataFrame(map_rows)
                fig_map = px.scatter_mapbox(
                    df_map, lat="lat", lon="lon",
                    hover_name="name",
                    hover_data={"cost": True, "contact": True},
                    color_discrete_sequence=["#00A878"],
                    zoom=6, height=350,
                    size_max=15,
                )
                fig_map.update_layout(
                    mapbox_style="carto-positron",
                    margin=dict(l=0, r=0, t=0, b=0),
                )
                st.plotly_chart(fig_map, use_container_width=True)

            # Location cards
            for i, loc in enumerate(locations):
                rank = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                st.markdown(f"""
                <div class="storage-card">
                  <div class="storage-name">{rank} {loc['name']}</div>
                  <div class="storage-meta">
                    📍 <strong>{loc['distance_km']} km</strong> from {district} district centre<br>
                    💰 <strong>GHS {loc['cost_per_bag']}/bag/month</strong> · Ghana Commodity Exchange rate<br>
                    🌾 Accepts: Maize, Sorghum · Minimum: 20 bags<br>
                    ✅ Verified · Active
                  </div>
                  <div class="storage-contact">📞 {loc['contact_number']}</div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.warning(f"No verified storage found for {crop} near {district}.")
            st.info("Note: GCX warehouses currently accept Maize and Sorghum only. "
                    "Millet storage expansion is planned for Phase 2. "
                    "Contact MoFA Tamale on 118 for Millet storage options.")
    else:
        st.error("Could not load storage data.")

    # GCX info
    st.markdown("---")
    st.markdown("### About Ghana Commodity Exchange Warehouses")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card green">
          <div class="metric-label">Storage Cost</div>
          <div class="metric-value">GHS 0.80</div>
          <div class="metric-sub">per bag per month</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Minimum Quantity</div>
          <div class="metric-value">20 bags</div>
          <div class="metric-sub">per deposit (1 metric tonne)</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card navy">
          <div class="metric-label">Verified Locations</div>
          <div class="metric-value">5</div>
          <div class="metric-sub">Tamale · Bolga · Wa · Tumu · Sandema</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# PAGE: RECOMMENDATIONS LOG
# ══════════════════════════════════════════════════════════════════
elif page == "📋 Recommendations Log":

    st.markdown('<p class="section-title">Farmer Recommendations Log</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Every USSD session is logged here for WFP monitoring and impact tracking</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="alert-box">
      Every time a farmer dials <strong>*384*33939#</strong> and completes the flow,
      their recommendation is anonymously logged here. Phone numbers are stored for
      session tracking only — no personal data is retained beyond the recommendation outcome.
      This data feeds WFP's impact monitoring for the P4P programme.
    </div>
    """, unsafe_allow_html=True)

    # Simulate recent sessions for demo
    demo_data = [
        {"Session": "demo_001", "Crop": "Maize",   "District": "Tamale",    "Decision": "STORE",        "Net Gain": "GHS 2,628", "Time": "Today 09:14"},
        {"Session": "demo_002", "Crop": "Millet",  "District": "Sagnarigu", "Decision": "STORE",        "Net Gain": "GHS 3,420", "Time": "Today 09:31"},
        {"Session": "demo_003", "Crop": "Sorghum", "District": "Tolon",     "Decision": "STORE",        "Net Gain": "GHS 3,486", "Time": "Today 10:02"},
        {"Session": "demo_004", "Crop": "Maize",   "District": "Kumbungu",  "Decision": "SELL_PARTIAL", "Net Gain": "GHS 580",   "Time": "Today 10:45"},
        {"Session": "demo_005", "Crop": "Maize",   "District": "Tamale",    "Decision": "STORE",        "Net Gain": "GHS 2,628", "Time": "Today 11:20"},
    ]

    df_log = pd.DataFrame(demo_data)

    def style_log(val):
        if val == "STORE":
            return "background-color:#E6F9F4; color:#00A878; font-weight:600"
        elif val == "SELL_PARTIAL":
            return "background-color:#FEF3E2; color:#E8940A; font-weight:600"
        elif val == "SELL_NOW":
            return "background-color:#FEEAEA; color:#C0392B; font-weight:600"
        return ""

    st.dataframe(
        df_log.style.applymap(style_log, subset=["Decision"]),
        use_container_width=True
    )

    st.caption("Demo data shown. Live recommendations are logged to MySQL recommendations table on Railway.")

    # Impact metrics
    st.markdown("---")
    st.markdown("### Projected Impact — Year 1")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card green">
          <div class="metric-label">Target Farmers</div>
          <div class="metric-value">2,000</div>
          <div class="metric-sub">Year 1 · 3 districts</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Avg. Net Gain</div>
          <div class="metric-value">GHS 800</div>
          <div class="metric-sub">per farmer per season</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card navy">
          <div class="metric-label">Community Income</div>
          <div class="metric-value">GHS 1.6M</div>
          <div class="metric-sub">recovered per season</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card amber">
          <div class="metric-label">SDG Target</div>
          <div class="metric-value">2.3</div>
          <div class="metric-sub">Double smallholder incomes</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ══════════════════════════════════════════════════════════════════
elif page == "ℹ️ About":

    st.markdown('<p class="section-title">About PostHarvest IQ</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        **PostHarvest IQ** is a USSD-based agricultural decision intelligence system
        that tells a smallholder cereal farmer in Northern Ghana whether to sell her
        crop today or store and wait — with the exact net return in Ghana cedis and
        the nearest verified storage location — delivered to any mobile phone on any
        Ghanaian network in under two minutes.

        ### How It Works
        1. **Farmer dials** `*384*33939#` on any phone
        2. **Selects** language (English / Dagbani / Hausa)
        3. **Selects** crop (Maize / Millet / Sorghum)
        4. **Selects** district (Sagnarigu / Tolon / Kumbungu / Tamale)
        5. **Receives** STORE / SELL NOW / SELL PARTIAL with net GHS figure
        6. **Action** — nearest GCX warehouse or nearest market

        ### The Technology
        - **Price forecasting:** Seasonal estimate based on 18-year WFP VAM pattern
        - **Decision classifier:** XGBoost trained on Northern Ghana cereal price history
        - **Storage matching:** Haversine GPS formula → nearest verified GCX warehouse
        - **Language layer:** English, Dagbani, Hausa
        - **API:** FastAPI deployed on Render
        - **Database:** MySQL on Railway with 6 verified datasets
        """)

    with col2:
        st.markdown(f"""
        <div class="metric-card navy">
          <div class="metric-label">Production URL</div>
          <div class="metric-value" style="font-size:14px; font-family:'DM Mono'">postharvest-iq.onrender.com</div>
          <div class="metric-sub">FastAPI · Always on</div>
        </div>

        <div class="metric-card">
          <div class="metric-label">USSD Code</div>
          <div class="metric-value">*384*33939#</div>
          <div class="metric-sub">Africa's Talking sandbox</div>
        </div>

        <div class="metric-card green">
          <div class="metric-label">Training Data</div>
          <div class="metric-value">1,744 rows</div>
          <div class="metric-sub">WFP VAM · 2006-2023 · 18 years</div>
        </div>

        <div class="metric-card amber">
          <div class="metric-label">Storage Locations</div>
          <div class="metric-value">5 verified</div>
          <div class="metric-sub">Ghana Commodity Exchange</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### WFP Strategic Alignment")

    st.markdown("""
    <div class="wfp-box">
      PostHarvest IQ advances SDG 2 Target 2.3 by recovering GHS 500 to 1,200 of
      smallholder farmer income per season through one better decision at harvest time.
      It serves WFP Ghana's Country Strategic Plan 2024-2028 Outcome 3 by building
      financial resilience for the farmers most vulnerable to price shocks. It strengthens
      WFP's Purchase for Progress programme by incentivising the storage behaviour that
      produces better quality grain. And it trains entirely on WFP VAM data — turning an
      investment WFP has already made into farmer-facing decision intelligence for the first time.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Datasets Used")

    datasets = [
        ["WFP VAM Food Prices Ghana", "26,254 rows", "Primary LSTM training data", "data.humdata.org"],
        ["WFP Market Registry Ghana", "93 markets", "GPS coordinates for distance matching", "data.humdata.org"],
        ["Ghana Exchange Rates", "785 rows", "Macro signal — separates inflation from seasonal", "fao.org/faostat"],
        ["Ghana Producer Prices", "5,696 rows", "Farm gate price signal", "fao.org/faostat"],
        ["Language Use Admin1", "139 rows", "Language distribution by region", "clearglobal.org"],
        ["Language Use Admin2", "423 rows", "Language distribution by district", "clearglobal.org"],
    ]

    df_data = pd.DataFrame(datasets, columns=["Dataset", "Records", "Purpose", "Source"])
    st.dataframe(df_data, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("PostHarvest IQ · Blossom Academy · WFP Code4FoodSecurity Fellowship 2026 · Presentation: 11 June 2026")