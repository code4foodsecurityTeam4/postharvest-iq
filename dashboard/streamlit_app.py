"""
PostHarvest IQ — Streamlit monitoring and model showcase dashboard.
"""

import datetime as _dt
import os
import plotly.graph_objects as go
import requests
import streamlit as st

try:
    API_BASE = st.secrets["API_BASE"]
except Exception:
    API_BASE = os.getenv("API_BASE", "https://postharvest-iq.onrender.com")

TIMEOUT = 20
DISTRICTS = ["Tamale", "Bolgatanga", "Wa"]
CROPS     = ["Maize", "Millet", "Sorghum"]

INK, PANEL = "#14110E", "#1E1A15"
GOLD, GRAIN, CREAM, MUTE = "#E8A33D", "#D4B483", "#F2E9DC", "#9C8F7A"
GREEN, RED, AMBER = "#3E8E5A", "#C44536", "#D9820B"

DEC = {
    "STORE":        (GREEN,  "Store"),
    "SELL_NOW":     (RED,    "Sell now"),
    "SELL_PARTIAL": (AMBER,  "Sell half"),
    "UNAVAILABLE":  (MUTE,   "—"),
}

STORAGE_FALLBACK = {
    "Tamale":     [{"name": "GCX Tamale Warehouse",  "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Tamale",  "crops": ["Maize", "Sorghum"]}],
    "Bolgatanga": [{"name": "GCX Bolga Warehouse",   "distance_km": 0.75, "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Bolga",   "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Sandema Warehouse", "distance_km": 44.9, "cost_per_bag": 0.80, "contact_number": "0594164451", "type": "Ghana Commodity Exchange", "district": "Sandema", "crops": ["Maize", "Sorghum"]}],
    "Wa":         [{"name": "GCX Wa Warehouse",      "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Wa",      "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Tumu Warehouse",    "distance_km": 68.5, "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Tumu",    "crops": ["Maize", "Sorghum"]}],
}


@st.cache_data(ttl=30, show_spinner=False)
def load_activity():
    try:
        r = requests.get(f"{API_BASE}/recommendations/activity", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), "live"
    except Exception:
        return None, "offline"


@st.cache_data(ttl=60, show_spinner=False)
def load_summary():
    try:
        r = requests.get(f"{API_BASE}/dashboard/summary", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("summary", []), "live"
    except Exception:
        return [], "offline"


@st.cache_data(ttl=300, show_spinner=False)
def load_metadata():
    try:
        r = requests.get(f"{API_BASE}/ml/metadata", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), "live"
    except Exception:
        return None, "offline"


@st.cache_data(ttl=120, show_spinner=False)
def load_storage(district, crop):
    try:
        r = requests.get(f"{API_BASE}/storage/{district}/{crop}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), "live"
    except Exception:
        return None, "offline"


st.set_page_config(page_title="PostHarvest IQ", page_icon="🌾", layout="wide")

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Outfit:wght@300;400;500;600&display=swap');
.stApp {{ background:{INK}; }}
.block-container {{ padding-top:2rem; max-width:1200px; }}
html,body,[class*="css"] {{ font-family:'Outfit',sans-serif; color:{CREAM}; }}
h1,h2,h3 {{ font-family:'Fraunces',serif !important; color:{CREAM} !important; letter-spacing:-.5px; }}
h1 {{ font-weight:900 !important; }}
section[data-testid="stSidebar"] {{ background:{PANEL}; border-right:1px solid #2E2820; }}
section[data-testid="stSidebar"] * {{ color:{CREAM}; }}
.hero {{ background:linear-gradient(135deg,{PANEL} 0%,#2A2318 100%); border:1px solid #332B20; border-left:4px solid {GOLD}; border-radius:14px; padding:1.8rem 2.1rem; margin-bottom:1.4rem; }}
.hero h1 {{ font-size:2.4rem; margin:0 0 .25rem 0; }}
.hero p {{ color:{GRAIN}; font-size:1rem; margin:0; }}
.statcard {{ background:{PANEL}; border:1px solid #2E2820; border-radius:12px; padding:1.1rem 1.3rem; height:100%; }}
.statcard .num {{ font-family:'Fraunces',serif; font-size:2rem; font-weight:900; color:{GOLD}; line-height:1; }}
.statcard .lab {{ color:{MUTE}; font-size:.8rem; margin-top:.4rem; }}
.panel {{ background:{PANEL}; border:1px solid #2E2820; border-radius:12px; padding:1.3rem 1.5rem; margin-bottom:1rem; }}
.fcard {{ background:{PANEL}; border:1px solid #2E2820; border-radius:12px; padding:1.1rem 1.2rem; height:100%; }}
.fcard .crop {{ font-family:'Fraunces',serif; font-size:1.05rem; font-weight:700; color:{CREAM}; margin-bottom:.1rem; }}
.fcard .district {{ color:{MUTE}; font-size:.78rem; letter-spacing:.5px; text-transform:uppercase; margin-bottom:.6rem; }}
.fcard .price {{ font-size:.85rem; color:{GRAIN}; margin:.15rem 0; }}
.fcard .range {{ font-size:.8rem; color:{MUTE}; margin:.15rem 0; }}
.scard {{ background:{PANEL}; border:1px solid #2E2820; border-left:4px solid {GOLD}; border-radius:12px; padding:1.1rem 1.3rem; margin-bottom:.8rem; }}
.pill {{ display:inline-block; padding:3px 12px; border-radius:20px; font-size:.78rem; font-weight:600; color:#fff; margin-top:.5rem; }}
.tag {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:.72rem; background:#332B20; color:{GRAIN}; margin-left:8px; }}
.feedrow {{ display:grid; grid-template-columns:1fr auto auto; align-items:center; gap:1rem; padding:.7rem 1rem; border-bottom:1px solid #2A241C; }}
.feedrow:last-child {{ border-bottom:none; }}
.dot {{ height:8px; width:8px; border-radius:50%; display:inline-block; margin-right:8px; }}
.metric-chip {{ background:{PANEL}; border:1px solid #2E2820; border-radius:10px; padding:.9rem 1.1rem; text-align:center; }}
.metric-chip .val {{ font-family:'Fraunces',serif; font-size:1.7rem; font-weight:900; color:{GOLD}; line-height:1; }}
.metric-chip .lbl {{ color:{MUTE}; font-size:.75rem; margin-top:.3rem; }}
.section-label {{ color:{GRAIN}; font-size:.72rem; letter-spacing:1px; text-transform:uppercase; margin-bottom:.4rem; }}
hr {{ border-color:#2E2820; }}
</style>""", unsafe_allow_html=True)


def stat(num, lab):
    return f"<div class='statcard'><div class='num'>{num}</div><div class='lab'>{lab}</div></div>"

def badge(d):
    c, l = DEC.get(d, DEC["UNAVAILABLE"])
    return f"<span class='pill' style='background:{c}'>{l}</span>"

def chip(val, lbl):
    return f"<div class='metric-chip'><div class='val'>{val}</div><div class='lbl'>{lbl}</div></div>"

def cedis(v):
    try:
        return f"GHS {round(float(v)):,}"
    except (TypeError, ValueError):
        return "—"

def ago(iso):
    if not iso:
        return "—"
    try:
        t = _dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)
        s = (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) - t).total_seconds()
        if s < 60:    return "just now"
        if s < 3600:  return f"{int(s//60)}m ago"
        if s < 86400: return f"{int(s//3600)}h ago"
        return f"{int(s//86400)}d ago"
    except Exception:
        return "recently"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='font-size:1.5rem;margin-bottom:0'>🌾 PostHarvest IQ</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.82rem;margin-top:.3rem;line-height:1.5'>A USSD-based sell-or-store advisory for smallholder cereal farmers in Northern Ghana.<br>Dial <b style='color:{GOLD}'>*384#</b> — works on any phone, no internet needed.</p>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"""
    <p class='section-label'>Coverage</p>
    <p style='color:{MUTE};font-size:.8rem;margin:0;line-height:1.8'>
        3 crops &nbsp;·&nbsp; Maize · Millet · Sorghum<br>
        3 districts · Tamale · Bolgatanga · Wa<br>
        3 languages · English · Dagbani · Hausa
    </p>
    <hr>
    <p class='section-label'>Data sources</p>
    <p style='color:{MUTE};font-size:.8rem;margin:0;line-height:1.8'>
        WFP VAM wholesale prices (2015–2023)<br>
        FAO GHS/USD exchange rates<br>
        Ghana Commodity Exchange warehouses<br>
        Synthetic extension 2023 → present
    </p>
    <hr>
    <p class='section-label'>Stack</p>
    <p style='color:{MUTE};font-size:.8rem;margin:0;line-height:1.8'>
        PyTorch LSTM · Random Forest<br>
        FastAPI · MySQL · Africa's Talking
    </p>
    """, unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_forecast, tab_activity, tab_model, tab_storage = st.tabs([
    "Current Forecasts", "Live Activity", "Model Performance", "Storage"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Current Forecasts
# ══════════════════════════════════════════════════════════════════════════════
with tab_forecast:
    st.markdown(f"""<div class='hero'>
    <h1>Current Forecasts</h1>
    <p>Live LSTM price forecasts and STORE / SELL NOW recommendations across all
    crop–district combinations. Prices in GHS per 100-kg bag.</p>
    </div>""", unsafe_allow_html=True)

    top = st.columns([3, 1])
    with top[1]:
        if st.button("↻ Refresh", key="ref_forecast"):
            st.cache_data.clear(); st.rerun()

    summary, src = load_summary()

    if not summary:
        st.warning("Could not reach the API. Check that the server is running.")
    else:
        if src == "live":
            with top[0]:
                st.success(f"Connected · {_dt.datetime.now():%H:%M:%S}")

        # Index by (district, crop) for easy lookup
        idx = {(r["district"], r["crop"]): r for r in summary}

        for crop in CROPS:
            cols = st.columns(3)
            for i, district in enumerate(DISTRICTS):
                rec = idx.get((district, crop), {})
                decision    = rec.get("decision", "UNAVAILABLE")
                cur         = rec.get("current_price")
                low         = rec.get("forecast_low")
                high        = rec.get("forecast_high")
                net_per_bag = rec.get("net_per_bag")
                dec_color   = DEC.get(decision, DEC["UNAVAILABLE"])[0]
                dec_label   = DEC.get(decision, DEC["UNAVAILABLE"])[1]

                cur_str   = f"GHS {round(cur):,}"   if cur  is not None else "—"
                range_str = (f"GHS {round(low):,} – {round(high):,}"
                             if low is not None and high is not None else "—")
                net_str   = (f"+GHS {round(net_per_bag):,} / bag"
                             if net_per_bag is not None and net_per_bag > 0
                             else (f"GHS {round(net_per_bag):,} / bag"
                                   if net_per_bag is not None else ""))

                cols[i].markdown(f"""<div class='fcard'>
                <div class='crop'>{crop}</div>
                <div class='district'>{district}</div>
                <div class='price'>Today: <b style='color:{CREAM}'>{cur_str}</b></div>
                <div class='range'>In 3 months: {range_str}</div>
                {"<div class='price'>Net gain: <b style='color:" + GREEN + "'>" + net_str + "</b></div>" if decision == "STORE" and net_str else ""}
                <span class='pill' style='background:{dec_color}'>{dec_label}</span>
                </div>""", unsafe_allow_html=True)

        st.markdown(f"<p style='color:{MUTE};font-size:.78rem;margin-top:1rem'>Forecast range = LSTM prediction ± per-crop test-set MAE. Net gain = price rise − storage cost (GHS 0.80/bag/month × 3) − transport cost.</p>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Live Activity
# ══════════════════════════════════════════════════════════════════════════════
with tab_activity:
    st.markdown(f"""<div class='hero'>
    <h1>Platform Activity</h1>
    <p>Every USSD advisory session logged in real time — crop, district, recommendation issued, language used.</p>
    </div>""", unsafe_allow_html=True)

    top2 = st.columns([3, 1])
    with top2[1]:
        if st.button("↻ Refresh", key="ref_activity"):
            st.cache_data.clear(); st.rerun()

    data, src = load_activity()

    if data and data.get("total_sessions", 0) > 0:
        with top2[0]:
            st.success(f"Connected · live data · {_dt.datetime.now():%H:%M:%S}")

        c = st.columns(4)
        c[0].markdown(stat(data["total_sessions"],                             "advisory sessions"),  unsafe_allow_html=True)
        c[1].markdown(stat(data.get("unique_farmers", "—"),                   "unique farmers"),     unsafe_allow_html=True)
        c[2].markdown(stat(data.get("by_decision", {}).get("SELL_NOW", 0),    "sell now"),           unsafe_allow_html=True)
        c[3].markdown(stat(data.get("by_decision", {}).get("STORE", 0),       "store"),              unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Recent decisions")
        feed_parts = []
        for r in data.get("recent", []):
            dec = r.get("decision", "UNAVAILABLE")
            dot_color = DEC.get(dec, DEC["UNAVAILABLE"])[0]
            feed_parts.append(
                f"<div class='feedrow'>"
                f"<div><span class='dot' style='background:{dot_color}'></span>"
                f"<b>{r['crop']}</b> · {r['district']}</div>"
                f"<div style='color:{MUTE};font-size:.85rem'>{r['phone']}</div>"
                f"<div>{badge(dec)} <span style='color:{MUTE};font-size:.8rem;margin-left:8px'>{ago(r['when'])}</span></div>"
                f"</div>"
            )
        feed = "".join(feed_parts)
        empty_feed = "<p style='padding:1rem'>No sessions yet.</p>"
        st.markdown(f"<div class='panel' style='padding:.3rem 0'>{feed or empty_feed}</div>",
                    unsafe_allow_html=True)

        bc  = data.get("by_crop", {})
        bd  = data.get("by_district", {})
        bde = data.get("by_decision", {})

        if bc or bd:
            st.markdown("### Usage breakdown")
            ch1, ch2 = st.columns(2)
            with ch1:
                if bc:
                    st.markdown(f"<p class='section-label'>Sessions by crop</p>", unsafe_allow_html=True)
                    fig = go.Figure(go.Bar(x=list(bc.keys()), y=list(bc.values()),
                                          marker_color=GOLD, text=list(bc.values()), textposition="outside"))
                    fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                      height=260, margin=dict(t=20,b=20,l=10,r=10), showlegend=False)
                    fig.update_xaxes(gridcolor="#2E2820")
                    fig.update_yaxes(gridcolor="#2E2820", title="sessions")
                    st.plotly_chart(fig, use_container_width=True)
            with ch2:
                if bd:
                    st.markdown(f"<p class='section-label'>Sessions by district</p>", unsafe_allow_html=True)
                    fig = go.Figure(go.Bar(x=list(bd.keys()), y=list(bd.values()),
                                          marker_color=GRAIN, text=list(bd.values()), textposition="outside"))
                    fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                      height=260, margin=dict(t=20,b=20,l=10,r=10), showlegend=False)
                    fig.update_xaxes(gridcolor="#2E2820")
                    fig.update_yaxes(gridcolor="#2E2820", title="sessions")
                    st.plotly_chart(fig, use_container_width=True)

        if bde:
            st.markdown(f"<p class='section-label'>Recommendation distribution</p>", unsafe_allow_html=True)
            labels  = list(bde.keys())
            vals    = list(bde.values())
            colors  = [DEC.get(k, DEC["UNAVAILABLE"])[0] for k in labels]
            display = [DEC.get(k, DEC["UNAVAILABLE"])[1] for k in labels]
            fig = go.Figure(go.Bar(x=display, y=vals, marker_color=colors,
                                   text=vals, textposition="outside"))
            fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                               height=240, margin=dict(t=20,b=20,l=10,r=10), showlegend=False)
            fig.update_xaxes(gridcolor="#2E2820")
            fig.update_yaxes(gridcolor="#2E2820", title="sessions")
            st.plotly_chart(fig, use_container_width=True)

    else:
        with top2[0]:
            st.info("No USSD sessions recorded yet. Dial *384# to generate the first advisory.")
        st.markdown(f"""<div class='panel' style='border-left:4px solid {GOLD}'>
        <b style='color:{GOLD}'>How it works</b><br>
        <p style='color:{GRAIN};margin:.6rem 0 0 0'>A farmer dials <b>*384#</b> on any basic phone →
        selects language, crop, and district → enters bag count → receives a STORE or SELL NOW
        recommendation with the expected net gain in GHS. Every session is logged here in real time.</p>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Model Performance
# ══════════════════════════════════════════════════════════════════════════════
with tab_model:
    st.markdown(f"""<div class='hero'>
    <h1>Model Performance</h1>
    <p>LSTM price forecaster and Random Forest classifier — benchmark results, per-crop breakdown,
    and the five-algorithm tournament that selected the deployed model.</p>
    </div>""", unsafe_allow_html=True)

    meta, src = load_metadata()

    if not meta:
        st.warning("Model metadata unavailable. Ensure the API is running and models have been trained.")
    else:
        # ── Top metric chips ─────────────────────────────────────────────────
        lstm_mae   = meta.get("lstm_mae_ghs", "—")
        lstm_r2    = meta.get("lstm_r2", "—")
        lstm_dir   = meta.get("lstm_dir_accuracy", "—")
        cls_name   = meta.get("best_classifier", "—")
        cls_val_f1 = meta.get("val_macro_f1", "—")
        cls_te_f1  = meta.get("test_macro_f1", "—")

        c0, c1, c2, c3, c4 = st.columns(5)
        c0.markdown(chip(f"{lstm_mae} GHS",       "LSTM MAE (test set)"),          unsafe_allow_html=True)
        c1.markdown(chip(f"{lstm_r2:.2f}",         "LSTM R²"),                      unsafe_allow_html=True)
        c2.markdown(chip(f"{lstm_dir:.0f}%",       "LSTM directional accuracy"),    unsafe_allow_html=True)
        c3.markdown(chip(f"{cls_val_f1:.2f}",      f"{cls_name} val F1"),           unsafe_allow_html=True)
        c4.markdown(chip(f"{cls_te_f1:.2f}",       f"{cls_name} test F1"),          unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Forecaster benchmark ─────────────────────────────────────────────
        st.markdown("### Forecaster benchmark")
        st.markdown(f"<p style='color:{MUTE};font-size:.88rem;margin-bottom:.8rem'>MAE on the same held-out test split (lower is better). LSTM is deployed despite a higher MAE than XGBoost/RF because it produces market-specific sequential forecasts that extend naturally to a 3-month horizon.</p>", unsafe_allow_html=True)

        forecast_results = meta.get("all_forecast_results", {})
        if forecast_results:
            order  = sorted(forecast_results.items(), key=lambda x: x[1].get("MAE", 9999))
            names  = [n for n, _ in order]
            maes   = [v.get("MAE", 0) for _, v in order]
            r2s    = [v.get("R2", 0)  for _, v in order]
            dirs   = [v.get("DirAcc", 0) for _, v in order]
            colors = [GOLD if "LSTM" in n else GRAIN for n in names]

            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown(f"<p class='section-label'>MAE (GHS) — lower is better</p>", unsafe_allow_html=True)
                fig = go.Figure(go.Bar(
                    x=names, y=maes, marker_color=colors,
                    text=[f"{m:.0f}" for m in maes], textposition="outside",
                ))
                fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                  height=300, margin=dict(t=20,b=60,l=10,r=10), showlegend=False)
                fig.update_xaxes(gridcolor="#2E2820", tickangle=-30)
                fig.update_yaxes(gridcolor="#2E2820", title="MAE (GHS)")
                st.plotly_chart(fig, use_container_width=True)

            with ch2:
                st.markdown(f"<p class='section-label'>Directional accuracy (%) — higher is better</p>", unsafe_allow_html=True)
                fig = go.Figure(go.Bar(
                    x=names, y=dirs, marker_color=colors,
                    text=[f"{d:.0f}%" for d in dirs], textposition="outside",
                ))
                fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                  height=300, margin=dict(t=20,b=60,l=10,r=10), showlegend=False)
                fig.update_xaxes(gridcolor="#2E2820", tickangle=-30)
                fig.update_yaxes(gridcolor="#2E2820", title="Directional accuracy (%)", range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)

        # ── Classifier tournament ────────────────────────────────────────────
        st.markdown("### Classifier tournament")
        st.markdown(f"<p style='color:{MUTE};font-size:.88rem;margin-bottom:.8rem'>Five algorithms evaluated on identical features and chronological splits. Model selection uses validation F1 — not test F1 — to prevent the held-out set from influencing the choice.</p>", unsafe_allow_html=True)

        cls_results = meta.get("all_cls_results", {})
        if cls_results:
            best = meta.get("best_classifier", "")
            algs      = list(cls_results.keys())
            val_f1s   = [cls_results[a]["val_f1"]  for a in algs]
            test_f1s  = [cls_results[a]["test_f1"] for a in algs]
            bar_colors = [GOLD if a == best else GRAIN for a in algs]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Validation F1", x=algs, y=val_f1s,
                marker_color=bar_colors,
                text=[f"{v:.3f}" for v in val_f1s], textposition="outside",
            ))
            fig.add_trace(go.Bar(
                name="Test F1", x=algs, y=test_f1s,
                marker_color=[c + "88" for c in bar_colors],
                text=[f"{v:.3f}" for v in test_f1s], textposition="outside",
            ))
            fig.update_layout(
                plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                barmode="group", height=320, margin=dict(t=20,b=20,l=10,r=10),
                legend=dict(bgcolor=PANEL, bordercolor="#2E2820"),
                yaxis_range=[0, 1.15],
            )
            fig.update_xaxes(gridcolor="#2E2820")
            fig.update_yaxes(gridcolor="#2E2820", title="Macro F1")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"<p style='color:{MUTE};font-size:.8rem'>★ Deployed: <b style='color:{GOLD}'>{best}</b> — highest validation F1. SMOTE and class_weight='balanced' were compared; the better-performing balance strategy was selected per run.</p>",
                        unsafe_allow_html=True)

        # ── Per-crop LSTM breakdown ──────────────────────────────────────────
        st.markdown("### Per-crop LSTM breakdown")
        per_crop = meta.get("lstm_per_crop", {})
        if per_crop:
            crop_names = list(per_crop.keys())
            crop_maes  = [per_crop[c]["mae"]     for c in crop_names]
            crop_dirs  = [per_crop[c]["dir_acc"] for c in crop_names]

            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown(f"<p class='section-label'>MAE per crop (GHS)</p>", unsafe_allow_html=True)
                fig = go.Figure(go.Bar(
                    x=crop_names, y=crop_maes, marker_color=[GOLD, GRAIN, AMBER],
                    text=[f"{m:.0f}" for m in crop_maes], textposition="outside",
                ))
                fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                  height=260, margin=dict(t=20,b=20,l=10,r=10), showlegend=False)
                fig.update_xaxes(gridcolor="#2E2820")
                fig.update_yaxes(gridcolor="#2E2820", title="MAE (GHS)")
                st.plotly_chart(fig, use_container_width=True)

            with ch2:
                st.markdown(f"<p class='section-label'>Directional accuracy per crop (%)</p>", unsafe_allow_html=True)
                fig = go.Figure(go.Bar(
                    x=crop_names, y=crop_dirs, marker_color=[GOLD, GRAIN, AMBER],
                    text=[f"{d:.0f}%" for d in crop_dirs], textposition="outside",
                ))
                fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                  height=260, margin=dict(t=20,b=20,l=10,r=10), showlegend=False)
                fig.update_xaxes(gridcolor="#2E2820")
                fig.update_yaxes(gridcolor="#2E2820", title="Directional accuracy (%)", range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)

        # ── Design choices callout ───────────────────────────────────────────
        st.markdown(f"""<div class='panel' style='border-left:4px solid {GOLD};margin-top:.5rem'>
        <b style='color:{GOLD}'>Key modelling decisions</b>
        <ul style='color:{GRAIN};margin:.6rem 0 0 0;padding-left:1.2rem;line-height:1.9;font-size:.88rem'>
        <li><b>Log-price training</b> — GHS depreciation 2021–2024 shifted prices from ~200 to ~1,000 GHS.
            Log transform makes the trend linear so train and test distributions stay comparable.</li>
        <li><b>Global model across 15 series</b> — per-crop models had ~240 sequences each, too few for
            a network with O(10k) parameters. Pooling all 15 market-crop series gives ~1,200 sequences.</li>
        <li><b>Direct multi-step forecasting</b> — target is log(price at t+3), not t+1. Avoids
            compounding one-step errors across 3 months of recursive rollout.</li>
        <li><b>Relative 5% STORE threshold</b> — scale-invariant across price eras: GHS 10 on a
            GHS 200 bag (2015) vs GHS 50 on a GHS 1,000 bag (2025) represent the same real signal.</li>
        <li><b>Chronological 70/15/15 split, no shuffle</b> — any shuffle would leak future prices into
            training folds, creating look-ahead bias that inflates reported metrics.</li>
        </ul>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Storage
# ══════════════════════════════════════════════════════════════════════════════
with tab_storage:
    st.markdown("# Available storage")
    st.markdown(f"<p style='color:{MUTE}'>Verified GCX warehouses in our registry. A STORE recommendation only holds if there is somewhere to store.</p>", unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    d = f1.selectbox("District", DISTRICTS, index=DISTRICTS.index("Tamale"))
    c = f2.selectbox("Crop", CROPS)

    data, src = load_storage(d, c)
    locs = []
    if isinstance(data, list):
        locs = data
    elif isinstance(data, dict):
        locs = data.get("storage_locations") or data.get("locations") or data.get("storage") or []
    if not locs:
        fallback_all = STORAGE_FALLBACK.get(d, [])
        locs = [l for l in fallback_all if c in l.get("crops", [])]
        src = "offline"

    if locs:
        locs = sorted(locs, key=lambda x: float(x.get("distance_km", 9e9)))
        src_label = "" if src == "live" else f" <span style='color:{MUTE};font-size:.75rem'>(cached)</span>"
        st.markdown(f"<p style='color:{MUTE};margin-bottom:1rem'>{len(locs)} verified "
                    f"warehouse{'s' if len(locs) != 1 else ''} that accept {c}, nearest first.{src_label}</p>",
                    unsafe_allow_html=True)
        for loc in locs:
            name    = loc.get("name", "Warehouse")
            org     = loc.get("type", "")
            town    = loc.get("district", "")
            contact = loc.get("contact_number", loc.get("contact", "—"))
            try:    dist = f"{float(loc.get('distance_km')):.0f} km away"
            except: dist = ""
            try:    cost = f"GHS {float(loc.get('cost_per_bag')):.2f} per bag / month"
            except: cost = ""
            loc_line = f"{town} · {cost}" if (town and cost) else (town or cost)
            st.markdown(f"""<div class='scard'>
            <b style='font-size:1.05rem'>{name}</b> <span class='tag'>{dist}</span><br>
            <span style='color:{GRAIN}'>{loc_line}</span><br>
            <span style='color:{GOLD};font-weight:600'>☎ {contact}</span>
            <span style='color:{MUTE};font-size:.8rem'> · {org}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class='panel' style='border-left:4px solid {AMBER};margin-top:1rem'>
        <b style='color:{AMBER}'>The visibility gap</b><br>
        <p style='color:{GRAIN};margin:.5rem 0 0 0;font-size:.88rem'>Every verified warehouse here belongs
        to one body — the Ghana Commodity Exchange — and they take only maize and sorghum. Even where
        storage exists, farmers often don't know it's there or how to reach it. Putting a real name,
        distance, and phone number in a farmer's hand is part of what this tool addresses.</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='panel' style='border-left:4px solid {AMBER}'>
        <b style='color:{AMBER}'>No verified storage for {c} near {d}.</b><br>
        <p style='color:{GRAIN};margin:.5rem 0 0 0;font-size:.88rem'>We don't invent a warehouse that
        isn't there. For {c}, selling is likely the better call. The GCX warehouses we mapped accept
        maize and sorghum — millet has no verified storage in our registry, which is a real gap
        this project surfaces.</p>
        </div>""", unsafe_allow_html=True)
