import pandas as pd


def safe_division(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


def score_mule_accounts(entities, transactions, links):
    accounts = entities[entities["type"] == "account"]
    results = []

    for _, account in accounts.iterrows():
        account_id = account["entity_id"]

        incoming = transactions[transactions["to_acct"] == account_id]
        outgoing = transactions[transactions["from_acct"] == account_id]

        inflow = incoming["amount"].sum()
        outflow = outgoing["amount"].sum()

        unique_senders = incoming["from_acct"].nunique()

        # Since A's dataset is small, use 2 instead of 5
        victim_score = min(unique_senders / 2, 1)

        forwarded_count = 0

        for _, received in incoming.iterrows():
            received_time = pd.to_datetime(received["timestamp"])

            later_transfers = outgoing[
                pd.to_datetime(outgoing["timestamp"]) > received_time
            ]

            if not later_transfers.empty:
                forwarded_count += 1

        velocity_score = safe_division(forwarded_count, len(incoming))
        pass_through_score = min(safe_division(outflow, inflow), 1)

        shared_links = links[
            (
                (links["entity_a"] == account_id)
                | (links["entity_b"] == account_id)
            )
            & (links["link_type"] == "same_ip")
        ]

        shared_ip_score = min(len(shared_links) / 2, 1)

        # A's data does not give account age, so keep it neutral
        account_age_score = 0.5

        complaint_score = min(len(incoming) / 2, 1)

        final_score = (
            victim_score * 0.25
            + velocity_score * 0.25
            + pass_through_score * 0.15
            + shared_ip_score * 0.15
            + account_age_score * 0.10
            + complaint_score * 0.10
        )

        reasons = []

        if unique_senders > 0:
            reasons.append(
                f"Received money from {unique_senders} sender account(s)"
            )

        if forwarded_count > 0:
            reasons.append(
                f"Forwarded money after {forwarded_count} incoming transaction(s)"
            )

        if inflow > 0:
            reasons.append(
                f"Pass-through ratio: {outflow / inflow:.0%}"
            )

        if len(shared_links) > 0:
            reasons.append(
                f"Connected to {len(shared_links)} IP evidence link(s)"
            )

        results.append({
            "entity_id": account_id,
            "account_label": account["label"],
            "mule_score": round(final_score, 2),
            "money_received": inflow,
            "money_sent": outflow,
            "unique_senders": unique_senders,
            "reasons": "; ".join(reasons) if reasons else "No suspicious pattern detected"
        })

    return pd.DataFrame(results).sort_values(
        "mule_score",
        ascending=False
    )