"""
dashboard/streamlit_app.py — PostHarvest IQ
"""

import datetime as _dt
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = "https://postharvest-iq.onrender.com"
SUMMARY_ENDPOINT = f"{API_BASE}/dashboard/summary"
ACTIVITY_ENDPOINT = f"{API_BASE}/recommendations/activity"
STORAGE_ENDPOINT = f"{API_BASE}/storage"
TIMEOUT = 20

INK, PANEL = "#14110E", "#1E1A15"
GOLD, GRAIN, CREAM, MUTE = "#E8A33D", "#D4B483", "#F2E9DC", "#9C8F7A"
GREEN, RED, AMBER = "#3E8E5A", "#C44536", "#D9820B"
DEC = {"STORE": (GREEN, "Store"), "SELL_NOW": (RED, "Sell now"),
       "SELL_PARTIAL": (AMBER, "Sell half"), "UNAVAILABLE": (MUTE, "—")}
_NOW = _dt.datetime.now()
CURRENT_LABEL = f"{_NOW:%B %Y} (current)"
MONTHS = [CURRENT_LABEL, "January", "February", "March", "April", "May",
          "June", "July", "August", "September", "October", "November", "December"]
DISTRICTS = ["Sagnarigu", "Tolon", "Kumbungu", "Tamale"]
CROPS = ["Maize", "Millet", "Sorghum"]
FALLBACK = [
    {"district": d, "crop": c, "decision": "SELL_NOW", "net_total": n, "current_price": p, "forecast_price": round(p*0.92, 2)}
    for d in DISTRICTS
    for c, p, n in [("Maize", 538.46, -925.6), ("Millet", 728.0, -1230.0), ("Sorghum", 741.2, -1250.0)]
]


@st.cache_data(ttl=120, show_spinner=False)
def load_summary(month=None):
    try:
        r = requests.get(SUMMARY_ENDPOINT, params=({"month": month} if month else None), timeout=TIMEOUT)
        r.raise_for_status()
        rows = r.json().get("summary", [])
        return (rows, "live") if rows else (FALLBACK, "offline")
    except Exception:
        return FALLBACK, "offline"


@st.cache_data(ttl=30, show_spinner=False)
def load_activity():
    try:
        r = requests.get(ACTIVITY_ENDPOINT, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), "live"
    except Exception:
        return None, "offline"


@st.cache_data(ttl=120, show_spinner=False)
def load_storage(district, crop):
    try:
        r = requests.get(f"{STORAGE_ENDPOINT}/{district}/{crop}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), "live"
    except Exception:
        return None, "offline"


st.set_page_config(page_title="PostHarvest IQ", page_icon="🌾", layout="wide")
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Outfit:wght@300;400;500;600&display=swap');
.stApp {{ background:{INK}; }}
.block-container {{ padding-top:2rem; max-width:1180px; }}
html,body,[class*="css"] {{ font-family:'Outfit',sans-serif; color:{CREAM}; }}
h1,h2,h3 {{ font-family:'Fraunces',serif !important; color:{CREAM} !important; letter-spacing:-.5px; }}
h1 {{ font-weight:900 !important; }}
section[data-testid="stSidebar"] {{ background:{PANEL}; border-right:1px solid #2E2820; }}
section[data-testid="stSidebar"] * {{ color:{CREAM}; }}
.hero {{ background:linear-gradient(135deg,{PANEL} 0%,#2A2318 100%); border:1px solid #332B20; border-left:4px solid {GOLD}; border-radius:14px; padding:1.8rem 2.1rem; margin-bottom:1.4rem; }}
.hero h1 {{ font-size:2.5rem; margin:0 0 .25rem 0; }}
.hero p {{ color:{GRAIN}; font-size:1.05rem; margin:0; }}
.statcard {{ background:{PANEL}; border:1px solid #2E2820; border-radius:12px; padding:1.1rem 1.3rem; height:100%; }}
.statcard .num {{ font-family:'Fraunces',serif; font-size:2rem; font-weight:900; color:{GOLD}; line-height:1; }}
.statcard .lab {{ color:{MUTE}; font-size:.8rem; margin-top:.4rem; }}
.panel {{ background:{PANEL}; border:1px solid #2E2820; border-radius:12px; padding:1.3rem 1.5rem; margin-bottom:1rem; }}
.scard {{ background:{PANEL}; border:1px solid #2E2820; border-left:4px solid {GOLD}; border-radius:12px; padding:1.1rem 1.3rem; margin-bottom:.8rem; }}
.pill {{ display:inline-block; padding:3px 12px; border-radius:20px; font-size:.78rem; font-weight:600; color:#fff; }}
.tag {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:.72rem; background:#332B20; color:{GRAIN}; margin-left:8px; }}
.quote {{ font-family:'Fraunces',serif; font-style:italic; font-size:1.25rem; color:{GRAIN}; border-left:3px solid {GOLD}; padding-left:1rem; margin:1.1rem 0; }}
.feedrow {{ display:grid; grid-template-columns:1fr auto auto; align-items:center; gap:1rem; padding:.7rem 1rem; border-bottom:1px solid #2A241C; }}
.feedrow:last-child {{ border-bottom:none; }}
.dot {{ height:8px; width:8px; border-radius:50%; display:inline-block; margin-right:8px; }}
.cap {{ color:{MUTE}; font-size:.9rem; margin:.2rem 0 1.4rem 0; }}
hr {{ border-color:#2E2820; }}
</style>""", unsafe_allow_html=True)


def stat(num, lab): return f"<div class='statcard'><div class='num'>{num}</div><div class='lab'>{lab}</div></div>"
def badge(d):
    c, l = DEC.get(d, DEC["UNAVAILABLE"]); return f"<span class='pill' style='background:{c}'>{l}</span>"
def cedis(v):
    try: return f"GHS {round(float(v)):,}"
    except (TypeError, ValueError): return "—"
def ago(iso):
    if not iso: return "—"
    try:
        t = _dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)
        s = (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) - t).total_seconds()
        if s < 60: return "just now"
        if s < 3600: return f"{int(s//60)}m ago"
        if s < 86400: return f"{int(s//3600)}h ago"
        return f"{int(s//86400)}d ago"
    except Exception:
        return "recently"


with st.sidebar:
    st.markdown("<h2 style='font-size:1.5rem;margin-bottom:0'>🌾 PostHarvest IQ</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.8rem;margin-top:.2rem'>The sell-or-store call,<br>for any farmer with a phone.</p>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{GRAIN};font-size:.7rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.3rem'>Coverage</p>"
                f"<p style='color:{MUTE};font-size:.78rem;margin-top:0'>3 crops &nbsp;·&nbsp; Maize, Millet, Sorghum<br>4 districts · Sagnarigu, Tolon, Kumbungu, Tamale</p>", unsafe_allow_html=True)


tab1, tab2, tab3, tab4 = st.tabs(["Live Activity", "Recommendations", "Storage", "Alignment"])

with tab1:
    st.markdown("""<div class='hero'><h1>Live activity</h1>
    <p>Every farmer session lands here: crop, district, the decision we gave, and when.</p></div>""", unsafe_allow_html=True)
    data, src = load_activity()
    top = st.columns([3, 1])
    with top[1]:
        if st.button("↻ Refresh"):
            st.cache_data.clear(); st.rerun()
    if data and data.get("total_sessions", 0) > 0:
        with top[0]:
            st.success(f"Live from the database · {_dt.datetime.now():%H:%M:%S}")
        c = st.columns(4)
        c[0].markdown(stat(data["total_sessions"], "decisions delivered"), unsafe_allow_html=True)
        c[1].markdown(stat(data["unique_farmers"], "farmers reached"), unsafe_allow_html=True)
        c[2].markdown(stat(data.get("by_decision", {}).get("SELL_NOW", 0), "told to sell"), unsafe_allow_html=True)
        c[3].markdown(stat(data.get("by_decision", {}).get("STORE", 0), "told to store"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### As it happens")
        feed = "".join(
            f"<div class='feedrow'><div><span class='dot' style='background:{DEC.get(r['decision'],DEC['UNAVAILABLE'])[0]}'></span>"
            f"<b>{r['crop']}</b> · {r['district']}</div>"
            f"<div style='color:{MUTE};font-size:.85rem'>{r['phone']}</div>"
            f"<div>{badge(r['decision'])} <span style='color:{MUTE};font-size:.8rem;margin-left:8px'>{ago(r['when'])}</span></div></div>"
            for r in data.get("recent", []))
        empty_msg = "<p style='padding:1rem'>No sessions yet.</p>"
        st.markdown(f"<div class='panel' style='padding:.3rem 0'>{feed or empty_msg}</div>", unsafe_allow_html=True)
        bc = data.get("by_crop", {})
        if bc:
            st.markdown("### What they're asking about")
            fig = go.Figure(go.Bar(x=list(bc.keys()), y=list(bc.values()), marker_color=GOLD))
            fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM, height=300, margin=dict(t=20, b=30), showlegend=False)
            fig.update_xaxes(gridcolor="#2E2820"); fig.update_yaxes(gridcolor="#2E2820")
            st.plotly_chart(fig, use_container_width=True)
    else:
        with top[0]:
            st.warning("No live sessions yet — dial the USSD code to see one appear here.")
        st.markdown(f"<div class='panel'>This feed fills the moment farmers start using the service. Every USSD session writes a row — crop, district, the decision we gave, the cedi figure — and it shows up here in seconds. <b style='color:{GOLD}'>Dial in during the demo and watch it land.</b></div>", unsafe_allow_html=True)


with tab2:
    st.markdown("# Recommendations given")
    st.markdown(f"<p style='color:{MUTE}'>What the tool tells a farmer for every crop in every district. Switch months to see the advice change with the season.</p>", unsafe_allow_html=True)
    sel = st.selectbox("Show me:", MONTHS, index=0,
        help="Defaults to live. Pick a month to watch the advice flip across the season — same engine, different time of year.")
    month = None if sel == CURRENT_LABEL else MONTHS.index(sel)
    rows, src = load_summary(month)
    df = pd.DataFrame(rows)
    a, b = st.columns([3, 1])
    with a:
        lab = CURRENT_LABEL if month is None else MONTHS[month]
        if src == "live":
            st.success(f"Live · {lab} · {_dt.datetime.now():%H:%M:%S}")
        else:
            st.warning("Sample snapshot — API unreachable.")
    with b:
        if st.button("↻ Refresh", key="rec_refresh"):
            st.cache_data.clear(); st.rerun()
    if not df.empty and "decision" in df:
        m = st.columns(4)
        m[0].markdown(stat(len(df), "crop × district pairs"), unsafe_allow_html=True)
        m[1].markdown(stat(int((df.decision == "STORE").sum()), "store"), unsafe_allow_html=True)
        m[2].markdown(stat(int((df.decision == "SELL_NOW").sum()), "sell now"), unsafe_allow_html=True)
        m[3].markdown(stat(int((df.decision == "SELL_PARTIAL").sum()), "sell half"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        rows_html = "".join(
            f"<tr><td style='padding:9px 12px'>{r.district}</td><td style='padding:9px 12px'>{r.crop}</td>"
            f"<td style='padding:9px 12px'>{badge(r.decision)}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{cedis(r.get('current_price'))}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{cedis(r.get('forecast_price'))}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:{GREEN if (r.get('net_total') or 0)>0 else RED}'>{cedis(r.get('net_total'))}</td></tr>"
            for _, r in df.iterrows())
        st.markdown(f"""<div class='panel'><table style='width:100%;border-collapse:collapse'>
        <thead><tr style='border-bottom:2px solid {GOLD};text-align:left;color:{GRAIN}'>
        <th style='padding:9px 12px'>District</th><th style='padding:9px 12px'>Crop</th><th style='padding:9px 12px'>Call</th>
        <th style='padding:9px 12px;text-align:right'>Today</th><th style='padding:9px 12px;text-align:right'>Forecast</th>
        <th style='padding:9px 12px;text-align:right'>Net (20 bags)</th></tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)
        st.caption("Net = gain or loss on 20 bags after storage cost. Red means storing loses money, so we say sell.")


with tab3:
    st.markdown("# Available storage")
    st.markdown(f"<p style='color:{MUTE}'>The verified warehouses in our registry. A 'store' recommendation only holds if there's somewhere to store.</p>", unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    d = f1.selectbox("District", DISTRICTS, index=DISTRICTS.index("Tamale"))
    c = f2.selectbox("Crop", CROPS)
    data, src = load_storage(d, c)
    locs = []
    if isinstance(data, list):
        locs = data
    elif isinstance(data, dict):
        locs = data.get("storage_locations") or data.get("locations") or data.get("storage") or []
    if locs:
        try:
            locs = sorted(locs, key=lambda x: float(x.get("distance_km", 9e9)))
        except Exception:
            pass
        st.markdown(f"<p style='color:{MUTE};margin-bottom:1rem'>{len(locs)} verified "
                    f"warehouse{'s' if len(locs)!=1 else ''} that accept {c}, nearest first.</p>",
                    unsafe_allow_html=True)
        for loc in locs:
            name = loc.get("name", "Warehouse")
            org = loc.get("type", "")
            town = loc.get("district", "")
            contact = loc.get("contact_number", loc.get("contact", "—"))
            try: dist = f"{float(loc.get('distance_km')):.0f} km away"
            except (TypeError, ValueError): dist = ""
            try: cost = f"GHS {float(loc.get('cost_per_bag')):.2f} per bag / month"
            except (TypeError, ValueError): cost = ""
            loc_line = f"{town} · {cost}" if (town and cost) else (town or cost)
            st.markdown(f"""<div class='scard'>
            <b style='font-size:1.1rem'>{name}</b> <span class='tag'>{dist}</span><br>
            <span style='color:{GRAIN}'>{loc_line}</span><br>
            <span style='color:{GOLD};font-weight:600'>☎ {contact}</span>
            <span style='color:{MUTE};font-size:.8rem'> · {org}</span></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='panel' style='border-left:4px solid {AMBER};margin-top:1rem'>
        <b style='color:{AMBER}'>Why this matters</b><br>
        Every verified warehouse we could find belongs to one body — the Ghana Commodity Exchange —
        and they take only maize and sorghum. So beyond the storage shortage itself, there's a
        <b>visibility gap</b>: even where storage exists, farmers often don't know it is there or how to reach it.
        Putting a real name, distance and phone number in a farmer's hand is part of what this tool fixes.</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='panel' style='border-left:4px solid {AMBER}'>
        <b style='color:{AMBER}'>No verified storage for {c} near {d}.</b><br>
        We don't invent a warehouse that isn't there. For {c}, selling is likely the better call — and
        closing this gap is a defined next step. <span style='color:{MUTE}'>(The Ghana Commodity Exchange
        warehouses we mapped accept maize and sorghum, not millet — and they're the only verified
        storage we could find, which is a visibility gap in itself.)</span></div>""", unsafe_allow_html=True)


with tab4:
    st.markdown("# Why this matters")
    st.markdown(f"<p style='color:{MUTE}'>Every recommendation in PostHarvest IQ is designed around one goal: helping farmers make better selling decisions and keep more value from their harvest.</p>", unsafe_allow_html=True)
    sdgs = [
        ("SDG 2 · Zero Hunger", "Targets 2.3 & 2.c", GOLD,
         "By helping farmers identify more favourable selling periods, PostHarvest IQ aims to improve returns from existing harvests, contributing to higher agricultural incomes. Better-informed selling decisions may also help ease the pressure that builds when large volumes enter the market all at once after harvest."),
        ("SDG 1 · No Poverty", "Target 1.1", GREEN,
         "The net-return figure gives farmers a clearer picture of whether a sale is likely to profit after storage and transport costs, supporting more informed income decisions."),
        ("SDG 9 · Innovation & Infrastructure", "Target 9.c", GRAIN,
         "Delivered through USSD, the tool is accessible on basic mobile phones, no internet or smartphone required."),
        ("SDG 10 · Reduced Inequalities", "Target 10.2", "#7FA6C9",
         "By prioritising feature phones and local-language access, the platform reaches farmers who are often excluded from digital agricultural services."),
    ]
    for title, tgt, col, body in sdgs:
        st.markdown(f"""<div class='panel' style='border-left:4px solid {col}'>
        <b style='color:{col};font-size:1.05rem'>{title}</b><span class='tag'>{tgt}</span><br>
        <span>{body}</span></div>""", unsafe_allow_html=True)
    st.markdown("### Built on WFP's existing investments")
    st.markdown(f"""<div class='panel'>
    PostHarvest IQ builds on the market intelligence WFP already collects through its
    <b style='color:{GOLD}'>VAM price monitoring</b>. Rather than creating a new data-collection programme,
    it transforms existing market information into practical guidance a farmer can use when deciding
    whether to sell now or store.</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class='panel'>
    The concept aligns with WFP's <b>Country Strategic Plan 2024–2028</b>, particularly its focus on
    resilient livelihoods and smallholder support, and complements initiatives such as
    <b>Purchase for Progress</b> by encouraging informed post-harvest decisions and better grain management.</div>""", unsafe_allow_html=True)