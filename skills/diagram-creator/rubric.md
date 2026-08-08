# Diagram scoring rubric

Score a rendered diagram out of 10 before shipping it. Every criterion below
came out of a real review round, and each one is checkable - measure it against
the SVG or the rendered PNG rather than eyeballing and hoping.

A diagram is not done because it renders. It is done when every criterion
passes and a designer pass finds nothing structural left.

## How to score

Twelve criteria, scored out of 12 and reported as a fraction. Anything you
cannot verify scores zero, not the benefit of the doubt. Report the score with
the failing criteria named.

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
- Icon ink: `diagram_creator.renderer.ICON_INK` gives where each glyph's ink
  starts and ends inside its box, as a fraction of the box.

One trap when measuring ink from a PNG: connector arrowheads land on a card's
outline, so a window that samples inside the card can catch them and shift the
apparent centre by 10 px. Compute the content's extent from the SVG numbers and
use the PNG only to confirm.

## The criteria

### 1. Shape is true

A ring is a circle, not an ellipse. All card centers sit the same distance from
the ring center, and neighbors are `360 / count` degrees apart.

Check: radius spread under 0.5 px, every angular step within 0.5 degrees.
Fails when: the layout derives positions from canvas fractions, so a wide
canvas flattens the circle.

A staircase is a cascade, not a scatter. Every tread advances the same distance
right and every riser the same distance down, and no two steps share a row.

Check: the spread of consecutive `x` advances and of consecutive `y` advances,
both under 0.5 px; every riser at least the card height.

### 2. Connectors are one arc repeated

Every connector in a loop is the same arc of the same circle, only rotated -
identical radius and identical length. Curvature and length are both things the
eye compares, so a connector that is shorter, or on a tighter radius, reads as a
different shape even when its endpoints are right.

The renderer enforces this: a ring whose connectors differ in length by more
than 10 percent is rejected, with the card height that would even them out.

Check: chord length and arc radius of every connector. Radius spread under
0.5 px always; chord spread under 10 percent, or it will not render.

Equal chords and touching cards pull against each other. Forcing one shared
angular standoff makes the chords identical but then only the card needing the
widest standoff is actually touched. Touching every card is the one to keep, and
chord equality then depends on the card shape: a card presents a different
angular width at each slot unless it is close to square. It converges near
h = 0.95w, but that ratio also brings adjacent cards almost together, so aim for
square-ish rather than exact.

The same applies to a staircase, where every connector should be one elbow
translated: identical horizontal run, identical vertical run, identical corner
radius.

### 3. Connectors touch the cards they join

A connector meets the card at each end. A connector that stops short reads as
broken, and the gap is more visible than any amount of curvature polish.

Check: each endpoint sits on a card's outline, within about a pixel. Bisect for
the crossing rather than sampling it - stepping along the arc leaves the
endpoint off by the step size, which is a visible pixel or two at ring scale.

### 4. Nodes are clearly separated

Adjacent cards read as separate objects. Two cards side by side at the bottom
of a ring are the tightest pair and set the standard.

Check: edge-to-edge clearance of EVERY adjacent pair, then the ratio of the
widest to the tightest. Checking only one pair hides the problem - a five-node
ring can look wrong because its side pairs are 1.76x its top pairs while every
individual gap looks reasonable. Aim for a spread under 1.2x.

Rectangles on a ring can never have exactly equal gaps: a pair side by side is
separated along one axis, a diagonal pair corner to corner, so the three cases
differ by construction. The spread shrinks as the cards get small relative to
the radius, and squarer cards help. Under about 1.15x it stops reading as
uneven. Wrapping subtitles is what lets a card be narrow enough to get there.

### 5. Cards are filled, not just centered

Both directions. Content is centered so no side is left visibly empty, and the
content actually occupies the card rather than floating in the middle of it.

Vertical emptiness is the one that slips through, because centering makes a
near-empty card look deliberate. It shows up when something else forces the card
size - a ring needs square cards for equal connectors (2), so a card holding one
short row ends up a third full and reads as a box with a label lost inside it.

Check: content height over card height, at least 50 percent. And for each card,
the widest empty margin beside the content - more than about a quarter of the
card width means the content is not carrying it.

The fix is usually to make the content taller rather than the card shorter, since
the card size is often fixed by the layout: `icon_position: "block"` stacks the
icon over the title and roughly doubles the content height of a one-line card.

### 6. One text axis per card

Title and subtitle share a single alignment. An icon plus a left-aligned title
above a centered subtitle gives a card two competing axes and three ragged
edges.

Check: the icon-and-title group's midpoint equals the card's center, and the
subtitle's anchor is the same center.

### 7. Content is optically centered

Both directions, and on ink rather than on boxes.

Vertically, the whole block - eyebrow through the last subtitle line - sits on
the card's center, and the title's cap height centers on the icon's middle. A
title placed by baseline leaves the glyph hanging below the words it labels.

Horizontally, an icon-and-title group centers on what is visible. Icon artwork
does not fill its box evenly - in this library the ink runs from 58 percent of
the box (`document`) to 100 percent (`openai`) - so centering the box leaves the
group visibly off-center and gives every card a different icon-to-text gap.

Check: the midpoint of icon ink start to title ink end equals the card's center
within a pixel; vertical block midpoint within about 2 px of half the height.

### 8. Type is never stretched or squeezed

Every glyph renders at its natural width. Copy is fitted by choosing a size and
wrapping, never by distorting letterforms.

`textLength` with `lengthAdjust` is the trap: it silently rescales glyph widths
to hit a target, so one card gets a 37 percent squeeze while its neighbour is
untouched, and the two faces sit side by side looking like different fonts. It
is worse than a size step because it is invisible in the code and obvious on the
page.

When copy does not fit, step the size down for the whole diagram - one title
size shared by every card - so the type stays consistent as well as undistorted.
If that pushes the size below what the diagram needs, the card is too small:
widen it rather than reaching for a squeeze.

Check: `textLength`, `lengthAdjust` and `font-stretch` must not appear anywhere
in the SVG. Title font sizes should be a single value across all cards.

### 9. Annotation earns its space

A center annotation sits on the true ring center, its label fits inside it with
real clearance, and any caption clears the circle instead of cutting through it.

Check: annotation `cx`/`cy` equal the computed ring center; `_text_width` of the
title plus about 16 px of breathing room fits inside the circle at the title's
baseline; the caption baseline is below `cy + r`.

### 10. Type survives the size it is delivered at

A diagram is read wherever it is published, usually a phone. The canvas is
scaled to the screen width, and every size on it scales with it, so a large
canvas is what makes type small - not the type size.

Check: multiply each size by `screen_width / canvas_width`. At 390 px, aim for
the primary label at 12 px or more and nothing meaningful under 9 px. A 1180 px
canvas takes 20 px type below 7 px; the same type on an 800 px canvas survives.

Fix it from the canvas first - pick the smallest one that holds the content -
then set type. `layout.font_scale` scales card type and its rhythm together.

### 11. The diagram carries only what was asked for

Every element is there because it is needed. Dropped content is actually gone,
not shrunk or moved.

Check: read the request back against the render. A subtitle nobody asked for, a
center heading that repeats the article title, a label that duplicates the
arrows - each one costs room that the remaining elements need.

### 12. Canvas is filled

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
- Still 6/10 after that, because criterion 4 was being checked on one pair
  only. Measured across all five, the gaps were 164/288/179/288/164 - the side
  pairs 1.76x the top pairs - and the connectors, while sharing a radius, were
  clipped per card so each arc was a different length.
- Claimed 10/10 after one shared angular standoff made the arcs identical. Wrong
  again: a shared standoff means only the card needing the widest one is
  actually touched, so four connectors floated 12 px off their cards. Criteria
  3, 7, 10 and 11 were all still failing and none of them were in the rubric
  yet.
- 6/10 once those were named: connectors not touching, icon groups centered on
  boxes instead of ink, 20 px type on a 1180 px canvas landing under 7 px on a
  phone, and subtitles and a center heading still rendering after being cut.

Two lessons, both learned the hard way:

- A criterion sampled on one instance is not checked. Measure every pair, every
  connector, every card.
- A score is only as good as the rubric behind it. Several times the diagram
  measured full marks and was still visibly wrong, because the thing that was
  wrong had no criterion. When feedback names a fault the rubric does not cover,
  add the criterion before fixing the diagram.
- Score before shipping, not after being told. A card a third full shipped
  because criterion 5 only measured width, and because the render was looked at,
  noticed to be airy, and sent anyway with the concern written in prose instead
  of being treated as a failure. A flagged fault is still a fault - if it is
  worth mentioning, it is worth either fixing or asking about before it ships.

## The criteria that fight each other

Several criteria cannot be maximised together, so decide the priority before
tuning rather than chasing each complaint in turn:

- Even gaps (4) want cards small relative to the radius. Short connectors and a
  compact canvas want the opposite.
- Equal chords (2) want a square-ish card. Even gaps (4) want a wide flat one.
- A compact canvas reads better on a phone - it is scaled down less, so every
  size on it survives - but leaves less room for everything else.

For a diagram that will be read on a phone, start from the canvas: pick the
smallest one that still holds the content, then let the type sizes follow. A
1180 px canvas on a 390 px screen shrinks 20 px type to under 7 px.
