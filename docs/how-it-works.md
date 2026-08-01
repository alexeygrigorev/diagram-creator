# Renderer design

The JSON is the source of truth. Rendering has three deterministic stages:

1. Validate labels, colors, icons, coordinates, edge references, and routes.
2. Resolve the selected layout into card boxes and SVG paths.
3. Write SVG directly, or ask headless Chromium to capture that SVG as PNG.

Using one SVG drawing path avoids the font, filter, and icon differences that
occurred when SVG and PNG had independent renderers.

## Layout model

The horizontal layout calculates equal card widths and gutters from the canvas.
The manual layout uses explicit node origins but still draws every node through
the same card component. The five-node ring uses a fixed clockwise slot system:
top, upper right, lower right, lower left, and upper left. Opposite curves are
derived as geometric mirrors, and the closing edge lands at the midpoint of the
top card's left side.

Each resolved card is a box with `x`, `y`, `width`, and `height`. Connectors use
named anchors on those boxes. Cubic curves add two control points; ring routes
calculate those points from the symmetric slot geometry.

## Drawing order

The SVG contains:

1. Accessible title and description elements.
2. One shadow, arrow markers, needed icon symbols, and shared CSS definitions.
3. A solid canvas background.
4. Edges and optional labels.
5. An optional quiet center annotation.
6. Cards, icons, titles, and subtitles.

Edges are emitted before cards, so joins terminate cleanly beneath card fills.
Each semantic color has a light fill and saturated border/icon. All ordinary
connectors use the same neutral gray unless the JSON assigns another semantic
color.

## Reproduce the examples

```bash
uv run diagram-creator examples/agent-workflow.json examples/agent-workflow.svg
uv run diagram-creator examples/faq-curation-loop.json examples/faq-curation-loop.svg
uv run diagram-creator examples/faq-curation-loop.json examples/faq-curation-loop.png
```

The SVG and PNG versions of the FAQ loop have the same intrinsic dimensions and
the PNG is a browser rendering of the generated SVG.
