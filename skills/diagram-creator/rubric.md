# Diagram scoring rubric

Score a rendered diagram out of 10 before shipping it. Every criterion below
came out of a real review round, and each one is checkable - measure it against
the SVG or the rendered PNG rather than eyeballing and hoping.

A diagram is not done because it renders. It is done when every criterion
passes and a designer pass finds nothing structural left.

## How to score

Ten criteria, one point each. Anything you cannot verify scores zero, not the
benefit of the doubt. Report the score with the failing criteria named.

Useful measurements, all cheap:

- Card centers: parse `transform="translate(x y)"` out of the SVG and add half
  the card size.
- Ring center and radius: evenly spaced points on a circle average out to the
  center, so the mean of the card centers is the center; distances to it are
  the radii.
- Ink extents: render the PNG and scan for pixels below a luminance threshold
  inside a known region. This is how you check what the eye actually sees
  rather than what the coordinates claim.
- Text width: `diagram_creator.renderer._text_width(text, size, weight)`.

## The criteria

### 1. Shape is true

A ring is a circle, not an ellipse. All card centers sit the same distance from
the ring center, and neighbors are `360 / count` degrees apart.

Check: radius spread under 0.5 px, every angular step within 0.5 degrees.
Fails when: the layout derives positions from canvas fractions, so a wide
canvas flattens the circle.

### 2. Connectors share one curvature

Every connector in a loop reads as part of the same circle. Curvature is what
the eye compares, so a connector on a tighter radius reads as a different
shape even when its endpoints are right.

Check: all arc radii in the SVG match the ring radius.
Fails when: one connector falls back to a straight line or a tighter bow.

### 3. Connectors attach cleanly

A connector leaves a card beside one of its sides, never past a corner, and
never sags behind or underneath a card.

Check: each endpoint is within the card's vertical span or its horizontal span.
Compute the arc's deepest point and confirm it stays inside the cards.

### 4. Nodes are clearly separated

Adjacent cards read as separate objects. Two cards side by side at the bottom
of a ring are the tightest pair and set the standard.

Check: smallest edge-to-edge clearance of any adjacent pair. Aim for at least
60% of a card height; under 50% starts to read as crowding. For a five-node
ring the bottom gap is `1.176 * radius - card_width`.

### 5. Cards fill their own width

Content is centered in the card, so no side is left visibly empty. A
left-aligned title in a wide card wastes half its row.

Check: for each card, the widest empty margin beside the content. More than
about a quarter of the card width means the content is not carrying it.

### 6. One text axis per card

Title and subtitle share a single alignment. An icon plus a left-aligned title
above a centered subtitle gives a card two competing axes and three ragged
edges.

Check: the icon-and-title group's midpoint equals the card's center, and the
subtitle's anchor is the same center.

### 7. Content is optically centered

The whole content block - icon top through subtitle descender - sits on the
card's vertical center. Centering only the icon row and hanging the subtitle
below it pushes everything low.

Check: ink extents of the card interior; the midpoint should be within about
2 px of half the card height.

### 8. Text is neither squeezed nor overflowing

Nothing is compressed with `textLength` unless it genuinely does not fit, and
nothing spills past its column.

Check: count `textLength` in the SVG. Every occurrence needs a reason.

### 9. Annotation earns its space

A center annotation sits on the true ring center, its label fits inside it with
real clearance, and any caption clears the circle instead of cutting through it.

Check: annotation `cx`/`cy` equal the computed ring center; `_text_width` of the
title plus about 16 px of breathing room fits inside the circle at the title's
baseline; the caption baseline is below `cy + r`.

### 10. Canvas is filled

The figure uses its canvas. Margins are symmetric on both axes and there is no
dead band or empty column.

Check: bounding box of all cards against the canvas; opposite margins should
match. For a ring, remember the circle only grows until its cards hit the
margin, so a wide canvas buys side whitespace, not a wider loop. Give rings a
roughly square canvas.

## Beyond the checklist

The ten criteria catch structure and geometry. They do not catch whether the
diagram is well designed - colour doing work versus colour as noise, hierarchy,
whether the annotation should exist at all, whether five hues help or scatter
the eye.

For that, run the designer review in `agents/designer.md` and treat its
structural findings as additional criteria for that specific diagram.

## Worked example

A five-node loop scored across one session:

- 3/10 at the start: ellipse not circle (1), squashed rhythm, dead band across
  the top (10), mixed text axes (6), content sitting low (7).
- 6/10 after the geometry was fixed: true circle, even margins, annotation
  centered - but one connector on a different radius (2), bottom cards 115 px
  apart (4), and 109-148 px of empty space beside every title (5).
- 10/10 once connectors shared the ring radius, the canvas grew to open the
  bottom gap to 179 px, and card content was centered using measured text
  widths.
