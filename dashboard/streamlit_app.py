"""
dashboard/streamlit_app.py — PostHarvest IQ
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
ACTIVITY_ENDPOINT = f"{API_BASE}/recommendations/activity"
STORAGE_ENDPOINT = f"{API_BASE}/storage"
TIMEOUT = 20

INK, PANEL = "#14110E", "#1E1A15"
GOLD, GRAIN, CREAM, MUTE = "#E8A33D", "#D4B483", "#F2E9DC", "#9C8F7A"
GREEN, RED, AMBER = "#3E8E5A", "#C44536", "#D9820B"
DEC = {"STORE": (GREEN, "Store"), "SELL_NOW": (RED, "Sell now"),
       "SELL_PARTIAL": (AMBER, "Sell half"), "UNAVAILABLE": (MUTE, "—")}
DISTRICTS = ["Tamale", "Bolgatanga", "Wa"]
CROPS = ["Maize", "Millet", "Sorghum"]

STORAGE_FALLBACK = {
    "Tamale":     [{"name": "GCX Tamale Warehouse",  "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Tamale",   "crops": ["Maize", "Sorghum"]}],
    "Bolgatanga": [{"name": "GCX Bolga Warehouse",   "distance_km": 0.75, "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Bolga",    "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Sandema Warehouse", "distance_km": 44.9, "cost_per_bag": 0.80, "contact_number": "0594164451", "type": "Ghana Commodity Exchange", "district": "Sandema",  "crops": ["Maize", "Sorghum"]}],
    "Wa":         [{"name": "GCX Wa Warehouse",      "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Wa",       "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Tumu Warehouse",    "distance_km": 68.5, "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Tumu",     "crops": ["Maize", "Sorghum"]}],
}



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
                f"<p style='color:{MUTE};font-size:.78rem;margin-top:0'>3 crops &nbsp;·&nbsp; Maize, Millet, Sorghum<br>3 districts · Tamale, Bolgatanga, Wa</p>", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["Live Activity", "Storage"])

with tab1:
    st.markdown(f"""<div class='hero'><h1>Platform Overview</h1>
    <p>Real-time visibility into every advisory session — crop, district, recommendation issued, and time of contact.</p></div>""", unsafe_allow_html=True)
    data, src = load_activity()
    top = st.columns([3, 1])
    with top[1]:
        if st.button("↻ Refresh"):
            st.cache_data.clear(); st.rerun()
    if data and data.get("total_sessions", 0) > 0:
        with top[0]:
            st.success(f"Connected · live data · {_dt.datetime.now():%H:%M:%S}")
        c = st.columns(4)
        c[0].markdown(stat(data["total_sessions"], "advisory sessions"), unsafe_allow_html=True)
        c[1].markdown(stat("3", "languages supported"), unsafe_allow_html=True)
        c[2].markdown(stat(data.get("by_decision", {}).get("SELL_NOW", 0), "sell now"), unsafe_allow_html=True)
        c[3].markdown(stat(data.get("by_decision", {}).get("STORE", 0), "store"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Recent decisions")
        feed = "".join(
            f"<div class='feedrow'><div><span class='dot' style='background:{DEC.get(r['decision'],DEC['UNAVAILABLE'])[0]}'></span>"
            f"<b>{r['crop']}</b> · {r['district']}</div>"
            f"<div style='color:{MUTE};font-size:.85rem'>{r['phone']}</div>"
            f"<div>{badge(r['decision'])} <span style='color:{MUTE};font-size:.8rem;margin-left:8px'>{ago(r['when'])}</span></div></div>"
            for r in data.get("recent", []))
        empty_msg = "<p style='padding:1rem'>No sessions recorded yet.</p>"
        st.markdown(f"<div class='panel' style='padding:.3rem 0'>{feed or empty_msg}</div>", unsafe_allow_html=True)
        bc = data.get("by_crop", {})
        bd = data.get("by_district", {})
        bde = data.get("by_decision", {})
        recent_rows = data.get("recent", [])

        if bc or bd:
            st.markdown("### Usage analysis")
            _ch1, _ch2 = st.columns(2)
            with _ch1:
                if bc:
                    st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>Sessions by crop</p>", unsafe_allow_html=True)
                    fig_crop = go.Figure(go.Bar(
                        x=list(bc.keys()), y=list(bc.values()),
                        marker_color=GOLD,
                        text=list(bc.values()), textposition="outside",
                    ))
                    fig_crop.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                           height=260, margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
                    fig_crop.update_xaxes(gridcolor="#2E2820")
                    fig_crop.update_yaxes(gridcolor="#2E2820", title="sessions")
                    st.plotly_chart(fig_crop, use_container_width=True)
            with _ch2:
                if bd:
                    st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>Sessions by district</p>", unsafe_allow_html=True)
                    fig_dist = go.Figure(go.Bar(
                        x=list(bd.keys()), y=list(bd.values()),
                        marker_color=GRAIN,
                        text=list(bd.values()), textposition="outside",
                    ))
                    fig_dist.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                           height=260, margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
                    fig_dist.update_xaxes(gridcolor="#2E2820")
                    fig_dist.update_yaxes(gridcolor="#2E2820", title="sessions")
                    st.plotly_chart(fig_dist, use_container_width=True)

        if bde:
            st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>Recommendation distribution</p>", unsafe_allow_html=True)
            _dec_labels = list(bde.keys())
            _dec_vals   = list(bde.values())
            _dec_colors = [DEC.get(k, DEC["UNAVAILABLE"])[0] for k in _dec_labels]
            _dec_display = [DEC.get(k, DEC["UNAVAILABLE"])[1] for k in _dec_labels]
            fig_dec = go.Figure(go.Bar(
                x=_dec_display, y=_dec_vals,
                marker_color=_dec_colors,
                text=_dec_vals, textposition="outside",
            ))
            fig_dec.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                                   height=240, margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
            fig_dec.update_xaxes(gridcolor="#2E2820")
            fig_dec.update_yaxes(gridcolor="#2E2820", title="sessions")
            st.plotly_chart(fig_dec, use_container_width=True)

        if recent_rows:
            lang_counts = {}
            for _r in recent_rows:
                _lang = _r.get("language") or "en"
                lang_counts[_lang] = lang_counts.get(_lang, 0) + 1
            _lang_labels = {"en": "English", "dag": "Dagbani", "hau": "Hausa"}
            if lang_counts:
                st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin:.6rem 0 .4rem 0'>Language distribution</p>", unsafe_allow_html=True)
                lang_html = " &nbsp; ".join(
                    f"<span style='background:{PANEL};border:1px solid #2E2820;border-radius:6px;padding:.3rem .8rem;font-size:.83rem'>"
                    f"<b style='color:{CREAM}'>{_lang_labels.get(k, k)}</b> "
                    f"<span style='color:{GOLD};font-weight:700'>{v}</span></span>"
                    for k, v in sorted(lang_counts.items(), key=lambda x: -x[1])
                )
                st.markdown(lang_html, unsafe_allow_html=True)
    else:
        with top[0]:
            st.warning("No sessions recorded yet — dial the USSD code to generate the first advisory.")


with tab2:
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
    if not locs:
        fallback_all = STORAGE_FALLBACK.get(d, [])
        locs = [l for l in fallback_all if c in l.get("crops", [])]
        src = "offline"
    if locs:
        locs = sorted(locs, key=lambda x: float(x.get("distance_km", 9e9)))
        src_label = "" if src == "live" else f" <span style='color:{MUTE};font-size:.75rem'>(cached)</span>"
        st.markdown(f"<p style='color:{MUTE};margin-bottom:1rem'>{len(locs)} verified "
                    f"warehouse{'s' if len(locs)!=1 else ''} that accept {c}, nearest first.{src_label}</p>",
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
        warehouses we mapped accept maize and sorghum — millet has no verified storage in our registry,
        which is a visibility gap in itself.)</span></div>""", unsafe_allow_html=True)
