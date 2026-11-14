import pandas as pd
import networkx as nx
from rapidfuzz import fuzz


def normalize_name(name):
    return " ".join(str(name).lower().replace(".", " ").split())


def fuzzy_name_clusters(entities, threshold=85):
    people = entities[entities["type"] == "person"].copy()
    people["normalized_name"] = people["value"].apply(normalize_name)

    graph = nx.Graph()
    graph.add_nodes_from(people["entity_id"])

    people_list = people.to_dict("records")

    for i in range(len(people_list)):
        for j in range(i + 1, len(people_list)):
            similarity = fuzz.token_sort_ratio(
                people_list[i]["normalized_name"],
                people_list[j]["normalized_name"]
            )

            if similarity >= threshold:
                graph.add_edge(
                    people_list[i]["entity_id"],
                    people_list[j]["entity_id"],
                    reason=f"Name similarity {similarity}%"
                )

    clusters = []

    for group in nx.connected_components(graph):
        if len(group) > 1:
            clusters.append({
                "cluster_id": f"NAME-{len(clusters) + 1}",
                "members": sorted(group),
                "reason": "Possible same person based on similar name"
            })

    return clusters


def shared_ip_clusters(entities, links):
    graph = nx.Graph()
    graph.add_nodes_from(entities["entity_id"])

    for _, row in links.iterrows():
        if row["link_type"] == "same_ip":
            graph.add_edge(
                row["entity_a"],
                row["entity_b"],
                reason=f"Same IP: {row['evidence_ref']}"
            )

    clusters = []

    for group in nx.connected_components(graph):
        if len(group) > 1:
            clusters.append({
                "cluster_id": f"IP-{len(clusters) + 1}",
                "members": sorted(group),
                "reason": "Entities connected through the same IP address"
            })

    return clusters


def resolve(entities, links):
    name_clusters = fuzzy_name_clusters(entities)
    ip_clusters = shared_ip_clusters(entities, links)

    return {
        "name_clusters": name_clusters,
        "ip_clusters": ip_clusters,
        "all_clusters": name_clusters + ip_clusters
    }