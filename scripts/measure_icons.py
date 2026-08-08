"""Measure where each icon's ink sits inside its box and print ICON_INK.

Icons are drawn into a fixed square slot, but their artwork does not fill that
slot evenly - a portrait glyph like `document` leaves far more empty space than
a full-bleed one like `browser`. Centring an icon-and-label group on the icon's
box therefore looks off-centre, because the eye centres on ink.

This renders every icon large on white, finds its ink bounds, and expresses them
as fractions of the box so the renderer can centre on what is actually visible.
Re-run it and paste the output into diagram_creator/renderer.py whenever the
icon library changes.

    uv run python scripts/measure_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from diagram_creator.renderer import render_diagram
from diagram_creator.spec import ICONS, DiagramSpec

BOX = 120
CELL = 160
COLUMNS = 8
THRESHOLD = 150


def main() -> None:
    names = sorted(icon for icon in ICONS if icon != "mention")
    rows = (len(names) + COLUMNS - 1) // COLUMNS
    width, height = 80 + CELL * COLUMNS, 80 + CELL * rows
    spec = DiagramSpec.from_dict(
        {
            "canvas": {"width": max(width, 600), "height": max(height, 280)},
            "layout": {"type": "manual", "card_width": BOX, "card_height": BOX},
            "nodes": [
                {
                    "id": name,
                    "title": ".",
                    "icon": name,
                    "variant": "icon",
                    "show_label": False,
                    "icon_size": BOX,
                    "x": 40 + CELL * (index % COLUMNS),
                    "y": 40 + CELL * (index // COLUMNS),
                    "width": BOX,
                    "height": BOX,
                }
                for index, name in enumerate(names)
            ],
            "edges": [],
        }
    )
    output = Path("icons-measure.png")
    render_diagram(spec, output)
    image = Image.open(output).convert("L")
    pixels = image.load()

    print("ICON_INK = {")
    for index, name in enumerate(names):
        left = 40 + CELL * (index % COLUMNS)
        top = 40 + CELL * (index // COLUMNS)
        columns = [
            x
            for x in range(left, left + BOX)
            if any(pixels[x, y] < THRESHOLD for y in range(top, top + BOX))
        ]
        if not columns:
            continue
        start = (min(columns) - left) / BOX
        end = (max(columns) + 1 - left) / BOX
        print(f'    "{name}": ({start:.3f}, {end:.3f}),')
    print("}")
    output.unlink()


if __name__ == "__main__":
    main()
