"""Named visual styles for rendered diagrams.

A style bundles every color the renderer can emit: the canvas background,
the text and muted-text fills, one palette per semantic node color, and the
accent colors for edge labels, dividers, boundaries, and center annotations.
Styles exist because a figure that reads well on a white article page can be
unreadable on a near-black app shell, and re-tuning hexes per diagram does
not scale.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    fill: str
    stroke: str


DEFAULT_FONT = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
INTER_FONT = '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
MONO_FONT = "ui-monospace, SFMono-Regular, Menlo, monospace"
JETBRAINS_MONO_FONT = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace'


@dataclass(frozen=True)
class Style:
    """Every themeable color and font in one place."""

    name: str
    canvas_background: str
    font_family: str
    mono_font_family: str
    text: str
    muted: str
    palettes: dict[str, Palette]
    edge_label_fill: str
    boundary_halo: str
    divider: str
    center_fill: str
    center_title: str
    shadow_color: str
    shadow_opacity: float
    specimen_axis: str
    specimen_gridline: str
    specimen_item: str
    specimen_record_fill: str
    specimen_record_border: str

    @property
    def edge_colors(self) -> dict[str, str]:
        return {name: palette.stroke for name, palette in self.palettes.items()}


STYLES: dict[str, Style] = {
    "default": Style(
        name="default",
        canvas_background="#ffffff",
        font_family=DEFAULT_FONT,
        mono_font_family=MONO_FONT,
        text="#172033",
        muted="#475569",
        palettes={
            "purple": Palette("#f5f3ff", "#7c3aed"),
            "blue": Palette("#eff6ff", "#2563eb"),
            "amber": Palette("#fff7ed", "#c2410c"),
            "green": Palette("#ecfdf5", "#15803d"),
            "red": Palette("#fef2f2", "#dc2626"),
            "gray": Palette("#f8fafc", "#64748b"),
        },
        edge_label_fill="#ffffff",
        boundary_halo="#ffffff",
        divider="#cbd5e1",
        center_fill="#f1f5f9",
        center_title="#334155",
        shadow_color="#0f172a",
        shadow_opacity=0.08,
        specimen_axis="#94a3b8",
        specimen_gridline="#cbd5e1",
        specimen_item="#475569",
        specimen_record_fill="#ffffff",
        specimen_record_border="#cbd5e1",
    ),
    # AI Shipping Labs light mode: white canvas on the neutral scale, with the
    # brand lime accent carrying the green (success/persistence) role.
    "asl-light": Style(
        name="asl-light",
        canvas_background="#ffffff",
        font_family=INTER_FONT,
        mono_font_family=JETBRAINS_MONO_FONT,
        text="#171717",
        muted="#525252",
        palettes={
            "purple": Palette("#f5f3ff", "#7c3aed"),
            "blue": Palette("#eff6ff", "#2563eb"),
            "amber": Palette("#fff7ed", "#c2410c"),
            "green": Palette("#f5fbe7", "#648900"),
            "red": Palette("#fef2f2", "#dc2626"),
            "gray": Palette("#f5f5f5", "#737373"),
        },
        edge_label_fill="#ffffff",
        boundary_halo="#ffffff",
        divider="#d4d4d4",
        center_fill="#f5f5f5",
        center_title="#404040",
        shadow_color="#000000",
        shadow_opacity=0.08,
        specimen_axis="#a3a3a3",
        specimen_gridline="#d4d4d4",
        specimen_item="#525252",
        specimen_record_fill="#ffffff",
        specimen_record_border="#d4d4d4",
    ),
    # AI Shipping Labs dark mode: near-black canvas, dark tinted card fills,
    # bright strokes, and the brighter lime accent the site uses at night.
    "asl-dark": Style(
        name="asl-dark",
        canvas_background="#0a0a0a",
        font_family=INTER_FONT,
        mono_font_family=JETBRAINS_MONO_FONT,
        text="#fafafa",
        muted="#a3a3a3",
        palettes={
            "purple": Palette("#2e1065", "#a78bfa"),
            "blue": Palette("#172554", "#60a5fa"),
            "amber": Palette("#431407", "#fb923c"),
            "green": Palette("#1a2e05", "#bfff00"),
            "red": Palette("#450a0a", "#f87171"),
            "gray": Palette("#262626", "#a3a3a3"),
        },
        edge_label_fill="#0a0a0a",
        boundary_halo="#0a0a0a",
        divider="#404040",
        center_fill="#262626",
        center_title="#d4d4d4",
        shadow_color="#000000",
        shadow_opacity=0.45,
        specimen_axis="#737373",
        specimen_gridline="#3f3f3f",
        specimen_item="#a3a3a3",
        specimen_record_fill="#171717",
        specimen_record_border="#404040",
    ),
    "editorial": Style(
        name="editorial",
        canvas_background="#fcfcf8",
        font_family=DEFAULT_FONT,
        mono_font_family=MONO_FONT,
        text="#1c2027",
        muted="#1c2027",
        palettes={
            "purple": Palette("#fcfcf8", "#2455ed"),
            "blue": Palette("#fcfcf8", "#2455ed"),
            "amber": Palette("#fcfcf8", "#ef7134"),
            "green": Palette("#fcfcf8", "#1c2027"),
            "red": Palette("#fcfcf8", "#ef7134"),
            "gray": Palette("#fcfcf8", "#1c2027"),
        },
        edge_label_fill="#fcfcf8",
        boundary_halo="#fcfcf8",
        divider="#1c2027",
        center_fill="#fcfcf8",
        center_title="#1c2027",
        shadow_color="#1c2027",
        shadow_opacity=0.04,
        specimen_axis="#1c2027",
        specimen_gridline="#1c2027",
        specimen_item="#1c2027",
        specimen_record_fill="#fcfcf8",
        specimen_record_border="#1c2027",
    ),
}

DEFAULT_STYLE_NAME = "default"


def resolve_style(name: str | None) -> Style:
    """Return the named style, falling back to the default look."""
    key = name or DEFAULT_STYLE_NAME
    if key not in STYLES:
        raise ValueError(f"unknown style '{key}'; available: {', '.join(sorted(STYLES))}")
    return STYLES[key]
