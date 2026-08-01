#!/usr/bin/env python3
"""Render local SVG images referenced by Markdown and publish PNG references."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


HTML_IMAGE = re.compile(
    r"(?P<prefix><img\b[^>]*?\bsrc\s*=\s*['\"])(?P<ref>[^'\"]+?\.svg)"
    r"(?P<suffix>[?#][^'\"]*)?(?P<quote>['\"])",
    re.IGNORECASE,
)
MARKDOWN_IMAGE = re.compile(
    r"(?P<prefix>!\[[^\]]*\]\()(?P<open><)?(?P<ref>[^\s)>]+?\.svg)"
    r"(?P<close>>)?(?P<suffix>[?#][^\s)>]*)?",
    re.IGNORECASE,
)
HTML_PUBLISHED_IMAGE = re.compile(
    r"(?P<prefix><img\b[^>]*?\bsrc\s*=\s*['\"])(?P<ref>[^'\"]+?\.png)"
    r"(?P<suffix>[?#][^'\"]*)?(?P<quote>['\"])",
    re.IGNORECASE,
)
MARKDOWN_PUBLISHED_IMAGE = re.compile(
    r"(?P<prefix>!\[[^\]]*\]\()(?P<open><)?(?P<ref>[^\s)>]+?\.png)"
    r"(?P<close>>)?(?P<suffix>[?#][^\s)>]*)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImageReference:
    source: Path
    destination: Path


def _local_svg(document: Path, reference: str) -> ImageReference | None:
    parsed = urlsplit(reference)
    published = Path(unquote(parsed.path)).suffix.lower() == ".png"
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        if published:
            return None
        raise ValueError(f"external SVG references are not supported: {reference}")

    relative = Path(unquote(parsed.path))
    if relative.is_absolute():
        if published:
            return None
        raise ValueError(f"root-relative SVG references are not supported: {reference}")

    referenced = (document.parent / relative).resolve()
    source = referenced.with_suffix(".svg") if published else referenced
    if published and not source.is_file():
        return None
    if source.suffix.lower() != ".svg" or not source.is_file():
        raise FileNotFoundError(f"SVG reference does not exist: {reference} ({source})")
    return ImageReference(source=source, destination=source.with_suffix(".png"))


def _references(document: Path, text: str) -> dict[Path, ImageReference]:
    found: dict[Path, ImageReference] = {}
    for pattern in (
        HTML_IMAGE,
        MARKDOWN_IMAGE,
        HTML_PUBLISHED_IMAGE,
        MARKDOWN_PUBLISHED_IMAGE,
    ):
        for match in pattern.finditer(text):
            image = _local_svg(document, match.group("ref"))
            if image is None:
                continue
            found[image.source] = image
    return found


def _replace_references(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        groups = match.groupdict()
        updated = str(Path(groups["ref"]).with_suffix(".png"))
        if "quote" in groups:
            return groups["prefix"] + updated + (groups.get("suffix") or "") + groups["quote"]
        return (
            groups["prefix"]
            + (groups.get("open") or "")
            + updated
            + (groups.get("close") or "")
            + (groups.get("suffix") or "")
        )

    text = HTML_IMAGE.sub(replace, text)
    return MARKDOWN_IMAGE.sub(replace, text)


def _svg_size(source: Path) -> tuple[int, int]:
    root = ET.parse(source).getroot()

    def pixels(value: str | None) -> float | None:
        if value is None:
            return None
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*", value)
        return float(match.group(1)) if match else None

    width = pixels(root.get("width"))
    height = pixels(root.get("height"))
    if width is None or height is None:
        view_box = root.get("viewBox", "").replace(",", " ").split()
        if len(view_box) == 4:
            width = width or float(view_box[2])
            height = height or float(view_box[3])
    if width is None or height is None or width <= 0 or height <= 0:
        raise ValueError(f"SVG needs numeric width/height or a viewBox: {source}")
    return round(width), round(height)


def _chromium() -> str:
    for executable in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        resolved = shutil.which(executable)
        if resolved:
            return resolved
    raise RuntimeError("Chromium is required to publish browser-matched PNGs")


def _background_flag(background: str | None) -> str:
    if background is None:
        return "00000000"
    colors = {"white": "FFFFFFFF", "black": "000000FF"}
    normalized = colors.get(background.lower(), background.removeprefix("#"))
    if re.fullmatch(r"[0-9a-fA-F]{6}", normalized):
        return normalized.upper() + "FF"
    if re.fullmatch(r"[0-9a-fA-F]{8}", normalized):
        return normalized.upper()
    raise ValueError("background must be white, black, transparent, #RRGGBB, or #RRGGBBAA")


def _render_svg(
    browser: str,
    source: Path,
    destination: Path,
    *,
    scale: float,
    background: str | None,
) -> None:
    width, height = _svg_size(source)
    command = [
        browser,
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--force-device-scale-factor={scale}",
        f"--default-background-color={_background_flag(background)}",
        f"--window-size={width},{height}",
        f"--screenshot={destination.resolve()}",
        source.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not destination.is_file():
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Chromium failed to render {source}: {details}")


def publish(documents: list[Path], *, scale: float, background: str | None) -> tuple[int, int]:
    contents = {document: document.read_text() for document in documents}
    images: dict[Path, ImageReference] = {}
    for document, text in contents.items():
        images.update(_references(document, text))

    browser = _chromium()
    with tempfile.TemporaryDirectory(
        prefix=".diagram-publish-", dir=documents[0].parent
    ) as temporary:
        staging = Path(temporary)
        rendered: dict[Path, Path] = {}
        for index, image in enumerate(images.values()):
            staged = staging / f"{index}.png"
            _render_svg(
                browser,
                image.source,
                staged,
                scale=scale,
                background=background,
            )
            rendered[image.destination] = staged

        for destination, staged in rendered.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary_output = destination.with_name(f".{destination.name}.tmp")
            shutil.copyfile(staged, temporary_output)
            os.replace(temporary_output, destination)

    changed = 0
    for document, text in contents.items():
        updated = _replace_references(text)
        if updated != text:
            document.write_text(updated)
            changed += 1
    return len(images), changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render locally referenced SVG images and replace their Markdown references with PNG."
    )
    parser.add_argument("documents", nargs="+", type=Path, help="Markdown files to publish")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="PNG scale relative to the SVG's intrinsic size (default: 1.0)",
    )
    parser.add_argument(
        "--background",
        default="white",
        help="PNG background color, or 'transparent' (default: white)",
    )
    args = parser.parse_args()
    if args.scale <= 0:
        parser.error("--scale must be greater than zero")

    documents = [document.resolve() for document in args.documents]
    for document in documents:
        if not document.is_file():
            parser.error(f"Markdown file does not exist: {document}")

    background = None if args.background.lower() == "transparent" else args.background
    image_count, document_count = publish(
        documents,
        scale=args.scale,
        background=background,
    )
    print(f"Rendered {image_count} SVG image(s); updated {document_count} Markdown file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
