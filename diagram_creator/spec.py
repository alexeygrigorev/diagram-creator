from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """Raised when a diagram specification is invalid."""


COLORS = {"purple", "blue", "amber", "green", "red", "gray"}
LAYOUTS = {"horizontal", "manual", "grid", "ring", "staircase"}
ROUTES = {"forward", "below", "straight", "curve", "ring", "step"}
STAIRCASE_DIRECTIONS = {"descending", "ascending"}
ANCHORS = {"left", "right", "top", "bottom"}
NODE_VARIANTS = {"card", "icon", "plain"}
ICON_POSITIONS = {"inline", "block"}
ICONS = {
    "github",
    "search",
    "database",
    "openai",
    "issue",
    "document",
    "user",
    "browser",
    "websocket",
    "api",
    "settings",
    "pull-request",
    "rank-fusion",
    "message",
    "video",
    "sparkles",
    "check",
    "warning",
    "close",
    "mention",
    "number-1",
    "number-2",
    "number-3",
}


@dataclass(frozen=True)
class Canvas:
    width: int = 1440
    height: int = 360
    background: str = "#f8fafc"


@dataclass(frozen=True)
class Layout:
    type: str = "horizontal"
    card_width: float | None = None
    card_height: float | None = None
    column_gap: float = 60
    row_gap: float = 60
    column_width: float | None = None
    row_height: float | None = None
    direction: str = "clockwise"
    margin: float | None = None
    font_scale: float = 1.0
    icon_position: str = "inline"
    step_x: float | None = None
    step_y: float | None = None


@dataclass(frozen=True)
class Node:
    id: str
    title: str
    subtitle: str = ""
    color: str = "blue"
    icon: str | None = None
    eyebrow: str = ""
    variant: str = "card"
    show_label: bool = True
    icon_size: float | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    row: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    label: str = ""
    color: str = "gray"
    route: str = "forward"
    source_anchor: str | None = None
    target_anchor: str | None = None
    controls: tuple[tuple[float, float], tuple[float, float]] | None = None
    bidirectional: bool = False


@dataclass(frozen=True)
class CenterAnnotation:
    title: str = ""
    subtitle: str = ""
    detail: str = ""
    radius: float = 68


@dataclass(frozen=True)
class Divider:
    after_row: int


@dataclass(frozen=True)
class DiagramSpec:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    canvas: Canvas = Canvas()
    layout: Layout = Layout()
    title: str = "Workflow diagram"
    description: str = ""
    center: CenterAnnotation | None = None
    dividers: tuple[Divider, ...] = ()

    @property
    def background(self) -> str:
        """Keep the original public attribute available for callers."""
        return self.canvas.background

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

        canvas = _parse_canvas(data)
        layout = _parse_layout(data.get("layout", {}))
        if layout.type == "manual":
            for node in nodes:
                if node.x is None or node.y is None:
                    raise SpecError("manual layout requires x and y for every node")
        if layout.type == "grid":
            cells: set[tuple[int, int]] = set()
            for node in nodes:
                if node.row is None or node.column is None:
                    raise SpecError("grid layout requires row and column for every node")
                cell = (node.row, node.column)
                if cell in cells:
                    raise SpecError("grid layout requires each node to use a unique cell")
                cells.add(cell)
        if layout.type == "ring" and len(nodes) < 3:
            raise SpecError("ring layout requires at least three nodes")

        title = data.get("title", "Workflow diagram")
        description = data.get("description", "")
        if not isinstance(title, str) or not title.strip():
            raise SpecError("'title' must be a non-empty string")
        if not isinstance(description, str):
            raise SpecError("'description' must be a string")

        center = _parse_center(data.get("center"))
        dividers = _parse_dividers(data.get("dividers"), layout, nodes)
        return cls(
            nodes=nodes,
            edges=edges,
            canvas=canvas,
            layout=layout,
            title=title,
            description=description,
            center=center,
            dividers=dividers,
        )


def _parse_canvas(data: dict[str, Any]) -> Canvas:
    raw = data.get("canvas", {})
    if not isinstance(raw, dict):
        raise SpecError("'canvas' must be an object")
    width = raw.get("width", 1440)
    height = raw.get("height", 360)
    background = raw.get("background", data.get("background", "#f8fafc"))
    if not isinstance(width, int) or width < 600:
        raise SpecError("canvas width must be an integer of at least 600")
    if not isinstance(height, int) or height < 280:
        raise SpecError("canvas height must be an integer of at least 280")
    if not isinstance(background, str):
        raise SpecError("canvas background must be a color string")
    return Canvas(width=width, height=height, background=background)


def _parse_layout(data: Any) -> Layout:
    if not isinstance(data, dict):
        raise SpecError("'layout' must be an object")
    layout_type = data.get("type", "horizontal")
    if layout_type not in LAYOUTS:
        raise SpecError(f"layout type must be one of: {', '.join(sorted(LAYOUTS))}")
    card_width = _optional_number(data, "card_width", "layout")
    card_height = _optional_number(data, "card_height", "layout")
    column_gap = data.get("column_gap", 60)
    row_gap = data.get("row_gap", 60)
    column_width = _optional_number(data, "column_width", "layout")
    row_height = _optional_number(data, "row_height", "layout")
    margin = _optional_number(data, "margin", "layout")
    font_scale = _optional_number(data, "font_scale", "layout")
    icon_position = data.get("icon_position", "inline")
    if icon_position not in ICON_POSITIONS:
        raise SpecError(
            f"layout 'icon_position' must be one of: {', '.join(sorted(ICON_POSITIONS))}"
        )
    step_x = _optional_number(data, "step_x", "layout")
    step_y = _optional_number(data, "step_y", "layout")
    if card_width is not None and card_width <= 0:
        raise SpecError("layout 'card_width' must be positive")
    if card_height is not None and card_height <= 0:
        raise SpecError("layout 'card_height' must be positive")
    if not isinstance(column_gap, (int, float)) or isinstance(column_gap, bool) or column_gap < 0:
        raise SpecError("layout 'column_gap' must be a non-negative number")
    if not isinstance(row_gap, (int, float)) or isinstance(row_gap, bool) or row_gap < 0:
        raise SpecError("layout 'row_gap' must be a non-negative number")
    if column_width is not None and column_width <= 0:
        raise SpecError("layout 'column_width' must be positive")
    if row_height is not None and row_height <= 0:
        raise SpecError("layout 'row_height' must be positive")
    if margin is not None and margin < 0:
        raise SpecError("layout 'margin' must be a non-negative number")
    if font_scale is not None and font_scale <= 0:
        raise SpecError("layout 'font_scale' must be positive")
    if step_x is not None and step_x <= 0:
        raise SpecError("layout 'step_x' must be positive")
    if step_y is not None and step_y <= 0:
        raise SpecError("layout 'step_y' must be positive")
    direction = data.get("direction")
    if layout_type == "staircase":
        direction = "descending" if direction is None else direction
        if direction not in STAIRCASE_DIRECTIONS:
            raise SpecError(
                f"staircase direction must be one of: {', '.join(sorted(STAIRCASE_DIRECTIONS))}"
            )
    else:
        direction = "clockwise" if direction is None else direction
        if direction != "clockwise":
            raise SpecError("ring direction currently must be 'clockwise'")
    return Layout(
        type=layout_type,
        card_width=card_width,
        card_height=card_height,
        column_gap=float(column_gap),
        row_gap=float(row_gap),
        column_width=column_width,
        row_height=row_height,
        direction=direction,
        margin=margin,
        font_scale=1.0 if font_scale is None else float(font_scale),
        icon_position=icon_position,
        step_x=step_x,
        step_y=step_y,
    )


def _parse_node(data: Any) -> Node:
    if not isinstance(data, dict):
        raise SpecError("each node must be an object")
    node_id = _required_string(data, "id", "node")
    title = _required_string(data, "title", f"node '{node_id}'")
    subtitle = data.get("subtitle", "")
    color = data.get("color", "blue")
    icon = data.get("icon")
    eyebrow = data.get("eyebrow", "")
    variant = data.get("variant", "card")
    show_label = data.get("show_label", True)
    icon_size = _optional_number(data, "icon_size", f"node '{node_id}'")
    if not isinstance(subtitle, str):
        raise SpecError(f"node '{node_id}' subtitle must be a string")
    if color not in COLORS:
        raise SpecError(f"node '{node_id}' has unknown color: {color}")
    if icon is not None and icon not in ICONS:
        raise SpecError(f"node '{node_id}' has unknown icon: {icon}")
    if not isinstance(eyebrow, str):
        raise SpecError(f"node '{node_id}' eyebrow must be a string")
    if variant not in NODE_VARIANTS:
        raise SpecError(
            f"node '{node_id}' variant must be one of: {', '.join(sorted(NODE_VARIANTS))}"
        )
    if variant == "icon" and icon is None:
        raise SpecError(f"node '{node_id}' with icon variant requires an icon")
    if not isinstance(show_label, bool):
        raise SpecError(f"node '{node_id}' show_label must be a boolean")
    if icon_size is not None and icon_size <= 0:
        raise SpecError(f"node '{node_id}' icon_size must be positive")
    width = _optional_number(data, "width", f"node '{node_id}'")
    height = _optional_number(data, "height", f"node '{node_id}'")
    if width is not None and width <= 0:
        raise SpecError(f"node '{node_id}' 'width' must be positive")
    if height is not None and height <= 0:
        raise SpecError(f"node '{node_id}' 'height' must be positive")
    return Node(
        id=node_id,
        title=title,
        subtitle=subtitle,
        color=color,
        icon=icon,
        eyebrow=eyebrow,
        variant=variant,
        show_label=show_label,
        icon_size=icon_size,
        x=_optional_number(data, "x", f"node '{node_id}'"),
        y=_optional_number(data, "y", f"node '{node_id}'"),
        width=width,
        height=height,
        row=_optional_nonnegative_int(data, "row", f"node '{node_id}'"),
        column=_optional_nonnegative_int(data, "column", f"node '{node_id}'"),
    )


def _optional_nonnegative_int(data: dict[str, Any], key: str, context: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SpecError(f"{context} '{key}' must be a non-negative integer")
    return value


def _parse_edge(data: Any) -> Edge:
    if not isinstance(data, dict):
        raise SpecError("each edge must be an object")
    source = _required_string(data, "from", "edge")
    target = _required_string(data, "to", "edge")
    label = data.get("label", "")
    color = data.get("color", "gray")
    route = data.get("route", "forward")
    source_anchor = data.get("from_anchor")
    target_anchor = data.get("to_anchor")
    bidirectional = data.get("bidirectional", False)
    if not isinstance(label, str):
        raise SpecError("edge label must be a string")
    if color not in COLORS:
        raise SpecError(f"edge has unknown color: {color}")
    if route not in ROUTES:
        raise SpecError(f"edge route must be one of: {', '.join(sorted(ROUTES))}")
    if source_anchor is not None and source_anchor not in ANCHORS:
        raise SpecError(f"edge from_anchor must be one of: {', '.join(sorted(ANCHORS))}")
    if target_anchor is not None and target_anchor not in ANCHORS:
        raise SpecError(f"edge to_anchor must be one of: {', '.join(sorted(ANCHORS))}")
    if not isinstance(bidirectional, bool):
        raise SpecError("edge bidirectional must be a boolean")
    controls = _parse_controls(data.get("controls"))
    if route == "curve" and controls is None:
        raise SpecError("a curve edge requires two control points")
    return Edge(
        source=source,
        target=target,
        label=label,
        color=color,
        route=route,
        source_anchor=source_anchor,
        target_anchor=target_anchor,
        controls=controls,
        bidirectional=bidirectional,
    )


def _parse_controls(data: Any) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if data is None:
        return None
    if not isinstance(data, list) or len(data) != 2:
        raise SpecError("edge controls must contain exactly two [x, y] points")
    points: list[tuple[float, float]] = []
    for point in data:
        if not isinstance(point, list) or len(point) != 2:
            raise SpecError("each edge control point must be [x, y]")
        x, y = point
        if not _is_number(x) or not _is_number(y):
            raise SpecError("edge control point coordinates must be numbers")
        points.append((float(x), float(y)))
    return points[0], points[1]


def _parse_dividers(data: Any, layout: Layout, nodes: tuple[Node, ...]) -> tuple[Divider, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise SpecError("'dividers' must be a list")
    if layout.type != "grid":
        raise SpecError("'dividers' currently requires the grid layout")
    rows = sorted({node.row for node in nodes if node.row is not None})
    dividers = []
    for item in data:
        if not isinstance(item, dict):
            raise SpecError("each divider must be an object")
        after_row = item.get("after_row")
        if not isinstance(after_row, int) or isinstance(after_row, bool):
            raise SpecError("divider after_row must be an integer")
        if after_row not in rows or after_row == rows[-1]:
            raise SpecError(f"divider after_row {after_row} has no row below it")
        dividers.append(Divider(after_row=after_row))
    return tuple(dividers)


def _parse_center(data: Any) -> CenterAnnotation | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise SpecError("'center' must be an object")
    title = data.get("title", "")
    subtitle = data.get("subtitle", "")
    detail = data.get("detail", "")
    radius = data.get("radius", 68)
    if not all(isinstance(value, str) for value in (title, subtitle, detail)):
        raise SpecError("center annotation title, subtitle and detail must be strings")
    if not (title or detail):
        raise SpecError("center annotation needs a 'title' or a 'detail'")
    if not _is_number(radius) or radius <= 0:
        raise SpecError("center annotation radius must be a positive number")
    return CenterAnnotation(title=title, subtitle=subtitle, detail=detail, radius=float(radius))


def _optional_number(data: dict[str, Any], key: str, context: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not _is_number(value):
        raise SpecError(f"{context} '{key}' must be a number")
    return float(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
