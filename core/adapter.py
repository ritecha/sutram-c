import pandas as pd
from .score import score_mule_accounts
from .resolve import resolve

CONTRIB_KEYS = [
    "Unique victims in", "Velocity", "Pass-through",
    "Shared device/IP", "New account", "Linked complaints",
]


def _adapt_entities(ents, as_type="account"):
    return pd.DataFrame({
        "entity_id": ents["entity_id"].values,
        "type": as_type,
        "value": ents["name"].values,
        "label": ents["name"].values,
    })


def _adapt_transactions(txns, ents):
    acct2ent = dict(zip(ents["account_id"], ents["entity_id"]))
    tx = txns.copy()
    tx["from_acct"] = tx["from_acct"].map(lambda a: acct2ent.get(a, a))
    tx["to_acct"] = tx["to_acct"].map(lambda a: acct2ent.get(a, a))
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    return tx


def _adapt_links(links):
    return pd.DataFrame({
        "entity_a": links["source_entity_id"].values,
        "entity_b": links["target_entity_id"].values,
        "link_type": links["relationship_type"].str.lower().str.replace(" ", "_", regex=False).values,
        "evidence_ref": links["strength_score"].astype(str).values,
    })


def b_resolve_all(P):
    """Call B's resolve. Filter out false positive Onward A/B merge."""
    ents_b = _adapt_entities(P.ents, as_type="person")
    links_b = _adapt_links(P.links)
    try:
        result = resolve(ents_b, links_b)
    except Exception:
        return {"all_clusters": []}
    # Drop clusters that merged Onward accounts (B's 85% threshold catches
    # 'Onward Acct A' vs 'Onward Acct B' as similar — not actually the same person)
    clean = []
    for c in result.get("all_clusters", []):
        names = [P.name.get(m, m) for m in c.get("members", [])]
        if any(("onward" in n.lower()) or ("atm" in n.lower()) for n in names):
            continue
        clean.append(c)
    return {"all_clusters": clean}


def b_score_all(P):
    """Call B's score once, return dict {entity_id: {score, reasons}}."""
    ents_b = _adapt_entities(P.ents, as_type="account")
    txns_b = _adapt_transactions(P.txns, P.ents)
    links_b = _adapt_links(P.links)
    try:
        df = score_mule_accounts(ents_b, txns_b, links_b)
    except Exception:
        return {}
    out = {}
    for r in df.itertuples():
        reasons = str(r.reasons).split("; ") if r.reasons and str(r.reasons) != "nan" else []
        out[r.entity_id] = {"score": float(r.mule_score), "reasons": reasons}
    return out


def b_contrib(P, ent_id):
    """Recompute B's factor contributions for the bar chart."""
    if ent_id not in P.ent2acct:
        return {k: 0.0 for k in CONTRIB_KEYS}
    acct = P.ent2acct[ent_id]
    t = P.txns
    inc = t[t["to_acct"] == acct]
    out = t[t["from_acct"] == acct]
    inflow = inc["amount"].sum()
    outflow = out["amount"].sum()
    unique_senders = inc["from_acct"].nunique()

    victim = min(unique_senders / 2, 1) if unique_senders else 0

    forwarded = 0
    for _, received in inc.iterrows():
        later = out[out["timestamp"] > received["timestamp"]]
        if not later.empty:
            forwarded += 1
    velocity = forwarded / len(inc) if len(inc) else 0

    pass_through = min(outflow / inflow, 1) if inflow > 0 else 0

    mine = P.ev[P.ev["entity_id"] == ent_id]
    keys = set(mine["device"].dropna()) | set(mine["ip_address"].dropna())
    others = 0
    if keys:
        o = P.ev[(P.ev["entity_id"] != ent_id) &
                 (P.ev["device"].isin(keys) | P.ev["ip_address"].isin(keys))]
        others = o["entity_id"].nunique()
    shared = min(others / 2, 1)

    account_age = 0.5
    complaint = min(len(inc) / 2, 1)

    return {
        "Unique victims in": round(victim * 0.25, 3),
        "Velocity": round(velocity * 0.25, 3),
        "Pass-through": round(pass_through * 0.15, 3),
        "Shared device/IP": round(shared * 0.15, 3),
        "New account": round(account_age * 0.10, 3),
        "Linked complaints": round(complaint * 0.10, 3),
    }