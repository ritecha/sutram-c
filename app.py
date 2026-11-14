import math
import pandas as pd
import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import folium
from pyvis.network import Network
from streamlit_folium import st_folium
from core.adapter import b_score_all, b_contrib, b_resolve_all

st.set_page_config(
    page_title="SUTRAM · Evidence Correlation",
    page_icon="🛰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════ NEON THEME ═══════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --neon-cyan: #00ffcc; --neon-pink: #ff3caa; --neon-lime: #b4ff2e;
  --neon-violet: #b366ff; --neon-amber: #ffb320;
  --bg-0: #05050f; --bg-1: #0b0b1e; --bg-2: #141428;
  --text: #e6e6ff; --muted: #8a8ab0; --border: rgba(255,255,255,0.08);
}
html, body, [class*="css"] { font-family: 'Space Grotesk', system-ui, sans-serif !important; }
.stApp {
  background:
    radial-gradient(circle at 12% 8%, rgba(0,255,204,0.10), transparent 42%),
    radial-gradient(circle at 88% 12%, rgba(255,60,170,0.10), transparent 42%),
    radial-gradient(circle at 50% 95%, rgba(179,102,255,0.10), transparent 45%),
    var(--bg-0) !important;
  color: var(--text) !important;
}

/* Header stays visible (needed for sidebar toggle), only menu/footer hidden */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] {
  background: transparent !important;
  height: 2.5rem !important;
}

/* Sidebar — styled, keeps native left position */
[data-testid="stSidebar"] > div:first-child {
  background: linear-gradient(180deg, rgba(11,11,30,0.98), rgba(5,5,15,0.98)) !important;
  border-right: 1px solid var(--border) !important;
  backdrop-filter: blur(12px);
}

/* Expand/collapse toggle — always visible, neon glow */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
  z-index: 99999 !important;
  background: var(--bg-2) !important;
  border: 1px solid var(--neon-cyan) !important;
  border-radius: 10px !important;
  box-shadow: 0 0 16px -2px var(--neon-cyan) !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
  fill: var(--neon-cyan) !important;
  color: var(--neon-cyan) !important;
}

section.main { padding: 1rem 2rem !important; }

/* ── HERO ── */
.hero { padding: 2rem 0 1.5rem 0; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; }
.hero h1 {
  font-size: 3.4rem; font-weight: 700; letter-spacing: -0.02em; margin: 0;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-violet), var(--neon-pink));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; text-shadow: 0 0 60px rgba(0,255,204,0.3);
}
.hero .tagline {
  color: var(--muted); font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem; letter-spacing: 0.18em; text-transform: uppercase; margin-top: 0.6rem;
}

/* ── KPI CARDS ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1.5rem 0 2rem 0; }
.kpi {
  background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border: 1px solid var(--border); border-radius: 16px;
  padding: 1.3rem 1.4rem; position: relative; overflow: hidden;
  transition: transform 0.2s, box-shadow 0.3s;
}
.kpi::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent, var(--neon-cyan));
  box-shadow: 0 0 20px var(--accent, var(--neon-cyan));
}
.kpi:hover { transform: translateY(-3px); box-shadow: 0 8px 32px -8px var(--accent, var(--neon-cyan)); }
.kpi-label {
  font-size: 0.68rem; letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--muted); font-family: 'JetBrains Mono', monospace;
}
.kpi-value { font-size: 2.2rem; font-weight: 700; color: var(--text); margin: 0.35rem 0; line-height: 1; }
.kpi-sub { font-size: 0.78rem; color: var(--muted); }
.kpi.cyan { --accent: var(--neon-cyan); } .kpi.pink { --accent: var(--neon-pink); }
.kpi.violet { --accent: var(--neon-violet); } .kpi.amber { --accent: var(--neon-amber); }

/* ── SECTION HEADERS ── */
.section-head {
  font-size: 1rem; font-weight: 600; letter-spacing: 0.1em;
  margin: 2rem 0 1rem 0; padding-left: 0.85rem;
  border-left: 3px solid var(--neon-cyan); text-transform: uppercase;
}

/* ── BUTTONS ── */
.stButton > button {
  background: linear-gradient(135deg, var(--neon-violet), var(--neon-pink)) !important;
  color: white !important; border: none !important; border-radius: 12px !important;
  font-weight: 600 !important; letter-spacing: 0.08em !important;
  padding: 0.65rem 1.5rem !important;
  box-shadow: 0 0 24px -4px var(--neon-violet) !important;
  transition: transform 0.15s, box-shadow 0.25s !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 0 40px -4px var(--neon-pink) !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, var(--neon-cyan), var(--neon-violet)) !important;
  color: #05050f !important;
  box-shadow: 0 0 24px -4px var(--neon-cyan) !important;
}

/* ── NAV PILLS ── */
[data-testid="stRadio"] > label { display: none; }
[data-testid="stRadio"] > div[role="radiogroup"] {
  display: flex !important; gap: 0.4rem; flex-wrap: wrap;
  background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 14px; padding: 0.4rem; width: fit-content; margin-bottom: 1rem;
}
[data-testid="stRadio"] div[role="radiogroup"] label {
  border-radius: 10px !important; padding: 0.55rem 1.3rem !important;
  color: var(--muted) !important; cursor: pointer !important;
  font-weight: 500 !important; transition: all 0.2s !important; margin: 0 !important;
  border: 1px solid transparent !important;
}
[data-testid="stRadio"] div[role="radiogroup"] label:hover {
  color: var(--text) !important; background: rgba(255,255,255,0.04) !important;
}
[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(135deg, rgba(0,255,204,0.15), rgba(179,102,255,0.15)) !important;
  border-color: var(--neon-cyan) !important; color: var(--neon-cyan) !important;
  box-shadow: 0 0 20px -4px var(--neon-cyan) !important;
}
[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child { display: none !important; }

/* ── SCORE RING ── */
.score-ring {
  width: 200px; height: 200px; border-radius: 50%;
  background: conic-gradient(var(--color) var(--pct), rgba(255,255,255,0.05) var(--pct));
  padding: 10px; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 60px -8px var(--color), inset 0 0 20px rgba(0,0,0,0.5);
  margin: 1rem auto; animation: pulse 3s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { filter: brightness(1); } 50% { filter: brightness(1.15); } }
.score-inner {
  width: 100%; height: 100%; border-radius: 50%;
  background: var(--bg-1); display: flex; flex-direction: column;
  align-items: center; justify-content: center; border: 1px solid var(--border);
}
.score-num { font-size: 2.6rem; font-weight: 700; color: var(--color); font-family: 'JetBrains Mono', monospace; line-height: 1; }
.score-label { font-size: 0.6rem; letter-spacing: 0.25em; color: var(--muted); margin-top: 0.4rem; text-transform: uppercase; }

/* ── ROLE BADGES ── */
.role-badge {
  display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace; border: 1px solid;
}
.role-victim { color: #4da3ff; border-color: #4da3ff; background: rgba(77,163,255,0.1); box-shadow: 0 0 12px -2px #4da3ff; }
.role-mule { color: var(--neon-pink); border-color: var(--neon-pink); background: rgba(255,60,170,0.1); box-shadow: 0 0 12px -2px var(--neon-pink); }
.role-recruiter { color: var(--neon-violet); border-color: var(--neon-violet); background: rgba(179,102,255,0.1); box-shadow: 0 0 12px -2px var(--neon-violet); }
.role-cash-out { color: var(--neon-amber); border-color: var(--neon-amber); background: rgba(255,179,32,0.1); box-shadow: 0 0 12px -2px var(--neon-amber); }
.role-onward { color: #ff8a4d; border-color: #ff8a4d; background: rgba(255,138,77,0.1); }
.role-account { color: var(--muted); border-color: var(--border); background: rgba(255,255,255,0.03); }

/* ── ALERTS ── */
.alert-success, .alert-info {
  padding: 1rem 1.2rem; border-radius: 12px; margin: 1rem 0;
  font-size: 0.95rem; line-height: 1.5;
}
.alert-success {
  background: linear-gradient(135deg, rgba(0,255,204,0.08), rgba(0,255,204,0.02));
  border: 1px solid rgba(0,255,204,0.3); color: var(--neon-cyan);
  box-shadow: 0 0 24px -8px var(--neon-cyan);
}
.alert-info { background: rgba(255,255,255,0.02); border: 1px solid var(--border); color: var(--muted); }

/* ── REASON CARDS ── */
.reason-item {
  padding: 0.65rem 0.95rem; border-left: 2px solid var(--neon-cyan);
  background: rgba(0,255,204,0.03); border-radius: 6px; margin: 0.4rem 0;
  font-size: 0.9rem; color: var(--text);
}

/* ── DATAFRAMES ── */
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 12px !important; overflow: hidden !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-0); }
::-webkit-scrollbar-thumb { background: linear-gradient(var(--neon-violet), var(--neon-cyan)); border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════ CONSTANTS ═══════════════════
FILES = ["entities", "transactions", "events", "links"]
COLORS = {
    "victim": "#4da3ff", "mule": "#ff3caa", "recruiter": "#b366ff",
    "cash-out": "#ffb320", "onward": "#ff8a4d", "account": "#9aa4b2",
}
WEIGHTS = {
    "Unique victims in": 0.25, "Velocity": 0.25, "Pass-through": 0.15,
    "Shared device/IP": 0.15, "New account": 0.10, "Linked complaints": 0.10,
}
VELOCITY_WINDOW_MIN = 120
MULE_THRESHOLD = 0.5
SOURCE_OF = {
    "Chat Message": "whatsapp_export", "Device Login": "device_log",
    "IP Registration": "ip_log", "ATM Proximity CCTV": "cctv_metadata",
    "ATM Access Log": "atm_log", "Network Alert": "bank_alert",
}
GRAPH_OPTIONS = """{
  "physics": {
    "barnesHut": {"gravitationalConstant": -12000, "springLength": 180, "springConstant": 0.04},
    "stabilization": {"enabled": true, "iterations": 250}
  },
  "nodes": {"font": {"color": "#e6e6ff", "face": "Space Grotesk", "size": 14}, "borderWidth": 2},
  "edges": {"font": {"color": "#8a8ab0", "size": 11, "strokeWidth": 0}},
  "interaction": {"hover": true, "tooltipDelay": 80}
}"""

# ═══════════════════ DATA / HELPERS ═══════════════════
def load_demo():
    return {k: pd.read_csv(f"data/{k}.csv") for k in FILES}

def role_from_text(r):
    r = str(r).lower()
    if "victim" in r: return "victim"
    if "mule" in r: return "mule"
    if "onward" in r: return "onward"
    if "suspect" in r or "recruit" in r: return "recruiter"
    if "cash" in r or "atm" in r: return "cash-out"
    return "account"

class Prepared: pass

def prepare(data):
    P = Prepared()
    ents = data["entities"].copy()
    txns = data["transactions"].copy()
    txns["timestamp"] = pd.to_datetime(txns["timestamp"])
    ev = data["events"].copy()
    ev["timestamp"] = pd.to_datetime(ev["timestamp"])
    P.ents, P.txns, P.links = ents, txns, data["links"].copy()
    P.acct2ent = dict(zip(ents["account_id"], ents["entity_id"]))
    P.ent2acct = dict(zip(ents["entity_id"], ents["account_id"]))
    P.name = dict(zip(ents["entity_id"], ents["name"]))
    P.role = {r.entity_id: role_from_text(r.role) for r in ents.itertuples()}
    alias = {}
    for r in ents.itertuples():
        for key in [r.entity_id, r.name, r.messy_aliases, r.account_id, r.associated_upi]:
            if pd.notna(key): alias[str(key).strip().lower()] = r.entity_id

    def map_entity(row):
        tid = row.get("true_entity_id")
        if pd.notna(tid): return tid
        return alias.get(str(row["entity_associated"]).strip().lower(), row["entity_associated"])

    e = pd.DataFrame({
        "timestamp": ev["timestamp"], "type": ev["event_type"],
        "alias": ev["entity_associated"], "entity_id": ev.apply(map_entity, axis=1),
        "source_doc": ev["event_type"].map(SOURCE_OF).fillna("evidence_log"),
        "ref": ev["event_id"], "details": ev["details"], "location": "",
        "latitude": ev["latitude"], "longitude": ev["longitude"],
        "ip_address": ev["ip_address"], "device": ev["shared_device_id"],
    })
    tx = pd.DataFrame({
        "timestamp": txns["timestamp"],
        "type": txns["channel"].eq("ATM_WITHDRAWAL").map({True: "withdrawal", False: "payment"}),
        "alias": txns["from_acct"], "entity_id": txns["from_acct"].map(lambda a: P.acct2ent.get(a, a)),
        "source_doc": "bank_upi_log", "ref": txns["txn_id"],
        "details": "₹" + txns["amount"].map("{:,.0f}".format) + " to " + txns["to_acct"],
        "location": txns["location"], "latitude": txns["latitude"], "longitude": txns["longitude"],
        "ip_address": None, "device": None,
    })
    allev = pd.concat([e, tx], ignore_index=True).sort_values("timestamp")
    allev["entity"] = allev["entity_id"].map(lambda x: P.name.get(x, x))
    P.ev = allev.reset_index(drop=True)
    return P

def hav(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1); dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))

def find_flags(ev):
    d = ev.dropna(subset=["latitude", "longitude"]).sort_values("timestamp")
    out = []
    for ent, g in d.groupby("entity"):
        rows = g.to_dict("records")
        for a, b in zip(rows, rows[1:]):
            km = hav(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
            if km < 50: continue
            hrs = (b["timestamp"] - a["timestamp"]).total_seconds() / 3600
            speed = km / hrs if hrs > 0 else float("inf")
            if speed > 900: kind = "Impossible travel"
            elif speed > 120: kind = "Fast travel (needs a flight)"
            else: continue
            out.append({"flag": kind, "who": ent, "km": round(km), "hours": round(hrs, 1),
                        "at": b["timestamp"], "from_xy": (a["latitude"], a["longitude"]),
                        "to_xy": (b["latitude"], b["longitude"]),
                        "evidence": f"{a['ref']} -> {b['ref']}"})
    for ip, g in d.dropna(subset=["ip_address"]).groupby("ip_address"):
        rows = g.to_dict("records"); first = rows[0]
        for b in rows[1:]:
            km = hav(first["latitude"], first["longitude"], b["latitude"], b["longitude"])
            if km > 100:
                out.append({"flag": "Same IP, different cities", "who": b["entity"], "km": round(km),
                            "hours": None, "at": b["timestamp"],
                            "from_xy": (first["latitude"], first["longitude"]),
                            "to_xy": (b["latitude"], b["longitude"]),
                            "evidence": f"{first['ref']} -> {b['ref']} (IP {ip})"})
                break
    cols = ["flag", "who", "km", "hours", "at", "from_xy", "to_xy", "evidence"]
    return pd.DataFrame(out, columns=cols)

def score(P, ent_id):
    acct = P.ent2acct.get(ent_id)
    t = P.txns
    inc = t[t["to_acct"] == acct]; out = t[t["from_acct"] == acct]
    total_in, total_out = inc["amount"].sum(), out["amount"].sum()
    f = {k: 0.0 for k in WEIGHTS}; reasons = []
    if total_in <= 0:
        return {"score": 0.0, "contrib": {k: 0.0 for k in WEIGHTS},
                "reasons": ["No inflow, so this is not a collecting account"]}
    n_senders = inc["from_acct"].nunique()
    f["Unique victims in"] = min(n_senders / 3, 1)
    win = pd.Timedelta(minutes=VELOCITY_WINDOW_MIN)
    fwd = 0.0
    for _, o in out.iterrows():
        recent = inc[(inc["timestamp"] <= o["timestamp"]) & (inc["timestamp"] >= o["timestamp"] - win)]
        if not recent.empty: fwd += o["amount"]
    f["Velocity"] = min(fwd / total_in, 1)
    f["Pass-through"] = max(0.0, 1 - abs(total_out - total_in) / total_in)
    mine = P.ev[P.ev["entity_id"] == ent_id]
    keys = set(mine["device"].dropna()) | set(mine["ip_address"].dropna())
    others = 0
    if keys:
        o = P.ev[(P.ev["entity_id"] != ent_id) & (P.ev["device"].isin(keys) | P.ev["ip_address"].isin(keys))]
        others = o["entity_id"].nunique()
        f["Shared device/IP"] = min(others / 2, 1)
    reasons.append(f"Received ₹{total_in:,.0f} from {n_senders} distinct sender(s)")
    reasons.append(f"{f['Velocity']:.0%} of inflow forwarded within {VELOCITY_WINDOW_MIN} minutes")
    reasons.append(f"Pass-through {f['Pass-through']:.0%}: sent out ₹{total_out:,.0f} of ₹{total_in:,.0f} received")
    reasons.append(f"Device/IP shared with {others} other entity(ies)" if keys else "No device/IP evidence for this account")
    reasons.append("Account age and complaint counts: no data yet (stub = 0)")
    contrib = {k: f[k] * WEIGHTS[k] for k in WEIGHTS}
    return {"score": round(sum(contrib.values()), 2), "contrib": contrib, "reasons": reasons}

def all_scores(P):
    return {e: score(P, e) for e in P.ents["entity_id"]}

def build_graph_html(P, t, scores, resolved):
    agg = (t.groupby(["from_acct", "to_acct"]).agg(
        amount=("amount", "sum"), n=("txn_id", "count"),
        first=("timestamp", "min"), last=("timestamp", "max")).reset_index())
    nid = lambda a: P.acct2ent.get(a, a)
    G = nx.DiGraph()
    for r in agg.itertuples():
        G.add_edge(nid(r.from_acct), nid(r.to_acct), amount=r.amount, n=r.n, first=r.first, last=r.last)
    hot = set()
    if resolved:
        for n in G.nodes:
            if P.role.get(n) == "cash-out":
                hot |= nx.ancestors(G, n) | {n}
    link_edges = []
    if resolved:
        for r in P.links.itertuples():
            if not G.has_edge(r.source_entity_id, r.target_entity_id):
                link_edges.append(r)
    net = Network(height="600px", width="100%", directed=True, bgcolor="#05050f", font_color="#e6e6ff")
    net.set_options(GRAPH_OPTIONS)
    nodes = set(G.nodes) | {x for r in link_edges for x in (r.source_entity_id, r.target_entity_id)}
    for n in nodes:
        role = P.role.get(n, "account") if resolved else "account"
        sc = scores.get(n, {}).get("score", 0)
        label = P.name.get(n, n) if resolved else P.ent2acct.get(n, n)
        indeg = G.in_degree(n) if n in G else 0
        net.add_node(n, label=label, color=COLORS[role], size=16 + 4 * indeg + 24 * sc,
                     title=f"{P.name.get(n, n)} | {P.role.get(n, 'account')} | score {sc:.2f}")
    for u, v, d in G.edges(data=True):
        on = u in hot and v in hot
        net.add_edge(u, v, label=f"₹{d['amount']:,.0f} ×{d['n']}",
                     title=f"{d['n']} txn(s), {d['first']} to {d['last']}",
                     color="#ff3caa" if on else "#334455", width=3 if on else 1)
    for r in link_edges:
        net.add_edge(r.source_entity_id, r.target_entity_id,
                     label=str(r.relationship_type), dashes=True, color="#b366ff",
                     title=f"link strength {r.strength_score}")
    html = net.generate_html()
    return html.replace("return network;",
        'network.once("stabilizationIterationsDone", function(){network.setOptions({physics:false});}); return network;')

def show_html(html, height=620):
    components.html(html, height=height, scrolling=False)

def time_slider(series, key):
    lo, hi = series.min().to_pydatetime(), series.max().to_pydatetime()
    if lo >= hi: return lo, hi
    return st.slider("Time range", min_value=lo, max_value=hi, value=(lo, hi),
                     format="DD/MM HH:mm", key=key)

def kpi(label, value, sub, color):
    return f'<div class="kpi {color}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>'

def role_badge(role):
    return f'<span class="role-badge role-{role}">{role}</span>'

# ═══════════════════ SIDEBAR ═══════════════════
with st.sidebar:
    st.markdown('<div style="text-align:center;padding:1rem 0;font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#00ffcc,#b366ff,#ff3caa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">SUTRAM</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#8a8ab0;font-size:0.68rem;letter-spacing:0.22em;margin-bottom:1.5rem;">EVIDENCE CORRELATION</div>', unsafe_allow_html=True)

    if st.button("⟳  LOAD DEMO CASE", use_container_width=True):
        try:
            st.session_state["data"] = load_demo()
            st.session_state["resolved"] = False
            st.rerun()
        except Exception as e:
            st.error(f"Could not read data/: {e}")

    st.markdown('<div style="color:#8a8ab0;font-size:0.72rem;margin:0.8rem 0 0.3rem 0;letter-spacing:0.1em;">UPLOAD CSVs</div>', unsafe_allow_html=True)
    ups = st.file_uploader("Upload", type="csv", accept_multiple_files=True, label_visibility="collapsed")
    if ups:
        d = dict(st.session_state.get("data", {}))
        for f in ups:
            for k in FILES:
                if k in f.name.lower(): d[k] = pd.read_csv(f)
        st.session_state["data"] = d

    st.markdown("---", unsafe_allow_html=False)
    role = st.selectbox("👤  ACTIVE ROLE", ["Investigator", "Supervisor", "Auditor"])
    st.markdown(f'<div style="color:#00ffcc;font-size:0.75rem;margin-top:-0.4rem;font-family:JetBrains Mono,monospace;">◉ session active · {role}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="color:#8a8ab0;font-size:0.7rem;letter-spacing:0.15em;margin-bottom:0.6rem;">LEGEND</div>', unsafe_allow_html=True)
    for r, c in [("victim", "#4da3ff"), ("mule", "#ff3caa"), ("recruiter", "#b366ff"),
                 ("cash-out", "#ffb320"), ("onward", "#ff8a4d")]:
        st.markdown(f'<div style="color:#e6e6ff;font-size:0.8rem;margin:0.25rem 0;"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{c};box-shadow:0 0 8px {c};margin-right:0.5rem;"></span>{r}</div>', unsafe_allow_html=True)

# ═══════════════════ HERO + NAV ═══════════════════
st.markdown('<div class="hero"><h1>SUTRAM</h1><div class="tagline">◈ Digital Evidence Correlation & Crime Reconstruction Engine</div></div>', unsafe_allow_html=True)

page = st.radio("nav", ["Overview", "Graph", "Timeline", "Map"], horizontal=True, label_visibility="collapsed")

data = st.session_state.get("data")
resolved = st.session_state.get("resolved", False)

if not data or any(k not in data for k in FILES):
    st.markdown('<div class="alert-info">▸ Click <strong>LOAD DEMO CASE</strong> in the sidebar, or upload all four CSVs (entities, transactions, events, links).</div>', unsafe_allow_html=True)
    st.stop()

P = prepare(data)
scores_b = b_score_all(P)
if scores_b:
    scores = {
        eid: {
            "score": v["score"],
            "reasons": v["reasons"],
            "contrib": b_contrib(P, eid),
        }
        for eid, v in scores_b.items()
    }
else:
    scores = all_scores(P)  # fallback to C stub if B's code fails
flags = find_flags(P.ev)
FLAG_COLS = ["flag", "who", "km", "hours", "at", "evidence"]

# ═══════════════════ OVERVIEW ═══════════════════
if page == "Overview":
    victims = [e for e, r in P.role.items() if r == "victim"]
    mules = [e for e, s in scores.items() if s["score"] >= MULE_THRESHOLD]
    lost = P.txns[P.txns["from_acct"].isin([P.ent2acct[v] for v in victims])]["amount"].sum()

    st.markdown(f'''<div class="kpi-grid">
        {kpi("VICTIMS", len(victims), "linked complaints", "cyan")}
        {kpi("MONEY LOST", f"₹{lost:,.0f}", "total reported", "pink")}
        {kpi("MULE ACCOUNTS", len(mules) if resolved else "?", "identified", "violet")}
        {kpi("ANOMALIES", len(flags), "flags raised", "amber")}
    </div>''', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🔍  RESOLVE NETWORK", use_container_width=True):
            st.session_state["resolved"] = True
            st.rerun()

    if resolved:
        names = ", ".join(P.name[m] for m in mules) or "none"
        st.markdown(f'<div class="alert-success">✓ Network resolved. <strong>{len(victims)}</strong> independent victims link to <strong>{names}</strong>. Open the Graph page to see the money flow.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-info">▸ Click <strong>RESOLVE NETWORK</strong> to correlate separate complaints into one financial network.</div>', unsafe_allow_html=True)

    if not flags.empty:
        st.markdown('<div class="section-head">Anomaly Flags</div>', unsafe_allow_html=True)
        st.dataframe(flags[FLAG_COLS], width="stretch")

    st.markdown('<div class="section-head">Transactions</div>', unsafe_allow_html=True)
    st.dataframe(P.txns, width="stretch")

    st.markdown('<div class="section-head">Entities</div>', unsafe_allow_html=True)
    st.dataframe(P.ents, width="stretch")

# ═══════════════════ GRAPH ═══════════════════
elif page == "Graph":
    if not resolved:
        st.markdown('<div class="alert-info">▸ Resolve the network first (Overview page) to see role colors and the money path.</div>', unsafe_allow_html=True)

    start, end = time_slider(P.txns["timestamp"], "g_time")
    t = P.txns[(P.txns["timestamp"] >= start) & (P.txns["timestamp"] <= end)]
    show_html(build_graph_html(P, t, scores, resolved), 620)

    st.markdown('<div class="section-head">Entity Detail</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        pick_name = st.selectbox("Select entity", list(P.name.values()), label_visibility="collapsed")
        pick = next(k for k, v in P.name.items() if v == pick_name)
        sc = scores[pick]
        st.markdown(f'<h2 style="margin:0.6rem 0 0.4rem 0;">{P.name[pick]}</h2>', unsafe_allow_html=True)
        st.markdown(role_badge(P.role[pick]), unsafe_allow_html=True)
        st.markdown('<div class="section-head">Score Breakdown</div>', unsafe_allow_html=True)
        bd = pd.DataFrame({"Signal": list(sc["contrib"]), "Points": list(sc["contrib"].values())})
        fig = px.bar(bd, x="Points", y="Signal", orientation="h", template="plotly_dark",
                     color="Points", color_continuous_scale=[[0, "#00ffcc"], [0.5, "#b366ff"], [1, "#ff3caa"]])
        fig.update_layout(height=320, showlegend=False, coloraxis_showscale=False,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        color = "var(--neon-pink)" if sc["score"] >= MULE_THRESHOLD else "var(--neon-amber)"
        st.markdown(f'<div class="score-ring" style="--pct: {sc["score"]*100}%; --color: {color}"><div class="score-inner"><div class="score-num">{sc["score"]:.2f}</div><div class="score-label">MULE SCORE</div></div></div>', unsafe_allow_html=True)
        verdict = "ABOVE THRESHOLD" if sc["score"] >= MULE_THRESHOLD else "below threshold"
        vcolor = "var(--neon-pink)" if sc["score"] >= MULE_THRESHOLD else "var(--neon-amber)"
        st.markdown(f'<div style="text-align:center;color:{vcolor};font-size:0.75rem;letter-spacing:0.15em;font-family:JetBrains Mono,monospace;">{verdict}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-head">Reasoning</div>', unsafe_allow_html=True)
    for r in sc["reasons"]:
        st.markdown(f'<div class="reason-item">{r}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-head">Account Transactions</div>', unsafe_allow_html=True)
    acct = P.ent2acct[pick]
    st.dataframe(P.txns[(P.txns["from_acct"] == acct) | (P.txns["to_acct"] == acct)], width="stretch")

# ═══════════════════ TIMELINE ═══════════════════
elif page == "Timeline":
    ev = P.ev
    start, end = time_slider(ev["timestamp"], "t_time")
    types = sorted(ev["type"].unique())
    chosen = st.multiselect("Event types", types, default=types)
    ev = ev[(ev["timestamp"] >= start) & (ev["timestamp"] <= end) & ev["type"].isin(chosen)]

    fig = px.scatter(ev, x="timestamp", y="entity", color="type",
                     hover_data=["ref", "source_doc", "alias", "details"], template="plotly_dark",
                     color_discrete_sequence=["#00ffcc", "#ff3caa", "#b366ff", "#ffb320", "#b4ff2e", "#4da3ff", "#ff8a4d"])
    fig.update_traces(marker=dict(size=13, line=dict(width=1.5, color="rgba(255,255,255,0.3)")))
    fig.update_layout(height=500, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    if not flags.empty:
        fig.add_trace(go.Scatter(x=flags["at"], y=flags["who"], mode="markers",
                                 marker=dict(symbol="x", size=22, color="#ff3caa", line=dict(width=2, color="#ff3caa")),
                                 name="Anomaly"))
    st.plotly_chart(fig, use_container_width=True)

    if not flags.empty:
        st.markdown('<div class="section-head" style="border-color:#ff3caa;">Anomalies Detected</div>', unsafe_allow_html=True)
        st.dataframe(flags[FLAG_COLS], width="stretch")

    st.markdown('<div class="section-head">Event Log</div>', unsafe_allow_html=True)
    st.dataframe(ev[["timestamp", "type", "entity", "alias", "ref", "source_doc", "details"]], width="stretch")

# ═══════════════════ MAP ═══════════════════
elif page == "Map":
    d = P.ev.dropna(subset=["latitude", "longitude"]).copy()
    d["lat3"] = d["latitude"].round(3)
    d["lon3"] = d["longitude"].round(3)
    m = folium.Map(location=[d["latitude"].mean(), d["longitude"].mean()],
                   zoom_start=5, tiles="CartoDB dark_matter")
    for (la, lo), g in d.groupby(["lat3", "lon3"]):
        place = next((x for x in g["location"] if x), "Device / ATM site")
        lines = "<br>".join(f"{r.timestamp:%d/%m %H:%M} | {r.type} | {r.entity}" for r in g.head(12).itertuples())
        folium.CircleMarker((la, lo), radius=6 + min(len(g), 10),
                            color="#00ffcc", fill=True, fill_color="#00ffcc", fill_opacity=0.6,
                            tooltip=f"{place}: {len(g)} events",
                            popup=folium.Popup(lines, max_width=320)).add_to(m)
    for r in flags.itertuples():
        folium.PolyLine([r.from_xy, r.to_xy], color="#ff3caa", weight=3, dash_array="8",
                        tooltip=f"{r.flag}: {r.who}, {r.km} km").add_to(m)
    st_folium(m, height=600, width=1100)