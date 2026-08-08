from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from pathlib import Path

from diagram_creator.spec import CenterAnnotation, DiagramSpec, Edge, Node, SpecError


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
RING_MARGIN = 40
RING_EDGE_GAP = 0
RING_ARC_SAMPLES = 240
RING_CARD_GAP = 24
# How much the ring's connectors may differ in length before the diagram is
# rejected. Unequal arrows are the most visible way a loop stops reading as one
# circle, so this is enforced rather than left to whoever picks the card size.
RING_CHORD_TOLERANCE = 0.10
STAIRCASE_MARGIN = 40
STAIRCASE_STEP_GAP = 18
# The tightest horizontal advance, as a share of the card width. Cards may
# overlap sideways because consecutive steps never share a row, but past this
# point the treads are too short to read as a staircase.
STAIRCASE_MIN_ADVANCE = 0.6
STEP_CORNER = 12
ICON_GUTTER = 12
ICON_SIZE = 34
TITLE_SIZE, TITLE_WEIGHT = 20, 750
SUBTITLE_SIZE, SUBTITLE_WEIGHT = 16, 500
DETAIL_SIZE, DETAIL_WEIGHT = 16, 600
ANNOTATION_PADDING = 14
CENTER_TITLE_RATIO, CENTER_DETAIL_RATIO = 0.22, 0.72
CENTER_TITLE_MIN, CENTER_TITLE_MAX = 16, 44
CENTER_TRACKING = 0.08
CENTER_DETAIL_LINES = 3
CAP_HALF, CAP_HEIGHT = 0.36, 0.72
TITLE_GAP = 10
# Where each icon's ink actually starts and ends inside its box, as a fraction of
# the box, measured by scripts/measure_icons.py. Artwork does not fill the slot
# evenly, so centring an icon-and-label group on the box leaves the group looking
# off-centre and the icon-to-text gap different on every card.
ICON_INK = {
    "api": (0.083, 0.917),
    "browser": (0.025, 0.975),
    "check": (0.083, 0.917),
    "close": (0.083, 0.917),
    "database": (0.158, 0.842),
    "document": (0.208, 0.792),
    "github": (0.025, 0.975),
    "issue": (0.083, 0.917),
    "message": (0.125, 0.875),
    "number-1": (0.042, 0.958),
    "number-2": (0.042, 0.958),
    "number-3": (0.042, 0.958),
    "openai": (0.0, 1.0),
    "pull-request": (0.108, 0.892),
    "rank-fusion": (0.083, 0.917),
    "search": (0.15, 0.892),
    "settings": (0.042, 0.958),
    "sparkles": (0.05, 0.95),
    "user": (0.167, 0.833),
    "video": (0.083, 0.917),
    "warning": (0.067, 0.933),
    "websocket": (0.125, 0.875),
}
DEFAULT_ICON_INK = (0.083, 0.917)
EYEBROW_SIZE = 13
EYEBROW_INK, EYEBROW_GAP = 10, 10
SUBTITLE_GAP, SUBTITLE_ASCENT, SUBTITLE_DESCENT = 9, 12, 5
SUBTITLE_LINE, SUBTITLE_LINES = 22, 3
# Advance widths per 1 px of font size for the card font stack, measured out of
# Chromium by scripts/measure_text.py. Widths scale linearly with font size to
# within 0.1 px, so one table per weight covers every size the cards use.
CHARACTER_EM = {
    500: {
        " ": 0.3179,
        "!": 0.4,
        "#": 0.8357,
        "%": 0.95,
        "&": 0.7786,
        "'": 0.2714,
        "(": 0.3929,
        ")": 0.3929,
        "+": 0.8429,
        ",": 0.3143,
        "-": 0.3571,
        ".": 0.3143,
        "/": 0.3357,
        "0": 0.6357,
        "1": 0.6357,
        "2": 0.6357,
        "3": 0.6357,
        "4": 0.6357,
        "5": 0.6357,
        "6": 0.6357,
        "7": 0.6357,
        "8": 0.6357,
        "9": 0.6357,
        ":": 0.3357,
        ";": 0.3357,
        "?": 0.5286,
        "@": 1.0,
        "A": 0.7071,
        "B": 0.6857,
        "C": 0.7,
        "D": 0.7714,
        "E": 0.6357,
        "F": 0.5786,
        "G": 0.7714,
        "H": 0.7571,
        "I": 0.3,
        "J": 0.3,
        "K": 0.65,
        "L": 0.5571,
        "M": 0.8643,
        "N": 0.75,
        "O": 0.7857,
        "P": 0.6,
        "Q": 0.7857,
        "R": 0.6929,
        "S": 0.6357,
        "T": 0.5929,
        "U": 0.7286,
        "V": 0.6857,
        "W": 0.9929,
        "X": 0.6857,
        "Y": 0.6071,
        "Z": 0.6857,
        "_": 0.5,
        "a": 0.6143,
        "b": 0.6357,
        "c": 0.55,
        "d": 0.6357,
        "e": 0.6143,
        "f": 0.3429,
        "g": 0.6357,
        "h": 0.6357,
        "i": 0.2786,
        "j": 0.2786,
        "k": 0.5786,
        "l": 0.2786,
        "m": 0.9714,
        "n": 0.6357,
        "o": 0.6071,
        "p": 0.6357,
        "q": 0.6357,
        "r": 0.3929,
        "s": 0.5214,
        "t": 0.3929,
        "u": 0.6357,
        "v": 0.5929,
        "w": 0.8214,
        "x": 0.5929,
        "y": 0.5929,
        "z": 0.5286,
        "→": 0.8357,
    },
    750: {
        " ": 0.3469,
        "!": 0.4562,
        "#": 0.8375,
        "%": 1.0063,
        "&": 0.875,
        "'": 0.3063,
        "(": 0.4562,
        ")": 0.4562,
        "+": 0.8375,
        ",": 0.3812,
        "-": 0.4125,
        ".": 0.3812,
        "/": 0.3625,
        "0": 0.6937,
        "1": 0.6937,
        "2": 0.7,
        "3": 0.6937,
        "4": 0.6937,
        "5": 0.6937,
        "6": 0.6937,
        "7": 0.6937,
        "8": 0.6937,
        "9": 0.6937,
        ":": 0.4,
        ";": 0.4,
        "?": 0.5813,
        "@": 1.0,
        "A": 0.7688,
        "B": 0.7625,
        "C": 0.7312,
        "D": 0.8313,
        "E": 0.6813,
        "F": 0.6813,
        "G": 0.8187,
        "H": 0.8313,
        "I": 0.3688,
        "J": 0.3688,
        "K": 0.775,
        "L": 0.6375,
        "M": 0.9938,
        "N": 0.8313,
        "O": 0.85,
        "P": 0.7312,
        "Q": 0.85,
        "R": 0.7688,
        "S": 0.675,
        "T": 0.7063,
        "U": 0.8125,
        "V": 0.7688,
        "W": 1.1062,
        "X": 0.775,
        "Y": 0.725,
        "Z": 0.725,
        "_": 0.5,
        "a": 0.675,
        "b": 0.7188,
        "c": 0.5938,
        "d": 0.7188,
        "e": 0.675,
        "f": 0.4062,
        "g": 0.7188,
        "h": 0.7125,
        "i": 0.3375,
        "j": 0.3375,
        "k": 0.6625,
        "l": 0.3375,
        "m": 1.0437,
        "n": 0.7125,
        "o": 0.6875,
        "p": 0.7188,
        "q": 0.7188,
        "r": 0.4938,
        "s": 0.5938,
        "t": 0.475,
        "u": 0.7063,
        "v": 0.6562,
        "w": 0.925,
        "x": 0.6438,
        "y": 0.6562,
        "z": 0.5813,
        "→": 0.8375,
    },
}
# An unmeasured glyph falls back to the table's own average rather than a guess.
FALLBACK_EM = {weight: sum(table.values()) / len(table) for weight, table in CHARACTER_EM.items()}
DEFAULT_STANDALONE_ICON_SIZE = 56
STANDALONE_ICON_DIMENSIONS = {
    "user": (56, 56),
    "browser": (160, 112),
    "database": (84, 84),
}
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
    if spec.layout.type == "ring":
        _check_ring_chords(spec, _ring_geometry(spec, canvas_width, canvas_height), boxes)
    symbols = _symbols_for(spec)
    markers = "\n".join(
        f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="9" markerHeight="9" orient="auto">'
        f'<path d="M0 0 10 5 0 10Z" fill="{color}"/></marker>'
        for name, color in EDGE_COLORS.items()
    )
    start_marker_colors = {edge.color for edge in spec.edges if edge.bidirectional}
    start_markers = "\n".join(
        f'<marker id="arrow-start-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
        f'<path d="M0 0 10 5 0 10Z" fill="{EDGE_COLORS[name]}"/></marker>'
        for name in sorted(start_marker_colors)
    )
    marker_defs = markers + ("\n" + start_markers if start_markers else "")
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
        _indent(marker_defs, 4),
        _indent(symbols, 4),
        _indent(_style(), 4),
        "  </defs>",
        f'  <rect width="{canvas_width}" height="{canvas_height}" '
        f'fill="{escape(spec.canvas.background)}"/>',
        "",
    ]
    parts.extend(_draw_dividers(spec, boxes, canvas_width))
    parts.extend(_draw_edge(spec, edge, boxes, canvas_width, canvas_height) for edge in spec.edges)
    if spec.center is not None:
        parts.extend(("", _draw_center(spec, canvas_width, canvas_height)))
    parts.append("")
    title_size = _card_title_size(spec, boxes)
    subtitle_size = _card_subtitle_size(spec, boxes)
    stacked = spec.layout.icon_position == "block"
    parts.extend(
        _draw_node(
            node,
            boxes[node.id],
            spec.layout.font_scale,
            title_size,
            subtitle_size,
            stacked,
        )
        for node in spec.nodes
    )
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
                node.width
                or (
                    _standalone_icon_dimensions(node)[0]
                    if node.variant == "icon"
                    else default_width
                ),
                node.height
                or (
                    _standalone_icon_dimensions(node)[1]
                    if node.variant == "icon"
                    else default_height
                ),
            )
            for node in spec.nodes
        }
    if spec.layout.type == "ring":
        return _ring_layout(spec, width, height)
    if spec.layout.type == "grid":
        return _grid_layout(spec, width, height)
    if spec.layout.type == "staircase":
        return _staircase_layout(spec, width, height)
    return _horizontal_layout(spec, width, height)


def _staircase_layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    """Cascade equal cards one tread right and one riser down (or up) per step."""
    count = len(spec.nodes)
    card_width = spec.layout.card_width or 260
    card_height = spec.layout.card_height or 100
    margin = STAIRCASE_MARGIN if spec.layout.margin is None else spec.layout.margin
    available_width = width - 2 * margin
    available_height = height - 2 * margin

    step_y = spec.layout.step_y or card_height + STAIRCASE_STEP_GAP
    if step_y < card_height:
        raise SpecError("staircase 'step_y' must be at least the card height so steps stay apart")
    if spec.layout.step_x is not None:
        step_x = spec.layout.step_x
    else:
        # Spread the treads over the canvas, but never past the point where
        # consecutive cards pull apart, and never tighter than the overlap limit.
        filled = (available_width - card_width) / (count - 1)
        step_x = min(max(filled, card_width * STAIRCASE_MIN_ADVANCE), card_width)

    total_width = card_width + (count - 1) * step_x
    total_height = card_height + (count - 1) * step_y
    if total_width > available_width or total_height > available_height:
        raise SpecError(
            "the canvas is too small for this staircase; use at least "
            f"{math.ceil(total_width + 2 * margin)}x{math.ceil(total_height + 2 * margin)} "
            "or smaller cards"
        )

    left = margin + (available_width - total_width) / 2
    top = margin + (available_height - total_height) / 2
    descending = spec.layout.direction == "descending"
    return {
        node.id: Box(
            left + index * step_x,
            top + (index if descending else count - 1 - index) * step_y,
            node.width or card_width,
            node.height or card_height,
        )
        for index, node in enumerate(spec.nodes)
    }


def _grid_layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    default_width = spec.layout.card_width or 220
    default_height = spec.layout.card_height or 100
    dimensions: dict[str, tuple[float, float]] = {}
    for node in spec.nodes:
        if node.variant == "icon":
            token_width, token_height = _standalone_icon_dimensions(node)
            dimensions[node.id] = (node.width or token_width, node.height or token_height)
        else:
            dimensions[node.id] = (node.width or default_width, node.height or default_height)

    columns = sorted({node.column for node in spec.nodes if node.column is not None})
    rows = sorted({node.row for node in spec.nodes if node.row is not None})
    if spec.layout.column_width is not None:
        column_widths = {column: spec.layout.column_width for column in columns}
    else:
        column_widths = {
            column: max(dimensions[node.id][0] for node in spec.nodes if node.column == column)
            for column in columns
        }
    if spec.layout.row_height is not None:
        row_heights = {row: spec.layout.row_height for row in rows}
    else:
        row_heights = {
            row: max(dimensions[node.id][1] for node in spec.nodes if node.row == row)
            for row in rows
        }
    for node in spec.nodes:
        assert node.column is not None and node.row is not None
        node_width, node_height = dimensions[node.id]
        if node_width > column_widths[node.column] or node_height > row_heights[node.row]:
            raise SpecError(f"grid cell is too small for node '{node.id}'")
    grid_width = sum(column_widths.values()) + spec.layout.column_gap * (len(columns) - 1)
    grid_height = sum(row_heights.values()) + spec.layout.row_gap * (len(rows) - 1)
    if grid_width > width or grid_height > height:
        raise SpecError("the canvas is too small for the requested grid")

    column_x: dict[int, float] = {}
    cursor_x = (width - grid_width) / 2
    for column in columns:
        column_x[column] = cursor_x
        cursor_x += column_widths[column] + spec.layout.column_gap
    row_y: dict[int, float] = {}
    cursor_y = (height - grid_height) / 2
    for row in rows:
        row_y[row] = cursor_y
        cursor_y += row_heights[row] + spec.layout.row_gap

    boxes: dict[str, Box] = {}
    for node in spec.nodes:
        assert node.column is not None and node.row is not None
        node_width, node_height = dimensions[node.id]
        boxes[node.id] = Box(
            column_x[node.column] + (column_widths[node.column] - node_width) / 2,
            row_y[node.row] + (row_heights[node.row] - node_height) / 2,
            node_width,
            node_height,
        )
    return boxes


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


@dataclass(frozen=True)
class Ring:
    """The circle that ring-layout card centers sit on."""

    center_x: float
    center_y: float
    radius: float
    count: int

    def angle(self, index: int) -> float:
        """Clockwise angle of one slot, measured from the top of the circle."""
        return 2 * math.pi * index / self.count

    def point(self, angle: float) -> tuple[float, float]:
        return (
            self.center_x + self.radius * math.sin(angle),
            self.center_y - self.radius * math.cos(angle),
        )


def _ring_geometry(spec: DiagramSpec, width: int, height: int) -> Ring:
    """Fit the largest circle whose cards still clear the canvas margin."""
    count = len(spec.nodes)
    card_width = spec.layout.card_width or 260
    card_height = spec.layout.card_height or 100
    margin = RING_MARGIN if spec.layout.margin is None else spec.layout.margin
    sizes = [(node.width or card_width, node.height or card_height) for node in spec.nodes]
    # Card centers on a unit circle, first slot at the top and running clockwise.
    offsets = [
        (math.sin(2 * math.pi * index / count), -math.cos(2 * math.pi * index / count))
        for index in range(count)
    ]

    def extents(radius: float) -> tuple[float, float, float, float]:
        spans = [
            (
                radius * offset_x - size_width / 2,
                radius * offset_x + size_width / 2,
                radius * offset_y - size_height / 2,
                radius * offset_y + size_height / 2,
            )
            for (offset_x, offset_y), (size_width, size_height) in zip(offsets, sizes, strict=True)
        ]
        return (
            min(span[0] for span in spans),
            max(span[1] for span in spans),
            min(span[2] for span in spans),
            max(span[3] for span in spans),
        )

    available_width = width - 2 * margin
    available_height = height - 2 * margin
    limit = float(max(width, height))

    def fits(radius: float) -> bool:
        left, right, top, bottom = extents(radius)
        return right - left <= available_width and bottom - top <= available_height

    fitted = _bisect(limit, fits, keep_low=True)
    spaced = _bisect(
        limit, lambda radius: _ring_cards_clear(offsets, sizes, radius), keep_low=False
    )
    if not fits(spaced):
        left, right, top, bottom = extents(spaced)
        raise SpecError(
            "ring layout cards overlap on this canvas; use at least "
            f"{math.ceil(right - left + 2 * margin)}x{math.ceil(bottom - top + 2 * margin)} "
            "or smaller cards"
        )

    left, right, top, bottom = extents(fitted)
    return Ring(
        center_x=margin + (available_width - (right - left)) / 2 - left,
        center_y=margin + (available_height - (bottom - top)) / 2 - top,
        radius=fitted,
        count=count,
    )


def _ring_cards_clear(
    offsets: list[tuple[float, float]],
    sizes: list[tuple[float, float]],
    radius: float,
) -> bool:
    """True when every pair of cards keeps a visible gap at this radius.

    Measured edge to edge, not as padded bounding boxes: two cards set apart on a
    diagonal are well clear of each other even when both their x and y spans
    overlap once padding is added.
    """
    for first in range(len(offsets)):
        for second in range(first + 1, len(offsets)):
            gap_x = (
                abs(offsets[first][0] - offsets[second][0]) * radius
                - (sizes[first][0] + sizes[second][0]) / 2
            )
            gap_y = (
                abs(offsets[first][1] - offsets[second][1]) * radius
                - (sizes[first][1] + sizes[second][1]) / 2
            )
            if gap_x < 0 and gap_y < 0:
                return False
            if math.hypot(max(gap_x, 0), max(gap_y, 0)) < RING_CARD_GAP:
                return False
    return True


def _bisect(limit: float, holds: Callable[[float], bool], *, keep_low: bool) -> float:
    """Find the boundary radius of a monotone predicate over ``[0, limit]``.

    ``keep_low`` returns the largest radius that still holds; otherwise the
    smallest radius that starts holding.
    """
    low, high = 0.0, limit
    for _ in range(64):
        candidate = (low + high) / 2
        if holds(candidate) == keep_low:
            low = candidate
        else:
            high = candidate
    return low if keep_low else high


def _ring_chords(spec: DiagramSpec, ring: Ring, boxes: dict[str, Box]) -> list[float]:
    """Straight-line length of every connector, in JSON order."""
    span = 2 * math.pi / ring.count
    lengths = []
    for index, node in enumerate(spec.nodes):
        following = spec.nodes[(index + 1) % len(spec.nodes)]
        start = _ring_exit(ring, boxes[node.id], ring.angle(index), span)
        end = _ring_exit(ring, boxes[following.id], ring.angle(index) + span, -span)
        first, second = ring.point(start), ring.point(end)
        lengths.append(math.hypot(second[0] - first[0], second[1] - first[1]))
    return lengths


def _check_ring_chords(spec: DiagramSpec, ring: Ring, boxes: dict[str, Box]) -> None:
    """Reject a ring whose connectors would come out visibly different lengths.

    A card presents a different angular width at each slot unless it is close to
    square, so a wide flat card makes the arc between the bottom pair far shorter
    than the arc over the top. Squaring the card up is the fix, so the error says
    which height would do it.
    """
    lengths = _ring_chords(spec, ring, boxes)
    if not lengths or min(lengths) <= 0:
        return
    spread = (max(lengths) - min(lengths)) / min(lengths)
    if spread <= RING_CHORD_TOLERANCE:
        return
    width = spec.layout.card_width or 260
    suggestion = _ring_even_height(spec, ring, boxes, width)
    advice = (
        f"; card_height of about {suggestion:.0f} evens them out"
        if suggestion is not None
        else "; use a squarer card"
    )
    raise SpecError(
        f"ring connectors differ in length by {spread:.0%} "
        f"(longest {max(lengths):.0f}px, shortest {min(lengths):.0f}px){advice}"
    )


def _ring_even_height(
    spec: DiagramSpec, ring: Ring, boxes: dict[str, Box], width: float
) -> float | None:
    """The card height that brings the connectors closest to equal length."""
    # Only heights that could hold a card's content are worth suggesting; a
    # sliver of a card also evens the arcs out, and is no use to anyone.
    best: tuple[float, float] | None = None
    for step in range(30, 251):
        candidate = width * step / 100
        trial = {
            key: Box(box.center_x - width / 2, box.center_y - candidate / 2, width, candidate)
            for key, box in boxes.items()
        }
        lengths = _ring_chords(spec, ring, trial)
        if min(lengths) <= 0:
            continue
        spread = (max(lengths) - min(lengths)) / min(lengths)
        if best is None or spread < best[0]:
            best = (spread, candidate)
    return None if best is None or best[0] > RING_CHORD_TOLERANCE else best[1]


def _ring_layout(spec: DiagramSpec, width: int, height: int) -> dict[str, Box]:
    card_width = spec.layout.card_width or 260
    card_height = spec.layout.card_height or 100
    ring = _ring_geometry(spec, width, height)
    boxes = {}
    for index, node in enumerate(spec.nodes):
        box_width = node.width or card_width
        box_height = node.height or card_height
        center_x, center_y = ring.point(ring.angle(index))
        boxes[node.id] = Box(
            center_x - box_width / 2, center_y - box_height / 2, box_width, box_height
        )
    return boxes


def _wrap_lines(text: str, available: float, size: int, weight: int, limit: int) -> list[str]:
    """Break a line at spaces so a card can be narrow without truncating copy."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if current and _text_width(candidate, size, weight) > available:
            lines.append(current)
            current = word
            if len(lines) == limit - 1:
                # The last line takes whatever is left and is squeezed if need be.
                remainder = text.split()[text.split().index(word) :]
                lines.append(" ".join(remainder))
                return lines
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def _text_width(text: str, size: int, weight: int) -> float:
    # A weight without its own table measures against the next heavier one, so an
    # estimate is never short and text never overflows the column it was sized for.
    measured = min((known for known in CHARACTER_EM if known >= weight), default=max(CHARACTER_EM))
    table, fallback = CHARACTER_EM[measured], FALLBACK_EM[measured]
    return size * sum(table.get(character, fallback) for character in text)


def _card_title_size(spec: DiagramSpec, boxes: dict[str, Box]) -> int:
    """The largest title size at or below the requested one that fits every card.

    Squeezing a title with `textLength` distorts the letterforms - a 37 percent
    squeeze is plainly visible next to an untouched neighbour - and it makes the
    type inconsistent across a diagram. Stepping the size down instead keeps
    every title in the same, undistorted face.
    """
    scale = spec.layout.font_scale
    wanted = round(TITLE_SIZE * scale)
    icon_size, gutter = round(ICON_SIZE * scale), ICON_GUTTER * scale
    # An icon above the title leaves the title the card's full inner width.
    stacked = spec.layout.icon_position == "block"
    for size in range(wanted, 7, -1):
        if all(
            _text_width(node.title, size, TITLE_WEIGHT)
            <= boxes[node.id].width
            - 32
            - (
                0
                if stacked or not node.icon
                else (
                    ICON_INK.get(node.icon or "", DEFAULT_ICON_INK)[1]
                    - ICON_INK.get(node.icon or "", DEFAULT_ICON_INK)[0]
                )
                * icon_size
                + gutter
            )
            for node in spec.nodes
            if node.variant != "icon"
        ):
            return size
    return 8


def _card_subtitle_size(spec: DiagramSpec, boxes: dict[str, Box]) -> int:
    """The largest subtitle size whose wrapped lines fit every card undistorted."""
    wanted = round(SUBTITLE_SIZE * spec.layout.font_scale)
    for size in range(wanted, 7, -1):
        if all(
            all(
                _text_width(line, size, SUBTITLE_WEIGHT) <= boxes[node.id].width - 32
                for line in _wrap_lines(
                    node.subtitle, boxes[node.id].width - 32, size, SUBTITLE_WEIGHT, SUBTITLE_LINES
                )
            )
            for node in spec.nodes
            if node.subtitle and node.variant != "icon"
        ):
            return size
    return 8


def _draw_node(
    node: Node,
    box: Box,
    scale: float = 1.0,
    title_size: int | None = None,
    subtitle_size: int | None = None,
    stacked: bool = False,
) -> str:
    palette = PALETTES[node.color]
    if node.variant == "icon":
        return _draw_icon_node(node, box, palette)
    plain = node.variant == "plain"
    # One scale drives glyph sizes and the vertical rhythm together, so a card
    # with bigger type keeps the same proportions rather than just crowding.
    title_size = round(TITLE_SIZE * scale) if title_size is None else title_size
    subtitle_size = round(SUBTITLE_SIZE * scale) if subtitle_size is None else subtitle_size
    eyebrow_size = round(EYEBROW_SIZE * scale)
    icon_size = round(ICON_SIZE * scale)
    gutter = ICON_GUTTER * scale
    compact = box.height < 80
    subtitle_lines = (
        _wrap_lines(node.subtitle, box.width - 32, subtitle_size, SUBTITLE_WEIGHT, SUBTITLE_LINES)
        if node.subtitle
        else []
    )
    # Every row the card carries belongs to one block centered on the card, so
    # the stack is measured top-down and then placed, rather than nudged.
    stacked = stacked and bool(node.icon)
    title_row = round(title_size * CAP_HEIGHT) if stacked else 0
    title_room_above = (TITLE_GAP * scale + title_row) if stacked else 0
    eyebrow_room = (EYEBROW_INK + EYEBROW_GAP) * scale if node.eyebrow else 0
    subtitle_room = (
        (SUBTITLE_GAP + SUBTITLE_ASCENT + (len(subtitle_lines) - 1) * SUBTITLE_LINE) * scale
        if subtitle_lines
        else 0
    ) + SUBTITLE_DESCENT * scale
    block_top = (box.height - (eyebrow_room + icon_size + title_room_above + subtitle_room)) / 2
    icon_y = 19 if compact else block_top + eyebrow_room
    # The title's cap height centres on the icon's middle, not its baseline, or
    # the glyph hangs below the text it labels.
    if stacked:
        title_y = icon_y + icon_size + TITLE_GAP * scale + title_row
    else:
        title_y = 27 if compact else icon_y + icon_size / 2 + title_size * CAP_HALF
    subtitle_y = 50 if compact else icon_y + icon_size + (SUBTITLE_GAP + SUBTITLE_ASCENT) * scale
    eyebrow_y = 25 if compact else block_top + EYEBROW_INK * scale
    center_x = box.width / 2
    radius = 16 if compact else 18
    shadow = "" if plain else ' filter="url(#shadow)"'
    variant_class = "node node-plain" if plain else "node"
    lines = [
        f'  <g class="{variant_class} node-{escape(node.color)}" '
        f'transform="translate({_number(box.x)} {_number(box.y)})"{shadow}>',
    ]
    if not plain:
        lines.append(
            f'    <rect width="{_number(box.width)}" height="{_number(box.height)}" '
            f'rx="{radius}" fill="{palette.fill}" stroke="{palette.stroke}"/>'
        )
    if node.eyebrow:
        lines.append(
            f'    <text class="eyebrow" x="{_number(center_x)}" y="{_number(eyebrow_y)}" '
            f'font-size="{eyebrow_size}">'
            f"{escape(node.eyebrow)}</text>"
        )
    # Icon and title are one centered group: a left-aligned row would leave the
    # right half of the card empty, and a centered subtitle under a left-aligned
    # title puts the two lines on competing axes.
    ink_start, ink_end = ICON_INK.get(node.icon or "", DEFAULT_ICON_INK)
    ink_left, ink_width = ink_start * icon_size, (ink_end - ink_start) * icon_size
    title_width = box.width - 32 - (0 if stacked or not node.icon else ink_width + gutter)
    title_room = min(_text_width(node.title, title_size, TITLE_WEIGHT), title_width)
    # Centre what is visible: the icon's ink plus the gutter plus the title.
    if stacked:
        group_x = (box.width - ink_width) / 2 - ink_left
    elif node.icon:
        group_x = (box.width - (ink_width + gutter + title_room)) / 2 - ink_left
    else:
        group_x = 0
    if node.icon == "mention":
        lines.append(
            f'    <text class="mention-icon" x="{_number(group_x + icon_size / 2)}" '
            f'y="{_number(title_y + 3)}" fill="{palette.stroke}">@</text>'
        )
    elif node.icon:
        lines.append(
            f'    <use href="#icon-{escape(node.icon)}" x="{_number(group_x)}" '
            f'y="{_number(icon_y)}" '
            f'width="{icon_size}" height="{icon_size}" color="{palette.stroke}"/>'
        )
    title_x = center_x if stacked or not node.icon else group_x + ink_left + ink_width + gutter
    title_class = "node-title" if stacked or not node.icon else "node-title icon-copy"
    lines.append(
        f'    <text class="{title_class}" x="{_number(title_x)}" '
        f'y="{_number(title_y)}" font-size="{title_size}">'
        f"{escape(node.title)}</text>"
    )
    for index, line in enumerate(subtitle_lines):
        lines.append(
            f'    <text class="node-subtitle" x="{_number(center_x)}" '
            f'y="{_number(subtitle_y + index * SUBTITLE_LINE * scale)}" '
            f'font-size="{subtitle_size}">'
            f"{escape(line)}</text>"
        )
    lines.append("  </g>")
    return "\n".join(lines)


def _draw_dividers(spec: DiagramSpec, boxes: dict[str, Box], width: int) -> list[str]:
    if not spec.dividers:
        return []
    rows = sorted({node.row for node in spec.nodes if node.row is not None})
    bottoms: dict[int, float] = {}
    tops: dict[int, float] = {}
    for node in spec.nodes:
        assert node.row is not None
        box = boxes[node.id]
        # A standalone icon prints its label below the box, so the row ends lower.
        label_room = 32 if node.variant == "icon" and node.show_label else 0
        bottoms[node.row] = max(bottoms.get(node.row, box.bottom), box.bottom + label_room)
        tops[node.row] = min(tops.get(node.row, box.y), box.y)
    left = min(box.x for box in boxes.values())
    right = max(box.right for box in boxes.values())
    padding = min(24.0, left, width - right)
    lines = []
    for divider in spec.dividers:
        below = rows[rows.index(divider.after_row) + 1]
        y = (bottoms[divider.after_row] + tops[below]) / 2
        lines.append(
            f'  <line class="divider" x1="{_number(left - padding)}" y1="{_number(y)}" '
            f'x2="{_number(right + padding)}" y2="{_number(y)}"/>'
        )
    lines.append("")
    return lines


def _draw_icon_node(node: Node, box: Box, palette: Palette) -> str:
    token_width, token_height = _standalone_icon_dimensions(node)
    icon_width = min(token_width, box.width)
    icon_height = min(token_height, box.height)
    icon_x = (box.width - icon_width) / 2
    title_y = box.height + 25
    lines = [
        f'  <g class="node-icon-only node-{escape(node.color)}" '
        f'transform="translate({_number(box.x)} {_number(box.y)})">',
    ]
    if node.icon == "mention":
        lines.append(
            f'    <text class="standalone-mention" x="{_number(box.width / 2)}" '
            f'y="{_number(icon_height * 0.8)}" fill="{palette.stroke}">@</text>'
        )
    else:
        lines.append(
            f'    <use href="#icon-{escape(node.icon or "")}" '
            f'x="{_number(icon_x)}" y="0" width="{_number(icon_width)}" '
            f'height="{_number(icon_height)}" color="{palette.stroke}"/>'
        )
    if node.show_label:
        lines.append(
            f'    <text class="icon-node-title" x="{_number(box.width / 2)}" '
            f'y="{_number(title_y)}">{escape(node.title)}</text>'
        )
    lines.append("  </g>")
    return "\n".join(lines)


def _standalone_icon_dimensions(node: Node) -> tuple[float, float]:
    if node.icon_size is not None:
        return (node.icon_size, node.icon_size)
    return STANDALONE_ICON_DIMENSIONS.get(
        node.icon or "", (DEFAULT_STANDALONE_ICON_SIZE, DEFAULT_STANDALONE_ICON_SIZE)
    )


def _draw_edge(
    spec: DiagramSpec,
    edge: Edge,
    boxes: dict[str, Box],
    width: int,
    height: int,
) -> str:
    if spec.layout.type == "ring":
        route = "ring" if edge.route in {"forward", "ring"} else edge.route
    elif spec.layout.type == "staircase":
        route = "step" if edge.route == "forward" else edge.route
    else:
        # A ring route has no circle to follow outside a ring layout.
        route = "curve" if edge.route == "ring" else edge.route
    if route == "ring":
        path, label_point = _ring_path(spec, edge, boxes, width, height)
    elif route == "step":
        path, label_point = _step_path(edge, boxes)
    elif route == "below":
        path, label_point = _below_path(edge, boxes, width, height)
    else:
        path, label_point = _direct_path(edge, boxes, curved=route == "curve")
    color = EDGE_COLORS[edge.color]
    marker_start = f' marker-start="url(#arrow-start-{edge.color})"' if edge.bidirectional else ""
    line = (
        f'  <path class="edge" d="{path}" stroke="{color}"{marker_start} '
        f'marker-end="url(#arrow-{edge.color})"/>'
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
    ring = _ring_geometry(spec, width, height)
    span = 2 * math.pi / ring.count
    if not _ring_arcs_are_clean(spec, ring, boxes):
        # The circle leaves a card past its corner, so following it would sag
        # behind the cards. Join the facing sides instead, on the ring's radius.
        return _ring_chord_arc(edge, boxes, ring)
    # Each end stops exactly where the circle crosses that card's edge, so every
    # connector meets the cards it joins. Equal arc lengths then come from the
    # card proportions - see the ring section of the skill for the ratio.
    start = _ring_exit(ring, boxes[edge.source], ring.angle(source_index), span)
    end = _ring_exit(ring, boxes[edge.target], ring.angle(source_index) + span, -span)
    radius = _number(ring.radius)
    path = f"M{_point(ring.point(start))}A{radius} {radius} 0 0 1 {_point(ring.point(end))}"
    return path, ring.point((start + end) / 2)


def _ring_arcs_are_clean(spec: DiagramSpec, ring: Ring, boxes: dict[str, Box]) -> bool:
    """True when following the circle never cuts back through a card."""
    span = 2 * math.pi / ring.count
    cards = list(boxes.values())
    for index, node in enumerate(spec.nodes):
        angle = ring.angle(index)
        start = _ring_exit(ring, boxes[node.id], angle, span)
        end = _ring_exit(
            ring, boxes[spec.nodes[(index + 1) % len(spec.nodes)].id], angle + span, -span
        )
        if end <= start:
            return False
        for step in range(RING_ARC_SAMPLES + 1):
            x, y = ring.point(start + (end - start) * step / RING_ARC_SAMPLES)
            if any(c.x < x < c.right and c.y < y < c.bottom for c in cards):
                return False
    return True


def _ring_chord_arc(
    edge: Edge, boxes: dict[str, Box], ring: Ring
) -> tuple[str, tuple[float, float]]:
    """Join two facing card sides on the ring's own radius, not a tighter curve.

    Curvature is what the eye reads as "part of the same circle", so this arc
    keeps the ring's radius even though its centre has to shift inward to reach
    the card edges. A tighter radius would bulge and look like a different shape.
    """
    source, target = boxes[edge.source], boxes[edge.target]
    start_anchor, end_anchor = _default_anchors(source, target)
    start = _anchor(source, edge.source_anchor or start_anchor)
    end = _anchor(target, edge.target_anchor or end_anchor)
    span = math.hypot(end[0] - start[0], end[1] - start[1])
    if span <= 2 * RING_EDGE_GAP or span / 2 >= ring.radius:
        return _line_path(start, end)
    # Hold the same standoff the arcs keep, so every connector clears its card
    # by the same distance.
    inset_x = (end[0] - start[0]) * RING_EDGE_GAP / span
    inset_y = (end[1] - start[1]) * RING_EDGE_GAP / span
    start = (start[0] + inset_x, start[1] + inset_y)
    end = (end[0] - inset_x, end[1] - inset_y)
    radius = _number(ring.radius)
    return (
        f"M{_point(start)}A{radius} {radius} 0 0 1 {_point(end)}",
        ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
    )


def _ring_exit(ring: Ring, box: Box, angle: float, span: float) -> float:
    """The angle at which the circle crosses one card's edge, to sub-pixel accuracy."""

    def clear(offset: float) -> bool:
        x, y = ring.point(angle + offset)
        return (
            x < box.x - RING_EDGE_GAP
            or x > box.right + RING_EDGE_GAP
            or y < box.y - RING_EDGE_GAP
            or y > box.bottom + RING_EDGE_GAP
        )

    if not clear(span):
        # The cards are packed tight enough to swallow the whole arc; keep a stub.
        return angle + span * 0.4
    low, high = 0.0, 1.0
    for _ in range(40):
        mid = (low + high) / 2
        if clear(span * mid):
            high = mid
        else:
            low = mid
    return angle + span * high


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


def _step_path(edge: Edge, boxes: dict[str, Box]) -> tuple[str, tuple[float, float]]:
    """Leave a card through its side, turn once, and drop into the next card's edge.

    The turn sits halfway across the tread - midway between the two cards'
    trailing edges - so every connector in a regular staircase is the same
    elbow, only translated.
    """
    source, target = boxes[edge.source], boxes[edge.target]
    rightward = (
        edge.source_anchor == "right"
        if edge.source_anchor in {"left", "right"}
        else target.center_x >= source.center_x
    )
    downward = (
        edge.target_anchor == "top"
        if edge.target_anchor in {"top", "bottom"}
        else target.center_y >= source.center_y
    )
    start = (source.right if rightward else source.x, source.center_y)
    end_y = target.y if downward else target.bottom
    turn_x = (source.right + target.right) / 2 if rightward else (source.x + target.x) / 2
    run_x = turn_x - start[0] if rightward else start[0] - turn_x
    run_y = end_y - start[1] if downward else start[1] - end_y
    if run_x <= 0 or run_y <= 0 or not target.x <= turn_x <= target.right:
        # The cards do not step apart in both directions, so one turn would
        # double back over a card. A straight join is honest about that.
        return _direct_path(edge, boxes, curved=False)
    radius = min(STEP_CORNER, run_x, run_y)
    corner_x = turn_x - radius if rightward else turn_x + radius
    corner_y = start[1] + radius if downward else start[1] - radius
    path = (
        f"M{_point(start)}H{_number(corner_x)}"
        f"Q{_number(turn_x)} {_number(start[1])} {_number(turn_x)} {_number(corner_y)}"
        f"V{_number(end_y)}"
    )
    return path, (turn_x, (corner_y + end_y) / 2)


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
    if spec.layout.type == "ring":
        ring = _ring_geometry(spec, width, height)
        x, y = ring.center_x, ring.center_y
    else:
        x, y = width / 2, height / 2
    # A fixed type size makes a big annotation look empty and a small one
    # overflow, so the type is sized from the circle and then shrunk until the
    # widest line genuinely fits the chord it sits on.
    title_size = _fitted_size(center, center.radius * CENTER_TITLE_RATIO, TITLE_WEIGHT)
    line = round(title_size * 1.35)
    lines = [
        f'  <circle class="center-annotation" cx="{_number(x)}" cy="{_number(y)}" '
        f'r="{_number(center.radius)}"/>'
    ]
    if center.title:
        title_y = y - line / 2 + title_size / 3 if center.subtitle else y + title_size / 3
        lines.append(
            f'  <text class="center-title" x="{_number(x)}" y="{_number(title_y)}" '
            f'font-size="{title_size}">{escape(center.title)}</text>'
        )
        if center.subtitle:
            lines.append(
                f'  <text class="center-title" x="{_number(x)}" '
                f'y="{_number(title_y + line)}" font-size="{title_size}">'
                f"{escape(center.subtitle)}</text>"
            )
    if center.detail:
        # With a heading above it the detail is a caption on one line. On its own
        # it is the annotation, so it takes the heading's size and wraps to fill
        # the circle rather than running out of it.
        if center.title:
            detail_size = round(title_size * CENTER_DETAIL_RATIO)
            baseline = (title_y + line if center.subtitle else title_y) + detail_size * 1.7
            detail_lines = [center.detail]
        else:
            detail_size, detail_lines = _fitted_detail(center)
            baseline = y - (len(detail_lines) - 1) * detail_size * 1.35 / 2 + detail_size / 3
        step = detail_size * 1.35
        for index, text in enumerate(detail_lines):
            at = baseline + index * step
            room = 2 * _circle_half_width(center.radius, at - y) - 2 * ANNOTATION_PADDING
            if _text_width(text, detail_size, DETAIL_WEIGHT) > room:
                at = y + center.radius + detail_size + 8 + index * step
            lines.append(
                f'  <text class="center-detail" x="{_number(x)}" y="{_number(at)}" '
                f'font-size="{detail_size}">{escape(text)}</text>'
            )
    return "\n".join(lines)


def _fitted_detail(center: CenterAnnotation) -> tuple[int, list[str]]:
    """Largest size at which the detail wraps to lines that all clear the circle."""
    wanted = round(min(center.radius * CENTER_TITLE_RATIO, CENTER_TITLE_MAX))
    for size in range(wanted, CENTER_TITLE_MIN - 1, -1):
        room = 2 * center.radius - 2 * ANNOTATION_PADDING
        wrapped = _wrap_lines(center.detail, room, size, DETAIL_WEIGHT, CENTER_DETAIL_LINES)
        step = size * 1.35
        top = -(len(wrapped) - 1) * step / 2
        if all(
            _text_width(text, size, DETAIL_WEIGHT)
            <= 2 * _circle_half_width(center.radius, top + index * step + size / 2)
            - 2 * ANNOTATION_PADDING
            for index, text in enumerate(wrapped)
        ):
            return size, wrapped
    return CENTER_TITLE_MIN, [center.detail]


def _fitted_size(center: CenterAnnotation, wanted: float, weight: int) -> int:
    """Largest size at or below `wanted` whose longest line clears the circle."""
    longest = max([center.title, center.subtitle] or [""], key=len)
    tracked = weight == TITLE_WEIGHT and bool(center.title)
    if not longest:
        longest = center.detail
    for size in range(round(min(wanted, CENTER_TITLE_MAX)), CENTER_TITLE_MIN - 1, -1):
        letter_spacing = size * CENTER_TRACKING * len(longest) if tracked else 0
        room = 2 * _circle_half_width(center.radius, size) - 2 * ANNOTATION_PADDING
        if _text_width(longest, size, weight) + letter_spacing <= room:
            return size
    return CENTER_TITLE_MIN


def _circle_half_width(radius: float, offset: float) -> float:
    """Half the circle's width at a given vertical offset from its center."""
    return math.sqrt(max(0.0, radius**2 - offset**2))


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
  .node-title { font-size: 20px; font-weight: 750; text-anchor: middle; }
  .node-title.icon-copy { text-anchor: start; }
  .node-subtitle { font-size: 16px; font-weight: 500; fill: #7a8699; text-anchor: middle; }
  .eyebrow { font-size: 13px; font-weight: 750; letter-spacing: 1px; fill: #64748b; text-anchor: middle; }
  .mention-icon { font-size: 27px; font-weight: 750; text-anchor: middle; }
  .standalone-mention { font-size: 52px; font-weight: 750; text-anchor: middle; }
  .icon-node-title { font-size: 16px; font-weight: 750; text-anchor: middle; }
  .edge { fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
  .edge-label rect { stroke-width: 2; }
  .edge-label text { font-size: 14px; font-weight: 750; text-anchor: middle; dominant-baseline: central; }
  .divider { stroke: #cbd5e1; stroke-width: 2; stroke-dasharray: 6 8; stroke-linecap: round; }
  .center-annotation { fill: #f1f5f9; stroke: none; }
  .center-title { font-weight: 800; letter-spacing: 0.08em; fill: #334155; text-anchor: middle; }
  .center-detail { font-weight: 600; fill: #64748b; text-anchor: middle; }
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
