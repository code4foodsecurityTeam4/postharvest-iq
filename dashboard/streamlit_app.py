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


tab1, tab2, tab3 = st.tabs(["Live Activity", "Recommendations", "Storage"])

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
        c[1].markdown(stat("3", "languages supported"), unsafe_allow_html=True)
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
        bd = data.get("by_district", {})
        bde = data.get("by_decision", {})
        recent_rows = data.get("recent", [])

        if bc or bd:
            st.markdown("### Breakdown")
            _ch1, _ch2 = st.columns(2)
            with _ch1:
                if bc:
                    st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>By crop</p>", unsafe_allow_html=True)
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
                    st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>By district</p>", unsafe_allow_html=True)
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
            st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:.4rem'>Decisions given</p>", unsafe_allow_html=True)
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
                st.markdown(f"<p style='color:{GRAIN};font-size:.75rem;letter-spacing:1px;text-transform:uppercase;margin:.6rem 0 .4rem 0'>Language used (recent sessions)</p>", unsafe_allow_html=True)
                lang_html = " &nbsp; ".join(
                    f"<span style='background:{PANEL};border:1px solid #2E2820;border-radius:6px;padding:.3rem .8rem;font-size:.83rem'>"
                    f"<b style='color:{CREAM}'>{_lang_labels.get(k, k)}</b> "
                    f"<span style='color:{GOLD};font-weight:700'>{v}</span></span>"
                    for k, v in sorted(lang_counts.items(), key=lambda x: -x[1])
                )
                st.markdown(lang_html, unsafe_allow_html=True)
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
