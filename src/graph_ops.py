from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def build_adjacency(edges: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    adj = {}
    rev_adj = {}

    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])
        rev_adj.setdefault(e["to"], []).append(e["from"])

    return adj, rev_adj


def get_context_pack(
    node_id: str,
    node_index: dict[str, Any],
    adj: dict[str, list[str]],
    rev_adj: dict[str, list[str]],
    max_hops: int = 1,
    max_nodes: int = 4,
    include_reverse: bool = False,
) -> dict[str, Any]:
    """
    Returns: primary node + related nodes reached by traversing outgoing edges up to max_hops.
    Caps related nodes count.
    """
    if node_id not in node_index:
        raise KeyError(f"Unknown node_id: {node_id}")

    visited = set([node_id])
    frontier = [(node_id, 0)]
    related_ids = []
    edges_used = []

    while frontier and len(related_ids) < max_nodes:
        current, hop = frontier.pop(0)
        if hop >= max_hops:
            continue

        neighbors = adj.get(current, [])
        for nb in neighbors:
            if nb in visited:
                continue
            visited.add(nb)
            related_ids.append(nb)
            edges_used.append({"from": current, "to": nb})
            frontier.append((nb, hop+1))
            if len(related_ids) >= max_nodes:
                break

        if include_reverse and len(related_ids) < max_nodes:
            rneighbors = rev_adj.get(current, [])
            for nb in rneighbors:
                if nb in visited:
                    continue
                visited.add(nb)
                related_ids.append(nb)
                edges_used.append({"from": nb, "to": current})
                frontier.append((nb, hop+1))
                if len(related_ids) >= max_nodes:
                    break

    def serialize(node: Any) -> dict[str, Any]:
        return asdict(node) if is_dataclass(node) else dict(vars(node))

    primary = serialize(node_index[node_id])
    related = [serialize(node_index[rid]) for rid in related_ids]

    return {"primary": primary, "related": related, "edges_used": edges_used}
