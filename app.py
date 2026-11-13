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

st.set_page_config(page_title="Sutram", layout="wide")

COLORS = {
    "victim": "#4da3ff",
    "mule": "#ff4d4d",
    "recruiter": "#b36bff",
    "cash-out": "#ffb020",
    "account": "#9aa4b2",
}
CITY = {
    "Delhi": (28.6139, 77.2090),
    "Noida": (28.5355, 77.3910),
    "Jaipur": (26.9124, 75.7873),
    "Pune": (18.5204, 73.8567),
}
WEIGHTS = {
    "Unique victims in": 0.25,
    "Velocity": 0.25,
    "Pass-through": 0.15,
    "Shared device/IP": 0.15,
    "New account": 0.10,
    "Linked complaints": 0.10,
}
GRAPH_OPTIONS = """{
  "physics": {
    "barnesHut": {"gravitationalConstant": -8000, "springLength": 160},
    "stabilization": {"enabled": true, "iterations": 200}
  },
  "interaction": {"hover": true}
}"""


# ---------- Helpers ----------
def haversine(a, b):
    la1, lo1 = CITY[a]
    la2, lo2 = CITY[b]
    p1, p2 = math.radians(la1), math.radians(la2)
    dl = math.radians(lo2 - lo1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def find_impossible(ev, max_kmh=120):
    out = []
    for ent, g in ev.sort_values("timestamp").groupby("entity_id"):
        rows = g.to_dict("records")
        for a, b in zip(rows, rows[1:]):
            la, lb = a["location"], b["location"]
            if la == lb or la not in CITY or lb not in CITY:
                continue
            km = haversine(la, lb)
            hrs = (b["timestamp"] - a["timestamp"]).total_seconds() / 3600
            if hrs <= 0 or km / hrs > max_kmh:
                out.append({"entity": ent, "from": la, "to": lb,
                            "km": round(km), "minutes": round(hrs * 60, 1),
                            "at": b["timestamp"]})
    return pd.DataFrame(out)


def prep_events(events):
    ev = events.copy()
    ev["timestamp"] = pd.to_datetime(ev["timestamp"])
    return ev.sort_values("timestamp")


# STUB: B's score() will replace this later. Same output shape.
def score(node, txns, events=None):
    t = txns.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    inc = t[t["to_acct"] == node]
    out = t[t["from_acct"] == node]
    total_in = inc["amount"].sum()
    total_out = out["amount"].sum()

    f = {k: 0.0 for k in WEIGHTS}
    reasons = []

    if total_in > 0:
        n_senders = inc["from_acct"].nunique()
        f["Unique victims in"] = min(n_senders / 3, 1)

        forwarded = 0.0
        for _, o in out.iterrows():
            recent = inc[(inc["timestamp"] <= o["timestamp"]) &
                         (inc["timestamp"] >= o["timestamp"] - pd.Timedelta(minutes=30))]
            if not recent.empty:
                forwarded += o["amount"]
        f["Velocity"] = min(forwarded / total_in, 1)
        f["Pass-through"] = max(0.0, 1 - abs(total_out - total_in) / total_in)

        if events is not None:
            complained = set(events.loc[events["type"] == "complaint", "entity_id"])
            f["Linked complaints"] = min(len(set(inc["from_acct"]) & complained) / 3, 1)

        reasons.append(f"Received ₹{total_in:,.0f} from {n_senders} distinct senders")
        reasons.append(f"{f['Velocity']:.0%} of inflow forwarded within 30 minutes")
        reasons.append(f"Pass-through ratio {f['Pass-through']:.0%} (money leaves almost as fast as it arrives)")
        reasons.append("Shared device/IP and account age: waiting for A/B data (stub = 0)")
    else:
        reasons.append("No inflow, so this is not a collecting account")

    contrib = {k: f[k] * WEIGHTS[k] for k in WEIGHTS}
    return {"score": round(sum(contrib.values()), 2), "factors": f,
            "contrib": contrib, "reasons": reasons}


def all_scores(txns, events):
    nodes = set(txns["from_acct"]) | set(txns["to_acct"])
    return {n: score(n, txns, events) for n in sorted(nodes)}


def node_role(n, scores=None):
    if n.startswith("V"):
        return "victim"
    if n.startswith("ATM"):
        return "cash-out"
    if n.startswith("R"):
        return "recruiter"
    if n.startswith("M") or (scores and scores.get(n, {}).get("score", 0) >= 0.5):
        return "mule"
    return "account"


def build_graph_html(t, scores, resolved):
    G = nx.DiGraph()
    for _, r in t.iterrows():
        G.add_edge(r["from_acct"], r["to_acct"], amount=r["amount"],
                   ts=str(r["timestamp"]), txn=r["txn_id"])

    hot = set()
    if resolved:
        for n in G.nodes:
            if node_role(n) == "cash-out":
                hot |= nx.ancestors(G, n) | {n}

    net = Network(height="600px", width="100%", directed=True,
                  bgcolor="#0e1117", font_color="white")
    net.set_options(GRAPH_OPTIONS)
    for n in G.nodes:
        role = node_role(n, scores) if resolved else "account"
        sc = scores.get(n, {}).get("score", 0)
        net.add_node(n, label=n, color=COLORS[role],
                     size=15 + 6 * G.in_degree(n),
                     title=f"{n} | {node_role(n, scores)} | score {sc:.2f}")
    for u, v, d in G.edges(data=True):
        on_path = u in hot and v in hot
        net.add_edge(u, v, label=f"₹{int(d['amount']):,}",
                     title=f"{d['txn']} | {d['ts']}",
                     color="#ff4d4d" if on_path else "#555555",
                     width=3 if on_path else 1)

    html = net.generate_html()
    # Freeze the layout once it settles so zoom/pan stays stable
    html = html.replace(
        "return network;",
        'network.once("stabilizationIterationsDone", function(){network.setOptions({physics:false});}); return network;')
    return html


# ---------- Sidebar ----------
st.sidebar.title("Sutram")
role = st.sidebar.selectbox("Role", ["Investigator", "Supervisor", "Auditor"])
page = st.sidebar.radio("Page", ["Overview", "Graph", "Timeline", "Map"])

if st.sidebar.button("Load demo case"):
    st.session_state["txns"] = pd.read_csv("data/transactions.csv")
    st.session_state["events"] = pd.read_csv("data/events.csv")
    st.session_state["resolved"] = False

up_t = st.sidebar.file_uploader("Transactions CSV", type="csv")
up_e = st.sidebar.file_uploader("Events CSV", type="csv")
if up_t:
    st.session_state["txns"] = pd.read_csv(up_t)
if up_e:
    st.session_state["events"] = pd.read_csv(up_e)

txns = st.session_state.get("txns")
events = st.session_state.get("events")
resolved = st.session_state.get("resolved", False)
st.sidebar.caption(f"Logged in as: {role}")

# ---------- Pages ----------
st.title(page)

if txns is None:
    st.info("Click 'Load demo case' in the sidebar.")

elif page == "Overview":
    scores = all_scores(txns, events)
    victims = [n for n in scores if n.startswith("V")]
    mules = [n for n, s in scores.items() if s["score"] >= 0.5]
    lost = txns[txns["from_acct"].isin(victims)]["amount"].sum()
    n_bad = 0
    if events is not None:
        bad = find_impossible(prep_events(events))
        n_bad = len(bad)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Victims", len(victims))
    c2.metric("Money lost by victims", f"₹{lost:,.0f}")
    c3.metric("Suspected mule accounts", len(mules) if resolved else "?")
    c4.metric("Impossible-travel flags", n_bad)

    if st.button("Resolve"):
        st.session_state["resolved"] = True
        st.rerun()

    if resolved:
        st.success(f"Resolved: {len(victims)} separate victims now link to "
                   f"{len(mules)} mule account(s): {', '.join(mules)}. Open the Graph page.")
    else:
        st.info("Click Resolve to link the separate cases into one network.")

    st.subheader("Transactions")
    st.dataframe(txns, use_container_width=True)
    if events is not None:
        st.subheader("Events")
        st.dataframe(events, use_container_width=True)

elif page == "Graph":
    scores = all_scores(txns, events)
    if not resolved:
        st.info("Network not resolved yet. Go to Overview and click Resolve to see roles and the money path.")

    t = txns.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    lo = t["timestamp"].min().to_pydatetime()
    hi = t["timestamp"].max().to_pydatetime()
    if lo < hi:
        start, end = st.slider("Time range", min_value=lo, max_value=hi,
                               value=(lo, hi), format="HH:mm")
        t = t[(t["timestamp"] >= start) & (t["timestamp"] <= end)]

    components.html(build_graph_html(t, scores, resolved), height=620)

    st.subheader("Node evidence")
    pick = st.selectbox("Select a node", list(scores))
    sc = scores[pick]
    st.write(f"**Role:** {node_role(pick, scores)}")
    st.metric("Mule score", f"{sc['score']:.2f}")

    bd = pd.DataFrame({"Signal": list(sc["contrib"].keys()),
                       "Points": list(sc["contrib"].values())})
    fig = px.bar(bd, x="Points", y="Signal", orientation="h",
                 template="plotly_dark", range_x=[0, 0.3])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    for r in sc["reasons"]:
        st.write("•", r)

    st.dataframe(txns[(txns["from_acct"] == pick) | (txns["to_acct"] == pick)],
                 use_container_width=True)

elif page == "Timeline":
    if events is None:
        st.info("Load the events file first.")
    else:
        ev = prep_events(events)
        bad = find_impossible(ev)

        lo = ev["timestamp"].min().to_pydatetime()
        hi = ev["timestamp"].max().to_pydatetime()
        start, end = st.slider("Time range", min_value=lo, max_value=hi,
                               value=(lo, hi), format="HH:mm")

        all_types = sorted(ev["type"].unique())
        types = st.multiselect("Event types", all_types, default=all_types)

        ev = ev[(ev["timestamp"] >= start) & (ev["timestamp"] <= end)
                & ev["type"].isin(types)]

        fig = px.scatter(ev, x="timestamp", y="entity_id", color="type",
                         hover_data=["source_doc", "location"],
                         template="plotly_dark")
        fig.update_traces(marker=dict(size=14))
        fig.update_layout(height=450)
        if not bad.empty:
            fig.add_trace(go.Scatter(x=bad["at"], y=bad["entity"], mode="markers",
                                     marker=dict(symbol="x", size=22, color="red"),
                                     name="Impossible travel"))
        st.plotly_chart(fig, use_container_width=True)
        if not bad.empty:
            st.error("Impossible travel detected")
            st.dataframe(bad, use_container_width=True)

        st.subheader("Event log")
        st.dataframe(ev, use_container_width=True)

elif page == "Map":
    if events is None:
        st.info("Load the events file first.")
    else:
        m = folium.Map(location=[23.5, 77], zoom_start=5, tiles="CartoDB dark_matter")
        for loc, g in events.groupby("location"):
            if loc not in CITY:
                continue
            lines = "<br>".join(f"{r.timestamp} | {r.type} | {r.entity_id}"
                                for r in g.itertuples())
            folium.CircleMarker(CITY[loc], radius=8 + 2 * len(g),
                                color="#ff4d4d", fill=True,
                                tooltip=f"{loc}: {len(g)} events",
                                popup=folium.Popup(lines, max_width=320)).add_to(m)
        st_folium(m, height=550, width=1100)