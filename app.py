import streamlit as st
import pandas as pd
import networkx as nx
import streamlit.components.v1 as components
from pyvis.network import Network
import plotly.express as px
import math
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

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

def haversine(a, b):
    la1, lo1 = CITY[a]; la2, lo2 = CITY[b]
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
# STUB: B's resolve()/score() will replace this later
def node_role(n):
    if n.startswith("V"): return "victim"
    if n.startswith("M"): return "mule"
    if n.startswith("R"): return "recruiter"
    if n.startswith("ATM"): return "cash-out"
    return "account"

def build_graph_html(txns):
    G = nx.DiGraph()
    for _, r in txns.iterrows():
        G.add_edge(r["from_acct"], r["to_acct"],
                   amount=r["amount"], ts=r["timestamp"], txn=r["txn_id"])

    net = Network(height="600px", width="100%", directed=True,
                  bgcolor="#0e1117", font_color="white")
    for n in G.nodes:
        role = node_role(n)
        net.add_node(n, label=n, color=COLORS[role],
                     size=15 + 6 * G.in_degree(n),
                     title=f"{n} ({role})")
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, label=f"₹{int(d['amount']):,}",
                     title=f"{d['txn']} | {d['ts']}")
    return net.generate_html()

# ---------- Sidebar ----------
st.sidebar.title("Sutram")
role = st.sidebar.selectbox("Role", ["Investigator", "Supervisor", "Auditor"])
page = st.sidebar.radio("Page", ["Overview", "Graph", "Timeline", "Map"])

if st.sidebar.button("Load demo case"):
    st.session_state["txns"] = pd.read_csv("data/transactions.csv")
    st.session_state["events"] = pd.read_csv("data/events.csv")

up_t = st.sidebar.file_uploader("Transactions CSV", type="csv")
up_e = st.sidebar.file_uploader("Events CSV", type="csv")
if up_t: st.session_state["txns"] = pd.read_csv(up_t)
if up_e: st.session_state["events"] = pd.read_csv(up_e)

txns = st.session_state.get("txns")
events = st.session_state.get("events")
st.sidebar.caption(f"Logged in as: {role}")

# ---------- Pages ----------
st.title(page)

if txns is None:
    st.info("Click 'Load demo case' in the sidebar.")
elif page == "Overview":
    st.dataframe(txns, use_container_width=True)
    if events is not None:
        st.dataframe(events, use_container_width=True)
elif page == "Graph":
    components.html(build_graph_html(txns), height=620)

    st.subheader("Node evidence")
    nodes = sorted(set(txns["from_acct"]) | set(txns["to_acct"]))
    pick = st.selectbox("Select a node", nodes)
    st.write(f"**Role:** {node_role(pick)}")
    st.write("**Score:** 0.87 (stub, B's output goes here)")
    st.dataframe(txns[(txns["from_acct"] == pick) | (txns["to_acct"] == pick)],
                 use_container_width=True)

elif page == "Timeline":
    if events is None:
        st.info("Load the events file first.")
    else:
        ev = events.copy()
        ev["timestamp"] = pd.to_datetime(ev["timestamp"])
        ev = ev.sort_values("timestamp")
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