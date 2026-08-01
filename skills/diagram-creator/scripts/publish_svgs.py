#!/usr/bin/env python3
"""Render local SVG images referenced by Markdown and publish PNG references."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

import cairosvg


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


@dataclass(frozen=True)
class ImageReference:
    source: Path
    destination: Path


def _local_svg(document: Path, reference: str) -> ImageReference:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        raise ValueError(f"external SVG references are not supported: {reference}")

    relative = Path(unquote(parsed.path))
    if relative.is_absolute():
        raise ValueError(f"root-relative SVG references are not supported: {reference}")

    source = (document.parent / relative).resolve()
    if source.suffix.lower() != ".svg" or not source.is_file():
        raise FileNotFoundError(f"SVG reference does not exist: {reference} ({source})")
    return ImageReference(source=source, destination=source.with_suffix(".png"))


def _references(document: Path, text: str) -> dict[Path, ImageReference]:
    found: dict[Path, ImageReference] = {}
    for pattern in (HTML_IMAGE, MARKDOWN_IMAGE):
        for match in pattern.finditer(text):
            image = _local_svg(document, match.group("ref"))
            found[image.source] = image
    return found


def _replace_references(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        groups = match.groupdict()
        updated = str(Path(groups["ref"]).with_suffix(".png"))
        if "quote" in groups:
            return (
                groups["prefix"]
                + updated
                + (groups.get("suffix") or "")
                + groups["quote"]
            )
        return (
            groups["prefix"]
            + (groups.get("open") or "")
            + updated
            + (groups.get("close") or "")
            + (groups.get("suffix") or "")
        )

    text = HTML_IMAGE.sub(replace, text)
    return MARKDOWN_IMAGE.sub(replace, text)


def publish(documents: list[Path], *, scale: float, background: str | None) -> tuple[int, int]:
    contents = {document: document.read_text() for document in documents}
    images: dict[Path, ImageReference] = {}
    for document, text in contents.items():
        images.update(_references(document, text))

    with tempfile.TemporaryDirectory(prefix="diagram-publish-") as temporary:
        staging = Path(temporary)
        rendered: dict[Path, Path] = {}
        for index, image in enumerate(images.values()):
            staged = staging / f"{index}.png"
            cairosvg.svg2png(
                url=str(image.source),
                write_to=str(staged),
                scale=scale,
                background_color=background,
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
