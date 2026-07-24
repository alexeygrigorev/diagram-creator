from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """Raised when a diagram specification is invalid."""


@dataclass(frozen=True)
class Node:
    id: str
    title: str
    subtitle: str = ""
    color: str = "blue"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    label: str = ""
    color: str = "gray"
    route: str = "forward"


@dataclass(frozen=True)
class DiagramSpec:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    background: str = "#f8fafc"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagramSpec:
        raw_nodes = data.get("nodes")
        raw_edges = data.get("edges")
        if not isinstance(raw_nodes, list) or len(raw_nodes) < 2:
            raise SpecError("'nodes' must contain at least two entries")
        if not isinstance(raw_edges, list):
            raise SpecError("'edges' must be a list")

        nodes = tuple(_parse_node(item) for item in raw_nodes)
        node_ids = [node.id for node in nodes]
        if len(set(node_ids)) != len(node_ids):
            raise SpecError("node IDs must be unique")

        edges = tuple(_parse_edge(item) for item in raw_edges)
        known_ids = set(node_ids)
        for edge in edges:
            if edge.source not in known_ids:
                raise SpecError(f"edge references unknown source node: {edge.source}")
            if edge.target not in known_ids:
                raise SpecError(f"edge references unknown target node: {edge.target}")
            if edge.source == edge.target:
                raise SpecError("an edge cannot connect a node to itself")

        background = data.get("background", "#f8fafc")
        if not isinstance(background, str):
            raise SpecError("'background' must be a color string")

        return cls(nodes=nodes, edges=edges, background=background)


def _parse_node(data: Any) -> Node:
    if not isinstance(data, dict):
        raise SpecError("each node must be an object")
    node_id = _required_string(data, "id", "node")
    title = _required_string(data, "title", f"node '{node_id}'")
    subtitle = data.get("subtitle", "")
    color = data.get("color", "blue")
    if not isinstance(subtitle, str):
        raise SpecError(f"node '{node_id}' subtitle must be a string")
    if not isinstance(color, str):
        raise SpecError(f"node '{node_id}' color must be a string")
    return Node(id=node_id, title=title, subtitle=subtitle, color=color)


def _parse_edge(data: Any) -> Edge:
    if not isinstance(data, dict):
        raise SpecError("each edge must be an object")
    source = _required_string(data, "from", "edge")
    target = _required_string(data, "to", "edge")
    label = data.get("label", "")
    color = data.get("color", "gray")
    route = data.get("route", "forward")
    if not isinstance(label, str):
        raise SpecError("edge label must be a string")
    if not isinstance(color, str):
        raise SpecError("edge color must be a string")
    if route not in {"forward", "below"}:
        raise SpecError("edge route must be 'forward' or 'below'")
    return Edge(source=source, target=target, label=label, color=color, route=route)


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{context} requires a non-empty '{key}'")
    return value


def load_spec(path: str | Path) -> DiagramSpec:
    source = Path(path)
    try:
        data = json.loads(source.read_text())
    except json.JSONDecodeError as exc:
        raise SpecError(f"invalid JSON in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("the diagram specification must be a JSON object")
    return DiagramSpec.from_dict(data)
