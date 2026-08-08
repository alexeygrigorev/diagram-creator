"""Measure advance widths for the card font stack and print CHARACTER_EM.

The renderer has to decide whether a title or subtitle overflows its column
before a browser ever lays the text out, so it needs a width table. This script
produces one by rendering runs of each glyph in Chromium and diffing the ink of
a 20-copy run against a 30-copy run, which cancels out the side bearings and
leaves the advance width.

Widths scale linearly with font size to within 0.1 px, so one table per weight
covers every size the cards use. Re-run this and paste the output into
diagram_creator/renderer.py whenever the card typography changes.

    uv run python scripts/measure_text.py
"""

from __future__ import annotations

import shutil
import string
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

CHARACTERS = string.ascii_letters + string.digits + " ,.:;/-+()'&?!→_@#%"
FONT_STACK = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
STYLES = ((14, 500), (16, 750))
CANVAS_WIDTH = 1400


def _browser() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if resolved := shutil.which(name):
            return resolved
    raise SystemExit("Chromium is required to measure text")


def _rows(size: int, weight: int) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for character in CHARACTERS:
        if character == " ":
            # A run of spaces leaves no ink, so anchor each gap between two 'a's.
            rows += [("a" * 21, 20), ("a " * 20 + "a", 20)]
        else:
            rows += [(character * 20, 10), (character * 30, 10)]
    return rows


def _measure(size: int, weight: int) -> dict[str, float]:
    rows = _rows(size, weight)
    step = int(size * 2) + 10
    height = 60 + step * len(rows)
    body = "\n".join(
        f'<text x="20" y="{30 + step * index}" style="font-size:{size}px;font-weight:{weight}">'
        f"{text.replace('&', '&amp;').replace('<', '&lt;')}</text>"
        for index, (text, _) in enumerate(rows)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{height}">'
        f"<style>text {{ font-family: {FONT_STACK}; fill: #000 }}</style>"
        f'<rect width="100%" height="100%" fill="#fff"/>{body}</svg>'
    )
    with tempfile.TemporaryDirectory(prefix=".measure-", dir=Path.cwd()) as raw:
        source, output = Path(raw) / "text.svg", Path(raw) / "text.png"
        source.write_text(svg)
        subprocess.run(
            [
                _browser(),
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--hide-scrollbars",
                "--run-all-compositor-stages-before-draw",
                "--default-background-color=FFFFFFFF",
                f"--window-size={CANVAS_WIDTH},{height}",
                f"--screenshot={output.resolve()}",
                source.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
        )
        image = Image.open(output).convert("L")
        pixels = image.load()
        widths = []
        for index in range(len(rows)):
            top = max(0, 30 + step * index - int(size * 1.2))
            bottom = 30 + step * index + int(size * 0.4)
            columns = [
                x
                for x in range(image.size[0])
                if any(pixels[x, y] < 150 for y in range(top, bottom))
            ]
            widths.append(max(columns) - min(columns) + 1 if columns else 0)
    return {
        character: (widths[2 * i + 1] - widths[2 * i]) / rows[2 * i][1] / size
        for i, character in enumerate(CHARACTERS)
    }


def main() -> None:
    print("CHARACTER_EM = {")
    for size, weight in STYLES:
        table = _measure(size, weight)
        print(f"    {weight}: {{")
        line = "        "
        for character in sorted(table):
            piece = f"{character!r}: {round(table[character], 4)}, "
            if len(line) + len(piece) > 100:
                print(line.rstrip())
                line = "        "
            line += piece
        print(line.rstrip())
        print("    },")
    print("}")


if __name__ == "__main__":
    main()
