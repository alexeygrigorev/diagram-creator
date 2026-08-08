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
the same card component. The ring layout places card centers on a circle, one
slot every `360 / count` degrees, clockwise from the top. The radius is the
largest one whose cards still clear the canvas margin, found by bisection, and
the resulting bounding box is centered in the canvas. A second bisection finds
the smallest radius that keeps the cards apart; when the canvas cannot reach it,
rendering fails with the canvas size that would.

The staircase layout advances one equal tread right and one equal riser down
per node, then centers the whole cascade. The riser is the card height plus a
fixed gap, so consecutive steps never share a row. The tread is whatever spreads
the cascade over the canvas width, clamped so that cards neither pull apart nor
overlap past 40 percent of their width; when the clamp no longer fits, rendering
fails with the canvas size that would. An ascending staircase reverses the slot
order, not the reading order, so the first node still sits on the left.

Each resolved card is a box with `x`, `y`, `width`, and `height`. Connectors use
named anchors on those boxes. Cubic curves add two control points. Ring routes
are arcs of the layout circle itself: the router walks the arc away from each
card until it clears that card's box, then joins the two points with a single
SVG `A` command, so every connector shares one curvature. Where the circle only
grazes a corner - two cards straddling the bottom of a five-node ring, for
instance - following it would sag underneath them, so that pair joins its facing
sides on a tighter arc that rises off its chord by the same proportion a full
ring slot does. Every connector still reads as part of one loop.

A ring is rejected when its connectors would come out visibly different lengths.
A card presents a different angular width at each slot unless it is close to
square, so a wide flat card makes the arc between the bottom pair far shorter
than the arc over the top - the most visible way a loop stops reading as one
circle. The error names the card height that evens them out, found by trying
heights and keeping the one with the smallest spread.

A step route is one elbow: out of a card's side, along to the point halfway
between the two cards' trailing edges, then a rounded turn into the next card's
top or bottom edge. Placing the turn by the two boxes rather than by the layout
keeps every connector in a regular staircase identical, and lets the same route
join two offset cards in a grid or manual layout. When the cards do not step
apart in both directions, one turn would double back over a card, so the router
falls back to a straight join.

Type is never distorted to fit. Each diagram resolves one title size and one
subtitle size - the largest at or below the requested size that leaves every
card's copy at its natural width - so titles stay consistent across cards
instead of one being squeezed while its neighbour is not. Deciding that needs a
text width before any browser has laid the text out, so the renderer carries a
table of advance widths per 1 px of font size, measured out of Chromium by
`scripts/measure_text.py`. Widths scale linearly with font size, so one table
per weight covers every size the cards use. A weight with no table of its own
measures against the next heavier one, so an estimate is never short.

An icon-and-title group is centered on ink, not on boxes. Icon artwork does not
fill its slot evenly - ink runs from 58 percent of the box to 100 percent across
this library - so `ICON_INK`, measured by `scripts/measure_icons.py`, records
each glyph's bounds and the group is centered on what is actually visible.

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
uv run diagram-creator examples/interview-stages.json examples/interview-stages.svg
uv run diagram-creator examples/faq-curation-loop.json examples/faq-curation-loop.svg
uv run diagram-creator examples/faq-curation-loop.json examples/faq-curation-loop.png
```

The SVG and PNG versions of the FAQ loop have the same intrinsic dimensions and
the PNG is a browser rendering of the generated SVG.
