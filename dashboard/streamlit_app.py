"""
dashboard/streamlit_app.py — PostHarvest IQ
"""

import datetime as _dt
import os
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

try:
    API_BASE = st.secrets["API_BASE"]
except Exception:
    API_BASE = os.getenv("API_BASE", "https://postharvest-iq.onrender.com")
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
DISTRICTS = ["Tamale", "Bolgatanga", "Wa"]
CROPS = ["Maize", "Millet", "Sorghum"]
FALLBACK = [
    {"district": d, "crop": c, "decision": "SELL_NOW", "net_total": n, "current_price": p, "forecast_price": round(p*0.92, 2)}
    for d in DISTRICTS
    for c, p, n in [("Maize", 538.46, -925.6), ("Millet", 728.0, -1230.0), ("Sorghum", 741.2, -1250.0)]
]

STORAGE_FALLBACK = {
    "Tamale":     [{"name": "GCX Tamale Warehouse",  "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Tamale",   "crops": ["Maize", "Sorghum"]}],
    "Bolgatanga": [{"name": "GCX Bolga Warehouse",   "distance_km": 0.75, "cost_per_bag": 0.80, "contact_number": "0504444065", "type": "Ghana Commodity Exchange", "district": "Bolga",    "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Sandema Warehouse", "distance_km": 44.9, "cost_per_bag": 0.80, "contact_number": "0594164451", "type": "Ghana Commodity Exchange", "district": "Sandema",  "crops": ["Maize", "Sorghum"]}],
    "Wa":         [{"name": "GCX Wa Warehouse",      "distance_km": 0.0,  "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Wa",       "crops": ["Maize", "Sorghum"]},
                   {"name": "GCX Tumu Warehouse",    "distance_km": 68.5, "cost_per_bag": 0.80, "contact_number": "0594164424", "type": "Ghana Commodity Exchange", "district": "Tumu",     "crops": ["Maize", "Sorghum"]}],
}


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
                f"<p style='color:{MUTE};font-size:.78rem;margin-top:0'>3 crops &nbsp;·&nbsp; Maize, Millet, Sorghum<br>3 districts · Tamale, Bolgatanga, Wa</p>", unsafe_allow_html=True)


tab1, tab2, tab3, tab4 = st.tabs(["Live Activity", "Recommendations", "Storage", "Data & Models"])

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


with tab2:
    st.markdown(f"""<div class='hero'>
    <h1>What the engine decides</h1>
    <p>XGBoost trained across 5 algorithms — best selected by validation F1.
    9 crop-district pairs, priced live. Switch months to watch the advice shift with the season.</p>
    </div>""", unsafe_allow_html=True)

    ctl_l, ctl_r = st.columns([4, 1])
    with ctl_l:
        sel = st.selectbox(
            "Season:",
            MONTHS,
            index=0,
            help="Current = live market data. Pick a month to simulate what the engine would say at that point in the season.",
        )
    month = None if sel == CURRENT_LABEL else MONTHS.index(sel)
    rows, src = load_summary(month)
    df = pd.DataFrame(rows)
    lab = CURRENT_LABEL if month is None else MONTHS[month]
    with ctl_r:
        st.markdown("<div style='margin-top:1.75rem'>", unsafe_allow_html=True)
        if st.button("↻ Refresh", key="rec_refresh"):
            st.cache_data.clear(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if src == "live":
        st.success(f"Live · {lab} · {_dt.datetime.now():%H:%M:%S}")
    else:
        st.warning("Showing sample snapshot — API unreachable. Numbers are illustrative.")

    if not df.empty and "decision" in df.columns:
        sc = st.columns(4)
        sc[0].markdown(stat(len(df), "crop × district pairs"), unsafe_allow_html=True)
        sc[1].markdown(stat(int((df["decision"] == "STORE").sum()), "store now"), unsafe_allow_html=True)
        sc[2].markdown(stat(int((df["decision"] == "SELL_NOW").sum()), "sell now"), unsafe_allow_html=True)
        sc[3].markdown(stat(int((df["decision"] == "SELL_PARTIAL").sum()), "sell partial"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Decision matrix")
        st.markdown(f"<p style='color:{MUTE};margin-bottom:1.2rem'>One call per crop per district. Border colour = the recommendation. Net return is on a 20-bag harvest after storage cost.</p>", unsafe_allow_html=True)

        for district in DISTRICTS:
            d_rows = df[df["district"] == district]
            st.markdown(f"<p style='color:{GRAIN};font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;margin:.4rem 0 .5rem 0'>{district}</p>", unsafe_allow_html=True)
            dc = st.columns(3)
            for i, crop in enumerate(CROPS):
                match = d_rows[d_rows["crop"] == crop]
                if match.empty:
                    continue
                r = match.iloc[0]
                dec = r.get("decision") or "UNAVAILABLE"
                dec_col, dec_lbl = DEC.get(dec, DEC["UNAVAILABLE"])
                net = float(r.get("net_total") or 0)
                net_col = GREEN if net > 0 else RED
                net_str = f"{'+'if net>0 else ''}GHS {abs(round(net)):,}"
                cur = cedis(r.get("current_price"))
                fcast = cedis(r.get("forecast_price"))
                dc[i].markdown(f"""<div style='background:{PANEL};border:1px solid #2E2820;border-top:3px solid {dec_col};
                border-radius:10px;padding:1rem 1.1rem;margin-bottom:.7rem'>
                <div style='font-size:.72rem;color:{MUTE};letter-spacing:1.2px;text-transform:uppercase;margin-bottom:.55rem'>{crop}</div>
                <span class='pill' style='background:{dec_col}'>{dec_lbl}</span>
                <div style='margin-top:.9rem;display:grid;grid-template-columns:auto 1fr;row-gap:.25rem;column-gap:.5rem;font-size:.8rem'>
                  <span style='color:{MUTE}'>Today</span><span style='color:{CREAM};text-align:right'>{cur}</span>
                  <span style='color:{MUTE}'>Forecast</span><span style='color:{CREAM};text-align:right'>{fcast}</span>
                  <span style='color:{MUTE}'>Net</span><span style='color:{net_col};font-weight:600;text-align:right'>{net_str}</span>
                </div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Net return on 20 bags")
        st.markdown(f"<p style='color:{MUTE};margin-bottom:.6rem'>Revenue gain or loss from storing until the forecast month, minus GHS 0.80/bag/month storage cost.</p>", unsafe_allow_html=True)

        net_labels = [f"{r['district'][:3]} · {r['crop'][:3]}" for _, r in df.iterrows()]
        net_values = [float(r.get("net_total") or 0) for _, r in df.iterrows()]
        bar_colors  = [GREEN if v > 0 else RED for v in net_values]
        bar_text    = [f"GHS {v:,.0f}" for v in net_values]

        fig_net = go.Figure(go.Bar(
            x=net_labels, y=net_values,
            marker_color=bar_colors,
            text=bar_text, textposition="outside",
            textfont=dict(color=CREAM, size=10),
            cliponaxis=False,
        ))
        fig_net.add_hline(y=0, line_color=MUTE, line_width=1)
        fig_net.update_layout(
            plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
            height=340, margin=dict(t=40, b=10, l=10, r=10),
            showlegend=False, yaxis_title="GHS",
        )
        fig_net.update_xaxes(gridcolor="#2E2820", tickfont=dict(size=11))
        fig_net.update_yaxes(gridcolor="#2E2820", zeroline=False)
        st.plotly_chart(fig_net, use_container_width=True)

        lstm_rows = [r for _, r in df.iterrows() if r.get("method") == "lstm"]
        if lstm_rows:
            gaps = [float(r["current_price"]) - float(r["forecast_price"])
                    for r in lstm_rows if r.get("current_price") and r.get("forecast_price")]
            avg_gap = round(sum(gaps) / len(gaps)) if gaps else 304
        else:
            avg_gap = 304  # known gap from live data

        st.markdown("<br>", unsafe_allow_html=True)
        gap_l, gap_r = st.columns([3, 2])

        with gap_l:
            st.markdown(f"""<div style='background:{PANEL};border:1px solid #2E2820;border-left:4px solid {AMBER};
            border-radius:12px;padding:1.6rem 1.8rem'>
            <div style='font-size:.68rem;letter-spacing:1.5px;text-transform:uppercase;color:{AMBER};margin-bottom:.7rem'>The data gap · and the funding ask</div>
            <div style='font-family:Fraunces,serif;font-size:1.55rem;font-weight:900;color:{CREAM};line-height:1.25;margin-bottom:1.1rem'>
            Our LSTM was trained on prices from a different era of Ghana's cereal market.</div>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin-bottom:1.1rem'>
              <div style='background:{INK};border-radius:8px;padding:.85rem 1rem'>
                <div style='font-size:.7rem;color:{MUTE};margin-bottom:.3rem'>Training data · 2006–2023</div>
                <div style='font-family:Fraunces,serif;font-size:1.4rem;font-weight:900;color:{GRAIN}'>GHS 95–200</div>
              </div>
              <div style='background:{INK};border-radius:8px;padding:.85rem 1rem'>
                <div style='font-size:.7rem;color:{MUTE};margin-bottom:.3rem'>Current market · 2024–2026</div>
                <div style='font-family:Fraunces,serif;font-size:1.4rem;font-weight:900;color:{AMBER}'>GHS 490–760</div>
              </div>
            </div>
            <div style='font-size:.88rem;color:{GRAIN};line-height:1.75'>
            Average gap: <b style='color:{AMBER};font-size:1.05rem'>GHS {avg_gap:,} per bag</b>
            &nbsp;·&nbsp; <b style='color:{CREAM}'>GHS {avg_gap * 20:,} on 20 bags</b><br><br>
            This is not a model failure. It is the precise distance between
            what our model was trained to know and what the market is doing today.<br><br>
            <b style='color:{CREAM}'>One dataset closes it.</b> Updated WFP price data from 2023 onwards.
            The LSTM retrains in under one hour. The forecast column becomes a live signal
            every farmer can act on.<br><br>
            <span style='color:{AMBER};font-weight:600;font-size:.92rem'>This is the core of what we are seeking funding to secure.</span>
            </div></div>""", unsafe_allow_html=True)

        with gap_r:
            fig_gap = go.Figure()
            fig_gap.add_trace(go.Bar(
                name="Training era", x=["GHS / bag"],
                y=[105], base=[95],
                marker_color=GRAIN, marker_line_width=0, width=0.45,
                text="GHS 95–200<br>Training data<br>2006–2023",
                textposition="inside", textfont=dict(color=INK, size=11),
            ))
            fig_gap.add_trace(go.Bar(
                name="Uncharted", x=["GHS / bag"],
                y=[290], base=[200],
                marker_color="#252018",
                marker_line=dict(width=1, color="#3A3020"),
                width=0.45,
                text="— gap —<br>no data",
                textposition="inside", textfont=dict(color=MUTE, size=10),
            ))
            fig_gap.add_trace(go.Bar(
                name="Current market", x=["GHS / bag"],
                y=[270], base=[490],
                marker_color=AMBER, marker_line_width=0, width=0.45,
                text="GHS 490–760<br>Today's prices<br>2024–2026",
                textposition="inside", textfont=dict(color=INK, size=11),
            ))
            fig_gap.update_layout(
                barmode="stack",
                plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=CREAM,
                height=380, margin=dict(t=20, b=10, l=10, r=10),
                showlegend=False, yaxis_title="GHS per bag",
                yaxis=dict(range=[0, 820], gridcolor="#2E2820", tickprefix="GHS "),
            )
            fig_gap.update_xaxes(showticklabels=False, showgrid=False)
            st.plotly_chart(fig_gap, use_container_width=True)


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


with tab4:
    st.markdown(f"<h2 style='color:{GOLD}'>Data &amp; Models</h2>", unsafe_allow_html=True)

    # ── Data at a glance ───────────────────────────────────────────────────────
    _da, _db, _dc, _dd = st.columns(4)
    for _col, _val, _lbl in zip(
        [_da, _db, _dc, _dd],
        ["1,744", "17 yrs", "5", "3"],
        ["price records", "Jan 2006 – Jul 2023", "markets", "commodities"],
    ):
        with _col:
            st.markdown(f"""<div class='panel' style='text-align:center;padding:.9rem .5rem'>
                <div style='color:{GOLD};font-size:1.8rem;font-weight:700;line-height:1'>{_val}</div>
                <div style='color:{MUTE};font-size:.8rem;margin-top:.3rem'>{_lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown(f"<p style='color:{MUTE};font-size:.82rem;margin-top:.4rem'>Sources: WFP Price Monitor (wholesale prices) &nbsp;·&nbsp; FAO Ghana Exchange Rates &nbsp;·&nbsp; FAO Producer Price Index</p>", unsafe_allow_html=True)

    st.divider()

    # ── Training split (visual bar) ────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>Training Split &amp; Features</h3>", unsafe_allow_html=True)
    _split_fig = go.Figure(go.Bar(
        x=[70, 15, 15], y=["Data split"],
        orientation='h',
        marker_color=[GREEN, AMBER, RED],
        text=["Train · 70%  (Jan 2006 – Aug 2018)", "Val · 15%  (Aug 2018 – Mar 2021)", "Test · 15%  (Mar 2021 – Jul 2023)"],
        textposition="inside", insidetextanchor="middle",
        hoverinfo="skip",
    ))
    _split_fig.update_layout(
        plot_bgcolor=PANEL, paper_bgcolor=PANEL,
        font=dict(color=CREAM, size=12),
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=70, barmode="stack",
    )
    st.plotly_chart(_split_fig, use_container_width=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.8rem;margin-top:-.5rem'>Chronological — no shuffling, no future data in training.</p>", unsafe_allow_html=True)

    _fc1, _fc2 = st.columns(2)
    def _chip(text, color): return f"<span style='background:{color}22;color:{color};border:1px solid {color}55;border-radius:4px;padding:.15rem .45rem;font-size:.75rem;margin:.15rem .1rem;display:inline-block'>{text}</span>"
    with _fc1:
        st.markdown(f"""<div class='panel'>
            <b style='color:{GREEN}'>XGBoost</b> <span style='color:{MUTE};font-size:.8rem'>· 22 features</span><br><br>
            {_chip("price lag 1/2/3", GRAIN)}{_chip("rolling mean", GRAIN)}{_chip("rolling std", GRAIN)}{_chip("% change", GRAIN)}
            {_chip("month sin/cos", GRAIN)}{_chip("harvest flag", GRAIN)}{_chip("lean flag", GRAIN)}{_chip("price vs annual", GRAIN)}
            {_chip("price YoY", GRAIN)}{_chip("exchange rate", GRAIN)}{_chip("PPI", GRAIN)}
            {_chip("market (OHE ×5)", GOLD)}{_chip("commodity (OHE ×3)", GOLD)}
        </div>""", unsafe_allow_html=True)
    with _fc2:
        st.markdown(f"""<div class='panel'>
            <b style='color:{AMBER}'>LSTM</b> <span style='color:{MUTE};font-size:.8rem'>· 10 features &nbsp;·&nbsp; 12-month window</span><br><br>
            {_chip("price", GRAIN)}{_chip("price lag 1/2/3", GRAIN)}{_chip("rolling mean", GRAIN)}{_chip("rolling std", GRAIN)}
            {_chip("month sin/cos", GRAIN)}{_chip("exchange rate", GRAIN)}{_chip("PPI", GRAIN)}
            <br><br><span style='color:{MUTE};font-size:.78rem'>LSTM takes sequential price history — no OHE market/commodity or season flags needed; seasonality is captured through the cyclical month encoding and the sequence itself.</span>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Label derivation ───────────────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>How Decision Labels Were Created</h3>", unsafe_allow_html=True)
    st.markdown(f"""<div class='panel'>
        <span style='color:{MUTE};font-size:.85rem'>Every row in the dataset was labelled using this formula before training:</span><br><br>
        <div style='background:{INK};border-radius:6px;padding:.7rem 1.1rem;font-family:monospace;font-size:.88rem;color:{CREAM};line-height:2'>
            net_per_bag &nbsp;= &nbsp;(price_next_month &minus; price_current)
            &nbsp;&minus;&nbsp; (GHS&nbsp;0.80 &times; 1.5 months)
            &nbsp;&minus;&nbsp; <span style='color:{AMBER}'>transport estimate</span>
        </div><br>
        <div style='display:flex;gap:.75rem'>
            <div style='flex:1;background:{INK};border-left:3px solid {GREEN};border-radius:4px;padding:.6rem .9rem;text-align:center'>
                <b style='color:{GREEN};font-size:1rem'>STORE</b><br>
                <span style='color:{MUTE};font-size:.8rem'>net &gt; GHS 20</span>
            </div>
            <div style='flex:1;background:{INK};border-left:3px solid {AMBER};border-radius:4px;padding:.6rem .9rem;text-align:center'>
                <b style='color:{AMBER};font-size:1rem'>SELL_PARTIAL</b><br>
                <span style='color:{MUTE};font-size:.8rem'>GHS 5 &lt; net ≤ GHS 20</span>
            </div>
            <div style='flex:1;background:{INK};border-left:3px solid {RED};border-radius:4px;padding:.6rem .9rem;text-align:center'>
                <b style='color:{RED};font-size:1rem'>SELL_NOW</b><br>
                <span style='color:{MUTE};font-size:.8rem'>net ≤ GHS 5</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Imbalance method comparison ────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>Handling Class Imbalance — Method Comparison</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.83rem'>SELL_NOW dominates the dataset. Two approaches were tested; the winner was used for final training.</p>", unsafe_allow_html=True)
    _im1, _im2 = st.columns(2)
    with _im1:
        st.markdown(f"""<div class='panel' style='border:1px solid {MUTE}55;opacity:.7'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <b style='color:{MUTE}'>class_weight='balanced'</b>
                <span style='color:{MUTE};font-size:.75rem;background:{INK};padding:.2rem .5rem;border-radius:4px'>Not selected</span>
            </div><br>
            <span style='color:{MUTE};font-size:.85rem'>Tells the model to penalise errors on minority classes more during training. No new data created — just reweights the loss function.</span><br><br>
            <span style='color:{MUTE};font-size:.8rem'>Simple · no data augmentation · lower validation F1</span>
        </div>""", unsafe_allow_html=True)
    with _im2:
        st.markdown(f"""<div class='panel' style='border:2px solid {GREEN}'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <b style='color:{GREEN}'>SMOTE</b>
                <span style='color:{GREEN};font-size:.75rem;background:{GREEN}22;padding:.2rem .5rem;border-radius:4px'>✓ Selected</span>
            </div><br>
            <span style='color:{CREAM};font-size:.85rem'>Synthesises new minority-class examples by interpolating between existing ones — so the model genuinely sees more STORE and SELL_PARTIAL cases.</span><br><br>
            <span style='color:{MUTE};font-size:.8rem'>Higher validation F1 · balanced training set · selected for final run</span>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Classifier comparison ──────────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>5 Classifiers Compared — Why XGBoost Won</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.83rem'>All five trained with the same split and SMOTE. Model selected on <b>validation F1</b> — not test F1 — to avoid peeking at held-out data.</p>", unsafe_allow_html=True)
    _cls_names  = ["XGBoost", "Random Forest", "Gradient Boosting", "Decision Tree", "Logistic Regression"]
    _val_f1s    = [0.3565, 0.3190, 0.3248, 0.2865, 0.2086]
    _test_f1s   = [0.2464, 0.3477, 0.1920, 0.2356, 0.3064]
    _bar_colors = [GREEN if n == "XGBoost" else GRAIN for n in _cls_names]
    _fig_cls = go.Figure()
    _fig_cls.add_trace(go.Bar(
        x=_cls_names, y=_val_f1s, name="Validation F1 (selection basis)",
        marker_color=_bar_colors, opacity=0.95,
        text=[f"{v:.3f}" for v in _val_f1s], textposition="outside",
    ))
    _fig_cls.add_trace(go.Bar(
        x=_cls_names, y=_test_f1s, name="Test F1 (held-out)",
        marker_color=_bar_colors, opacity=0.4,
        text=[f"{v:.3f}" for v in _test_f1s], textposition="outside",
    ))
    _fig_cls.update_layout(
        barmode="group", plot_bgcolor=PANEL, paper_bgcolor=PANEL,
        font=dict(color=CREAM), margin=dict(t=30, b=10, l=10, r=10),
        legend=dict(bgcolor=INK, bordercolor=MUTE, borderwidth=1),
        yaxis=dict(title="Macro F1", gridcolor=INK, range=[0, 0.50]),
        xaxis=dict(gridcolor=INK),
        height=300,
    )
    _fig_cls.add_annotation(x="XGBoost", y=0.3565 + 0.06, text="Selected", showarrow=False,
                            font=dict(color=GREEN, size=11))
    st.plotly_chart(_fig_cls, use_container_width=True)
    with st.expander("Why macro F1 and not accuracy?"):
        st.markdown(f"<span style='color:{MUTE}'>With imbalanced classes, a model that always predicts SELL_NOW gets high accuracy but misses STORE and SELL_PARTIAL entirely. <b style='color:{CREAM}'>Macro F1</b> averages the F1 score equally across all three classes — the model only scores well if it learns all three.</span>", unsafe_allow_html=True)

    st.divider()

    # ── Forecast model comparison ──────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>3 Forecast Models Compared — Why LSTM Won</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTE};font-size:.83rem'>Lower MAE = better. Tree models treat each month independently; LSTM reads the full 12-month sequence.</p>", unsafe_allow_html=True)
    _fcast_models = ["RF Regressor", "XGBoost Regressor", "LSTM"]
    _fcast_maes   = [347.85, 340.25, 280.29]
    _fcast_colors = [MUTE, MUTE, GREEN]
    _fig_fcast = go.Figure(go.Bar(
        x=_fcast_maes, y=_fcast_models,
        orientation='h',
        marker_color=_fcast_colors,
        text=[f"MAE  {v:.0f} GHS" for v in _fcast_maes],
        textposition="outside",
    ))
    _fig_fcast.update_layout(
        plot_bgcolor=PANEL, paper_bgcolor=PANEL,
        font=dict(color=CREAM), margin=dict(t=20, b=20, l=10, r=80),
        xaxis=dict(title="Mean Absolute Error (GHS) — lower is better", gridcolor=INK),
        yaxis=dict(gridcolor=INK),
        height=220,
    )
    _fig_fcast.add_annotation(x=280.29 + 12, y="LSTM", text="Selected", showarrow=False,
                              font=dict(color=GREEN, size=11), xanchor="left")
    st.plotly_chart(_fig_fcast, use_container_width=True)

    st.divider()

    # ── LSTM performance ───────────────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{CREAM}'>LSTM Forecast Performance on Test Set</h3>", unsafe_allow_html=True)
    _lc1, _lc2, _lc3, _lc4, _lc5 = st.columns(5)
    _lstm_metrics = [
        ("MAE", "GHS 280", "Mean absolute error"),
        ("RMSE", "GHS 312", "Root mean square error"),
        ("MAPE", "47.65%", "Mean abs. % error"),
        ("R²", "−3.15", "Underperforms flat mean"),
        ("Dir. Accuracy", "61.1%", "Correct price direction"),
    ]
    for _col, (_label, _value, _note) in zip([_lc1, _lc2, _lc3, _lc4, _lc5], _lstm_metrics):
        with _col:
            _c = RED if _label in ("MAE", "RMSE", "MAPE", "R²") else AMBER
            st.markdown(f"""<div class='panel' style='text-align:center;padding:.7rem .4rem'>
                <div style='color:{MUTE};font-size:.7rem;text-transform:uppercase'>{_label}</div>
                <div style='color:{_c};font-size:1.25rem;font-weight:700;margin:.2rem 0'>{_value}</div>
                <div style='color:{MUTE};font-size:.68rem'>{_note}</div>
            </div>""", unsafe_allow_html=True)

    _sh1, _sh2 = st.columns(2)
    with _sh1:
        st.markdown(f"""<div class='panel' style='border-left:4px solid {AMBER};margin-top:.75rem'>
            <b style='color:{AMBER}'>Why errors are large</b><br>
            <span style='color:{MUTE};font-size:.85rem'>Training range: <b style='color:{CREAM}'>GHS 95–200</b><br>
            Current prices: <b style='color:{CREAM}'>GHS 490–760</b> &nbsp;(3× higher)<br>
            Caused by post-2020 inflation &amp; 2022 debt crisis. The model has never seen these price levels.</span>
        </div>""", unsafe_allow_html=True)
    with _sh2:
        st.markdown(f"""<div class='panel' style='border-left:4px solid {GREEN};margin-top:.75rem'>
            <b style='color:{GREEN}'>What still works</b><br>
            <span style='color:{MUTE};font-size:.85rem'>Directional accuracy: <b style='color:{CREAM}'>61.1%</b> — the model correctly reads whether prices will rise or fall more often than not. Re-training with post-2023 data is the single fix that would close this gap.</span>
        </div>""", unsafe_allow_html=True)

