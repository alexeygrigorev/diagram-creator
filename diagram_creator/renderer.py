from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from pathlib import Path

from diagram_creator.spec import DiagramSpec, Edge, Node, SpecError


@dataclass(frozen=True)
class Palette:
    fill: str
    stroke: str


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2


PALETTES = {
    "purple": Palette("#f5f3ff", "#7c3aed"),
    "blue": Palette("#eff6ff", "#2563eb"),
    "amber": Palette("#fff7ed", "#c2410c"),
    "green": Palette("#ecfdf5", "#15803d"),
    "red": Palette("#fef2f2", "#dc2626"),
    "gray": Palette("#f8fafc", "#64748b"),
}

EDGE_COLORS = {name: palette.stroke for name, palette in PALETTES.items()}
SYMBOL_PATTERN = re.compile(r"<symbol\s+id=\"icon-(?P<name>[^\"]+)\".*?</symbol>", re.DOTALL)


def render_diagram(
    spec: DiagramSpec,
    output: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """Render one JSON-backed diagram as SVG or a Chromium-matched PNG."""
    canvas_width = spec.canvas.width if width is None else width
    canvas_height = spec.canvas.height if height is None else height
    _validate_canvas(canvas_width, canvas_height)

    destination = Path(output)
    suffix = destination.suffix.lower()
    if suffix not in {".svg", ".png"}:
        raise SpecError("output must have an .svg or .png extension")
    destination.parent.mkdir(parents=True, exist_ok=True)

    svg = render_svg_text(spec, width=canvas_width, height=canvas_height)
    if suffix == ".svg":
        destination.write_text(svg)
        return destination

    # Snap-packaged Chromium cannot access every pytest/system temporary mount.
    # Stage beside the current checkout, then copy the finished PNG to its target.
    with tempfile.TemporaryDirectory(prefix=".diagram-render-", dir=Path.cwd()) as raw:
        source = Path(raw) / "diagram.svg"
        source.write_text(svg)
        staged = Path(raw) / "diagram.png"
        _render_png(source, staged, canvas_width, canvas_height, spec.canvas.background)
        shutil.copyfile(staged, destination)
    return destination


def render_svg_text(
    spec: DiagramSpec,
    *,
    width: int | None = None,
    height: int | None = None,
) -> str:
    canvas_width = spec.canvas.width if width is None else width
    canvas_height = spec.canvas.height if height is None else height
    _validate_canvas(canvas_width, canvas_height)
    boxes = _layout(spec, canvas_width, canvas_height)
    symbols = _symbols_for(spec)
    markers = "\n".join(
        f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0 0 10 5 0 10Z" fill="{color}"/></marker>'
        for name, color in EDGE_COLORS.items()
    )
    description = spec.description or _default_description(spec)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" '
        f'height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}" '
        'role="img" aria-labelledby="title desc">',
        f'  <title id="title">{escape(spec.title)}</title>',
        f'  <desc id="desc">{escape(description)}</desc>',
        "  <defs>",
        '    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">',
        '      <feDropShadow dx="0" dy="4" stdDeviation="5" '
        'flood-color="#0f172a" flood-opacity="0.08"/>',
        "    </filter>",
        _indent(markers, 4),
        _indent(symbols, 4),
        _indent(_style(), 4),
        "  </defs>",
        f'  <rect width="{canvas_width}" height="{canvas_height}" '
        f'fill="{escape(spec.canvas.background)}"/>',
        "",
    ]
    parts.extend(_draw_edge(spec, edge, boxes, canvas_width, canvas_height) for edge in spec.edges)
    if spec.center is not None:
        parts.extend(("", _draw_center(spec, canvas_width, canvas_height)))
    parts.append("")
    parts.extend(_draw_node(node, boxes[node.id]) for node in spec.nodes)
    parts.append("</svg>\n")
    return "\n".join(parts)


def _layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    if spec.layout.type == "manual":
        default_width = spec.layout.card_width or 220
        default_height = spec.layout.card_height or 100
        return {
            node.id: Box(
                node.x or 0,
                node.y or 0,
                node.width or default_width,
                node.height or default_height,
            )
            for node in spec.nodes
        }
    if spec.layout.type == "ring":
        return _ring_layout(spec, width, height)
    return _horizontal_layout(spec, width, height)


def _horizontal_layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    count = len(spec.nodes)
    side_padding = width * 0.035
    minimum_gap = width * 0.06
    calculated_width = min(
        width * 0.18,
        (width - 2 * side_padding - minimum_gap * (count - 1)) / count,
    )
    card_width = spec.layout.card_width or calculated_width
    if card_width < 120:
        raise SpecError("the canvas is too narrow for the number of nodes")
    gap = (width - 2 * side_padding - card_width * count) / (count - 1)
    if gap < 20:
        raise SpecError("the canvas is too narrow for the requested card width")
    card_height = spec.layout.card_height or min(104.0, height * 0.31)
    card_y = height * 0.195
    return {
        node.id: Box(
            side_padding + index * (card_width + gap),
            card_y,
            node.width or card_width,
            node.height or card_height,
        )
        for index, node in enumerate(spec.nodes)
    }


def _ring_layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    card_width = spec.layout.card_width or 260
    card_height = spec.layout.card_height or 100
    x_scale = width / 1100
    y_scale = height / 550
    positions = (
        ((width - card_width) / 2, 20 * y_scale),
        (width - 80 * x_scale - card_width, 155 * y_scale),
        (width - 210 * x_scale - card_width, 415 * y_scale),
        (210 * x_scale, 415 * y_scale),
        (80 * x_scale, 155 * y_scale),
    )
    # The expanded expressions keep the right-hand positions mirrored when the canvas scales.
    return {
        node.id: Box(x, y, node.width or card_width, node.height or card_height)
        for node, (x, y) in zip(spec.nodes, positions, strict=True)
    }


def _draw_node(node: Node, box: Box) -> str:
    palette = PALETTES[node.color]
    icon_size = 28
    compact = box.height < 80
    icon_y = 19 if compact else (box.height - icon_size) / 2
    title_y = 27 if compact else box.height / 2 + 6
    subtitle_y = 50 if compact else box.height / 2 + 31
    center_x = box.width / 2
    radius = 16 if compact else 18
    lines = [
        f'  <g class="node node-{escape(node.color)}" '
        f'transform="translate({_number(box.x)} {_number(box.y)})" filter="url(#shadow)">',
        f'    <rect width="{_number(box.width)}" height="{_number(box.height)}" '
        f'rx="{radius}" fill="{palette.fill}" stroke="{palette.stroke}"/>',
    ]
    if node.eyebrow:
        lines.append(
            f'    <text class="eyebrow" x="{_number(center_x)}" y="25">'
            f"{escape(node.eyebrow)}</text>"
        )
    if node.icon == "mention":
        lines.append(
            f'    <text class="mention-icon" x="30" y="{_number(title_y + 3)}" '
            f'fill="{palette.stroke}">@</text>'
        )
    elif node.icon:
        lines.append(
            f'    <use href="#icon-{escape(node.icon)}" x="16" y="{_number(icon_y)}" '
            f'width="{icon_size}" height="{icon_size}" color="{palette.stroke}"/>'
        )
    title_x = 56 if node.icon else center_x
    title_class = "node-title icon-copy" if node.icon else "node-title"
    title_width = box.width - 72 if node.icon else box.width - 32
    fit = (
        f' textLength="{_number(title_width)}" lengthAdjust="spacingAndGlyphs"'
        if len(node.title) * 9.5 > title_width
        else ""
    )
    lines.append(
        f'    <text class="{title_class}" x="{_number(title_x)}" '
        f'y="{_number(title_y)}"{fit}>'
        f"{escape(node.title)}</text>"
    )
    if node.subtitle:
        lines.append(
            f'    <text class="node-subtitle" x="{_number(center_x)}" '
            f'y="{_number(subtitle_y)}">{escape(node.subtitle)}</text>'
        )
    lines.append("  </g>")
    return "\n".join(lines)


def _draw_edge(
    spec: DiagramSpec,
    edge: Edge,
    boxes: dict[str, Box],
    width: int,
    height: int,
) -> str:
    route = "ring" if spec.layout.type == "ring" and edge.route == "forward" else edge.route
    if route == "ring":
        path, label_point = _ring_path(spec, edge, boxes, width, height)
    elif route == "below":
        path, label_point = _below_path(edge, boxes, width, height)
    else:
        path, label_point = _direct_path(edge, boxes, curved=route == "curve")
    color = EDGE_COLORS[edge.color]
    line = (
        f'  <path class="edge" d="{path}" stroke="{color}" marker-end="url(#arrow-{edge.color})"/>'
    )
    if not edge.label:
        return line
    x, y = label_point
    label = escape(edge.label)
    pill_width = max(62, len(edge.label) * 9 + 24)
    return "\n".join(
        (
            line,
            f'  <g class="edge-label" transform="translate({_number(x)} {_number(y)})">',
            f'    <rect x="{-pill_width / 2}" y="-16" width="{pill_width}" height="32" '
            f'rx="16" fill="#ffffff" stroke="{color}"/>',
            f'    <text fill="{color}">{label}</text>',
            "  </g>",
        )
    )


def _ring_path(
    spec: DiagramSpec,
    edge: Edge,
    boxes: dict[str, Box],
    width: int,
    height: int,
) -> tuple[str, tuple[float, float]]:
    node_ids = [node.id for node in spec.nodes]
    source_index = node_ids.index(edge.source)
    target_index = node_ids.index(edge.target)
    if target_index != (source_index + 1) % len(node_ids):
        raise SpecError("ring edges must connect each node to the next node in JSON order")
    box = boxes[edge.source]
    target = boxes[edge.target]
    x_scale = width / 1100
    y_scale = height / 550

    if source_index == 0:
        start = (box.right, box.center_y)
        end = (target.center_x - 20 * x_scale, target.y)
        c1 = (start[0] + 90 * x_scale, start[1])
        c2 = (end[0] - 30 * x_scale, end[1] - 50 * y_scale)
    elif source_index == 1:
        start = (box.center_x, box.bottom)
        end = (target.center_x + 20 * x_scale, target.y)
        c1 = (start[0], start[1] + 75 * y_scale)
        c2 = (end[0] + 70 * x_scale, end[1] - 35 * y_scale)
    elif source_index == 2:
        start = (box.x, box.center_y)
        end = (target.right, target.center_y)
        return _line_path(start, end)
    elif source_index == 3:
        start = (box.center_x - 20 * x_scale, box.y)
        end = (target.center_x, target.bottom)
        c1 = (start[0] - 70 * x_scale, start[1] - 35 * y_scale)
        c2 = (end[0], end[1] + 75 * y_scale)
    else:
        start = (box.center_x + 20 * x_scale, box.y)
        end = (target.x, target.center_y)
        c1 = (start[0] + 30 * x_scale, start[1] - 50 * y_scale)
        c2 = (end[0] - 90 * x_scale, end[1])
    path = f"M{_point(start)}C{_point(c1)} {_point(c2)} {_point(end)}"
    return path, _bezier_midpoint(start, c1, c2, end)


def _direct_path(
    edge: Edge,
    boxes: dict[str, Box],
    *,
    curved: bool,
) -> tuple[str, tuple[float, float]]:
    source = boxes[edge.source]
    target = boxes[edge.target]
    start_anchor, end_anchor = _default_anchors(source, target)
    start = _anchor(source, edge.source_anchor or start_anchor)
    end = _anchor(target, edge.target_anchor or end_anchor)
    if curved:
        assert edge.controls is not None
        c1, c2 = edge.controls
        path = f"M{_point(start)}C{_point(c1)} {_point(c2)} {_point(end)}"
        return path, _bezier_midpoint(start, c1, c2, end)
    return _line_path(start, end)


def _below_path(
    edge: Edge,
    boxes: dict[str, Box],
    width: int,
    height: int,
) -> tuple[str, tuple[float, float]]:
    source = boxes[edge.source]
    target = boxes[edge.target]
    start = _anchor(source, edge.source_anchor or "bottom")
    end = _anchor(target, edge.target_anchor or "bottom")
    start = (start[0], start[1] + height * 0.035)
    end = (end[0], end[1] + height * 0.045)
    loop_y = height * 0.77
    path = f"M{_point(start)}V{_number(loop_y)}H{_number(end[0])}V{_number(end[1])}"
    return path, ((start[0] + end[0]) / 2, loop_y)


def _line_path(
    start: tuple[float, float], end: tuple[float, float]
) -> tuple[str, tuple[float, float]]:
    return (
        f"M{_point(start)}L{_point(end)}",
        ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
    )


def _default_anchors(source: Box, target: Box) -> tuple[str, str]:
    dx = target.center_x - source.center_x
    dy = target.center_y - source.center_y
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def _anchor(box: Box, name: str) -> tuple[float, float]:
    anchors = {
        "left": (box.x, box.center_y),
        "right": (box.right, box.center_y),
        "top": (box.center_x, box.y),
        "bottom": (box.center_x, box.bottom),
    }
    return anchors[name]


def _bezier_midpoint(
    start: tuple[float, float],
    c1: tuple[float, float],
    c2: tuple[float, float],
    end: tuple[float, float],
) -> tuple[float, float]:
    return tuple((start[i] + 3 * c1[i] + 3 * c2[i] + end[i]) / 8 for i in range(2))  # type: ignore[return-value]


def _draw_center(spec: DiagramSpec, width: int, height: int) -> str:
    assert spec.center is not None
    center = spec.center
    x = width / 2
    y = height * 285 / 550 if spec.layout.type == "ring" else height / 2
    lines = [
        f'  <circle class="center-annotation" cx="{_number(x)}" cy="{_number(y)}" '
        f'r="{_number(center.radius)}"/>',
        f'  <text class="center-title" x="{_number(x)}" y="{_number(y - 5)}">'
        f"{escape(center.title)}</text>",
    ]
    if center.subtitle:
        lines.append(
            f'  <text class="center-title" x="{_number(x)}" y="{_number(y + 18)}">'
            f"{escape(center.subtitle)}</text>"
        )
    if center.detail:
        detail_y = y + 43 if center.subtitle else y + 25
        lines.append(
            f'  <text class="center-detail" x="{_number(x)}" y="{_number(detail_y)}">'
            f"{escape(center.detail)}</text>"
        )
    return "\n".join(lines)


def _symbols_for(spec: DiagramSpec) -> str:
    names = {node.icon for node in spec.nodes if node.icon and node.icon != "mention"}
    if not names:
        return ""
    source = _icons_path().read_text()
    available = {match.group("name"): match.group(0) for match in SYMBOL_PATTERN.finditer(source)}
    missing = names - available.keys()
    if missing:
        raise SpecError(f"icon definitions are missing for: {', '.join(sorted(missing))}")
    return "\n".join(available[name] for name in sorted(names))


def _icons_path() -> Path:
    packaged = Path(str(files("diagram_creator").joinpath("assets/icons.svg")))
    if packaged.is_file():
        return packaged
    checkout = Path(__file__).resolve().parents[1] / "skills/diagram-creator/assets/icons.svg"
    if checkout.is_file():
        return checkout
    raise SpecError("the bundled icon library could not be found")


def _style() -> str:
    return """<style>
  text { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #172033; }
  .node rect { stroke-width: 2; }
  .node-title { font-size: 16px; font-weight: 750; text-anchor: middle; }
  .node-title.icon-copy { text-anchor: start; }
  .node-subtitle { font-size: 14px; font-weight: 500; fill: #64748b; text-anchor: middle; }
  .eyebrow { font-size: 12px; font-weight: 750; letter-spacing: 1px; fill: #64748b; text-anchor: middle; }
  .mention-icon { font-size: 27px; font-weight: 750; text-anchor: middle; }
  .edge { fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
  .edge-label rect { stroke-width: 2; }
  .edge-label text { font-size: 14px; font-weight: 750; text-anchor: middle; dominant-baseline: central; }
  .center-annotation { fill: #f8fafc; stroke: #cbd5e1; stroke-width: 2; stroke-dasharray: 7 7; }
  .center-title { font-size: 16px; font-weight: 800; letter-spacing: 1.3px; fill: #334155; text-anchor: middle; }
  .center-detail { font-size: 13px; font-weight: 600; fill: #64748b; text-anchor: middle; }
</style>"""


def _default_description(spec: DiagramSpec) -> str:
    return " → ".join(node.title for node in spec.nodes)


def _validate_canvas(width: int, height: int) -> None:
    if width < 600:
        raise SpecError("width must be at least 600 pixels")
    if height < 280:
        raise SpecError("height must be at least 280 pixels")


def _render_png(source: Path, destination: Path, width: int, height: int, background: str) -> None:
    browser = next(
        (
            resolved
            for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
            if (resolved := shutil.which(name))
        ),
        None,
    )
    if browser is None:
        raise SpecError("Chromium is required to render PNG output; render SVG instead")
    normalized = background.removeprefix("#")
    background_flag = (
        normalized.upper() + "FF" if re.fullmatch(r"[0-9a-fA-F]{6}", normalized) else "FFFFFFFF"
    )
    command = [
        browser,
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--default-background-color={background_flag}",
        f"--window-size={width},{height}",
        f"--screenshot={destination.resolve()}",
        source.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not destination.is_file():
        details = (result.stderr or result.stdout).strip()
        raise SpecError(f"Chromium failed to render the SVG: {details}")


def _point(point: tuple[float, float]) -> str:
    return f"{_number(point[0])} {_number(point[1])}"


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())
