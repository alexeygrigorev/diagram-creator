from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from diagram_creator.spec import DiagramSpec, Edge, Node, SpecError


@dataclass(frozen=True)
class Palette:
    fill: str
    stroke: str
    title: str
    subtitle: str


PALETTES = {
    "purple": Palette("#f3e8ff", "#a855f7", "#3b0764", "#7e22ce"),
    "blue": Palette("#e0f2fe", "#0ea5e9", "#0c4a6e", "#0369a1"),
    "amber": Palette("#fef3c7", "#f59e0b", "#78350f", "#b45309"),
    "green": Palette("#dcfce7", "#22c55e", "#14532d", "#15803d"),
    "red": Palette("#ffe4e6", "#f43f5e", "#881337", "#be123c"),
    "gray": Palette("#f1f5f9", "#94a3b8", "#1e293b", "#475569"),
}

EDGE_COLORS = {
    "gray": "#64748b",
    "green": "#16a34a",
    "red": "#dc2626",
    "blue": "#0284c7",
    "purple": "#9333ea",
    "amber": "#d97706",
}


def render_diagram(
    spec: DiagramSpec,
    output: str | Path,
    *,
    width: int = 1440,
    height: int = 360,
) -> Path:
    if width < 600:
        raise SpecError("width must be at least 600 pixels")
    if height < 280:
        raise SpecError("height must be at least 280 pixels")

    image = Image.new("RGB", (width, height), spec.background)
    draw = ImageDraw.Draw(image)
    layout = _layout(spec, width, height)

    for edge in spec.edges:
        _draw_edge(draw, edge, layout, width, height)
    for node in spec.nodes:
        _draw_node(draw, node, layout[node.id], width)

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)
    return destination


def _layout(
    spec: DiagramSpec,
    width: int,
    height: int,
) -> dict[str, tuple[float, float, float, float]]:
    count = len(spec.nodes)
    side_padding = width * 0.035
    minimum_gap = width * 0.06
    card_width = min(
        width * 0.18,
        (width - 2 * side_padding - minimum_gap * (count - 1)) / count,
    )
    if card_width < 120:
        raise SpecError("the canvas is too narrow for the number of nodes")

    gap = (width - 2 * side_padding - card_width * count) / (count - 1)
    card_height = min(104.0, height * 0.31)
    card_y = height * 0.195

    boxes: dict[str, tuple[float, float, float, float]] = {}
    for index, node in enumerate(spec.nodes):
        x = side_padding + index * (card_width + gap)
        boxes[node.id] = (x, card_y, x + card_width, card_y + card_height)
    return boxes


def _draw_node(
    draw: ImageDraw.ImageDraw,
    node: Node,
    box: tuple[float, float, float, float],
    width: int,
) -> None:
    palette = PALETTES.get(node.color)
    if palette is None:
        raise SpecError(f"unknown node color: {node.color}")

    x1, y1, x2, y2 = box
    radius = max(12, int(width / 80))
    shadow_offset = max(4, int(width / 240))
    draw.rounded_rectangle(
        (x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
        radius=radius,
        fill="#dbe3ee",
    )
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=palette.fill,
        outline=palette.stroke,
        width=max(2, width // 720),
    )

    title_font = _font(max(18, width // 58), bold=True)
    subtitle_font = _font(max(14, width // 80))
    center_x = (x1 + x2) / 2
    if node.subtitle:
        _center_text(draw, (center_x, y1 + (y2 - y1) * 0.38), node.title, title_font, palette.title)
        _center_text(
            draw,
            (center_x, y1 + (y2 - y1) * 0.68),
            node.subtitle,
            subtitle_font,
            palette.subtitle,
        )
    else:
        _center_text(draw, (center_x, (y1 + y2) / 2), node.title, title_font, palette.title)


def _draw_edge(
    draw: ImageDraw.ImageDraw,
    edge: Edge,
    boxes: dict[str, tuple[float, float, float, float]],
    width: int,
    height: int,
) -> None:
    color = EDGE_COLORS.get(edge.color)
    if color is None:
        raise SpecError(f"unknown edge color: {edge.color}")
    line_width = max(3, width // 360)
    source = boxes[edge.source]
    target = boxes[edge.target]

    if edge.route == "forward":
        y = (source[1] + source[3]) / 2
        start = (source[2] + width * 0.009, y)
        end = (target[0] - width * 0.009, y)
        draw.line((start, end), fill=color, width=line_width)
        _arrowhead(draw, end, "right", color, width)
        if edge.label:
            _draw_label(draw, edge.label, ((start[0] + end[0]) / 2, y - 28), color, width)
        return

    source_x = (source[0] + source[2]) / 2
    target_x = (target[0] + target[2]) / 2
    start_y = source[3] + height * 0.035
    end_y = target[3] + height * 0.045
    loop_y = height * 0.77
    draw.line(
        ((source_x, start_y), (source_x, loop_y), (target_x, loop_y), (target_x, end_y)),
        fill=color,
        width=line_width,
        joint="curve",
    )
    _arrowhead(draw, (target_x, end_y), "up", color, width)
    if edge.label:
        _draw_label(draw, edge.label, ((source_x + target_x) / 2, loop_y), color, width)


def _arrowhead(
    draw: ImageDraw.ImageDraw,
    point: tuple[float, float],
    direction: str,
    color: str,
    width: int,
) -> None:
    x, y = point
    size = max(11, width // 90)
    if direction == "right":
        points = [(x, y), (x - size, y - size * 0.65), (x - size, y + size * 0.65)]
    else:
        points = [
            (x, y - size * 0.25),
            (x - size * 0.65, y + size),
            (x + size * 0.65, y + size),
        ]
    draw.polygon(points, fill=color)


def _draw_label(
    draw: ImageDraw.ImageDraw,
    label: str,
    center: tuple[float, float],
    color: str,
    width: int,
) -> None:
    font = _font(max(14, width // 65), bold=True)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    padding_x = width * 0.015
    padding_y = width * 0.006
    x, y = center
    pill = (
        x - text_width / 2 - padding_x,
        y - text_height / 2 - padding_y,
        x + text_width / 2 + padding_x,
        y + text_height / 2 + padding_y,
    )
    draw.rounded_rectangle(
        pill,
        radius=int((pill[3] - pill[1]) / 2),
        fill="#fff1f2",
        outline=color,
        width=max(2, width // 720),
    )
    _center_text(draw, center, label, font, color)


def _center_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = center[0] - (bbox[2] - bbox[0]) / 2
    y = center[1] - (bbox[3] - bbox[1]) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size=size)
    except OSError:
        return ImageFont.load_default(size=size)
