import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sutram", layout="wide")

# ---------- Sidebar ----------
st.sidebar.title("Sutram")
role = st.sidebar.selectbox("Role", ["Investigator", "Supervisor", "Auditor"])
page = st.sidebar.radio("Page", ["Overview", "Graph", "Timeline", "Map"])

if st.sidebar.button("Load demo case"):
    st.session_state["txns"] = pd.read_csv("data/transactions.csv")
    st.session_state["events"] = pd.read_csv("data/events.csv")

up_t = st.sidebar.file_uploader("Transactions CSV", type="csv")
up_e = st.sidebar.file_uploader("Events CSV", type="csv")
if up_t:
    st.session_state["txns"] = pd.read_csv(up_t)
if up_e:
    st.session_state["events"] = pd.read_csv(up_e)

txns = st.session_state.get("txns")
events = st.session_state.get("events")

st.sidebar.caption(f"Logged in as: {role}")

# ---------- Pages ----------
st.title(page)

if txns is None:
    st.info("Click 'Load demo case' in the sidebar.")
elif page == "Overview":
    st.subheader("Transactions")
    st.dataframe(txns, use_container_width=True)
    if events is not None:
        st.subheader("Events")
        st.dataframe(events, use_container_width=True)
else:
    st.write(f"{page} page coming in the next step.")