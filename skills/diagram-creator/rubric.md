# Diagram scoring rubric

Score a rendered diagram out of 10 before shipping it. Every criterion below
came out of a real review round, and each one is checkable - measure it against
the SVG or the rendered PNG rather than eyeballing and hoping.

A diagram is not done because it renders. It is done when every criterion
passes and a designer pass finds nothing structural left.

## How to score

Thirty criteria in six sections. Each is pass, fail, or N/A - a criterion that
does not apply (ring checks on a staircase, set checks on a lone diagram) leaves
the denominator entirely; it is never a free point. Anything you cannot verify
scores zero, not the benefit of the doubt.

Report per section and in total, naming the failures:

```
A geometry 6/7 · B cards 6/6 · C meaning 5/6 · D access 5/5 · E restraint 4/4 · F n/a
Total 26/28. Failing: A4 (gap spread 1.4x), C2 (evaluate->deploy arrow reversed).
```

Three criteria are blockers: C1, A6, B4, plus D1. A diagram failing a blocker
does not ship at any total - a reversed arrow or unreadable text is not offset by
good geometry.

Each criterion is tagged AUTOMATABLE (a script can check it against the JSON,
SVG or PNG) or JUDGEMENT (needs a reader, though the check is still concrete).

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
- Contrast: WCAG relative luminance of two hex values, `(L1+0.05)/(L2+0.05)` with
  sRGB linearisation. Ten lines of Python - compute it, never estimate it.
- Colour-vision simulation: transform the PNG with protanopia and deuteranopia
  matrices and desaturate a third copy.
- Icon ink: `diagram_creator.renderer.ICON_INK` gives where each glyph's ink
  starts and ends inside its box, as a fraction of the box.

One trap when measuring ink from a PNG: connector arrowheads land on a card's
outline, so a window that samples inside the card can catch them and shift the
apparent centre by 10 px. Compute the content's extent from the SVG numbers and
use the PNG only to confirm.

## The criteria

## Section A - Geometry and layout

### A1. Shape is true - AUTOMATABLE

A ring is a circle, not an ellipse. All card centers sit the same distance from
the ring center, and neighbors are `360 / count` degrees apart.

Check: radius spread under 0.5 px, every angular step within 0.5 degrees.
Fails when: the layout derives positions from canvas fractions, so a wide
canvas flattens the circle.

A staircase is a cascade, not a scatter. Every tread advances the same distance
right and every riser the same distance down, and no two steps share a row.

Check: the spread of consecutive `x` advances and of consecutive `y` advances,
both under 0.5 px; every riser at least the card height.

### A2. Connectors are all the same length - AUTOMATABLE, renderer-guaranteed

In a loop, every arrow between one node and the next is identical: same radius,
same length, same curvature. Different lengths are the single most visible way a
cycle stops reading as one circle, and the eye compares length before anything
else.

This is structural in the renderer, not a tolerance. Every connector spans one
shared angle, centred in its slot, so no card size can produce a ring of mixed
lengths. Chord spread measures 0.002 px across a five-node loop.

Check: chord length and arc radius of every connector. Chord spread under 0.5 px,
radius spread under 0.01 px. Anything larger means the shared sweep has been
bypassed and is a bug, not a tuning problem.

### A3. Connectors reach the cards they join - AUTOMATABLE, renderer-enforced

A connector that stops visibly short reads as broken.

One shared sweep and exact contact at both ends cannot both hold. A rectangle
covers a different angle at each slot on the circle unless it is exactly square,
so a sweep sized to clear the widest case leaves the narrowest ends a little
short. Measured floor is about 22 px for any card that can hold content, and
typical shapes land in the thirties. Equal length wins - a 30 px gap is far less
visible than one arrow half the length of its neighbour - and the renderer bounds
the gap at 42 px, rejecting anything worse with the card height that closes it.

Check: distance from each endpoint to the nearest card outline, at most 42 px.
The error names the card height that minimises it.

### A4. Nodes are clearly separated - AUTOMATABLE

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

### A5. Canvas is filled - AUTOMATABLE

The figure uses its canvas. Margins are symmetric on both axes and there is no
dead band or empty column.

Check: bounding box of all cards against the canvas; opposite margins should
match. For a ring, remember the circle only grows until its cards hit the
margin, so a wide canvas buys side whitespace, not a wider loop. Give rings a
roughly square canvas.

## Beyond the checklist

The criteria catch structure, geometry, meaning and access. They do not catch whether the
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
- Equal length (2) and exact contact (3) cannot both hold for rectangles on a
  circle. The renderer resolves this one for you: length is guaranteed, contact
  is bounded.
- A compact canvas reads better on a phone - it is scaled down less, so every
  size on it survives - but leaves less room for everything else.

For a diagram that will be read on a phone, start from the canvas: pick the
smallest one that still holds the content, then let the type sizes follow. A
1180 px canvas on a 390 px screen shrinks 20 px type to under 7 px.

### A6. Nothing collides and nothing is clipped - AUTOMATABLE, BLOCKER

No element overlaps another it does not belong to, and no ink is cut off by the
canvas edge. Text stays inside its card with real padding; edge labels sit in
open space, not on cards or other edges; connectors pass under no card they do
not connect.

Check, three parts: for every text element, `_text_width` against the card box -
at least 12 px of clearance on every side; for every edge label box, zero
intersection with any card box or other label; the outer 8 px band of the PNG
contains only background. The renderer knows every box and path, so all three
are assertable at render time.

### A7. Crossings are minimised and deliberate - AUTOMATABLE count, JUDGEMENT verdict

Every avoidable edge crossing is avoided. Crossings predict reading errors, so
each one must buy something.

Check: count segment intersections between edge paths in the SVG. In horizontal,
staircase and ring layouts the correct count is zero. In grid and manual, a
crossing needs a stated reason; if reordering nodes or moving an anchor removes
it, it fails.

## Section B - Cards and typography

### B1. Cards are filled, not just centered - AUTOMATABLE

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

### B2. One text axis per card - AUTOMATABLE

Title and subtitle share a single alignment. An icon plus a left-aligned title
above a centered subtitle gives a card two competing axes and three ragged
edges.

Check: the icon-and-title group's midpoint equals the card's center, and the
subtitle's anchor is the same center.

### B3. Content is optically centered - AUTOMATABLE

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

### B4. Type is never stretched or squeezed - AUTOMATABLE, renderer-enforced, BLOCKER

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

### B5. Type and strokes survive the size they are delivered at - AUTOMATABLE

A diagram is read wherever it is published, usually a phone. The canvas is
scaled to the screen width, and every size on it scales with it, so a large
canvas is what makes type small - not the type size.

Check: multiply each size by `screen_width / canvas_width`. At 390 px, aim for
the primary label at 12 px or more and nothing meaningful under 9 px. A 1180 px
canvas takes 20 px type below 7 px; the same type on an 800 px canvas survives.

Fix it from the canvas first - pick the smallest one that holds the content -
then set type. `layout.font_scale` scales card type and its rhythm together.

The same scaling applies to strokes. The 2.5 px connector and 2 px border must
each stay at 1 px or more after scaling, so a canvas wider than about 975 px
starts erasing connectors before it erases words. Arrowheads must stay at 4 px
or more.

### B6. Type hierarchy survives without colour - AUTOMATABLE

Title and subtitle are told apart by size and weight alone, because in greyscale
on a phone that is all that is left.

Check: title size between 1.15x and 1.6x the subtitle, and at least 200 weight
units heavier. Currently 20/750 over 16/500 - 1.25x and 250.

## Section C - Meaning and correctness

### C1. The picture matches the process - JUDGEMENT, BLOCKER

Every arrow points the way the process flows, every relationship shown exists,
and nothing described is missing or reversed. This is what everything else
serves: a beautiful diagram of the wrong process is worth less than none.

Check: write the source description as a list of `from -> to (label)` triples,
then read the same triples off the render - off the PNG, not the JSON, because
the JSON is what you meant and the render is what the reader gets. Zero
mismatches in direction or kind. Node titles use the user's own words.

### C2. One entry point, one reading order - AUTOMATABLE structure, JUDGEMENT verdict

A reader lands knowing where to start and which way to go. Diagrams read left to
right, top to bottom, rings clockwise from the top.

Check, from the edge list: a linear or staircase flow has exactly one node with
in-degree zero and it is leftmost or topmost; a ring has none, and its first
declared node sits at twelve o'clock. In grid and manual, trace from the
top-left: if following arrows forces the eye right-to-left or bottom-to-top
without a `below`-routed edge making the reversal explicit, it fails.

### C3. Labels are parallel and sized to their role - JUDGEMENT with automatable bounds

Peer nodes take the same grammatical form - all imperative verbs, or all nouns,
never a mixture.

Check: titles at most 3 words, subtitles at most 8, no title ending in
punctuation, one sentence case throughout, one part of speech across peers.

### C4. Edge labels name the interaction - JUDGEMENT

A labelled edge says what moves or what triggers it, not a repeat of a node
title. An unlabelled edge is right whenever direction alone carries the meaning.

Check: delete the label mentally; if nothing is lost it fails E1 instead. If it
survives, it must not duplicate either endpoint's title.

### C5. Colour means one thing per diagram - JUDGEMENT with automatable helper

Each hue maps to exactly one role and each role to one hue. Two nodes sharing a
colour claim to be the same kind of thing, and a reader will believe it.

Check: build `colour -> roles` from the JSON; every hue's list must be one kind
of thing. More than 4 node colours in one diagram almost always means colour has
stopped meaning anything. All ordinary connectors stay one neutral grey.

### C6. Icons are literal, not decorative - JUDGEMENT

Each icon depicts what its card names, closely enough that a reader could guess
the pairing.

Check: cover the titles, read only the icons, write down what each suggests,
then uncover. Any icon whose guess contradicts its card fails. An icon that
suggests nothing in particular fails E2.

## Section D - Accessibility

### D1. Text contrast meets WCAG AA - AUTOMATABLE, BLOCKER

Every text element reaches 4.5:1 against what is behind it; 3:1 is allowed at
24 px, or 18.66 px bold.

Check: WCAG relative luminance of the two hex values, `(L1+0.05)/(L2+0.05)`.
Compute it, do not guess. This caught a real failure: the subtitle token
`#7a8699` measured 3.36-3.52:1 against all six card fills, and the eyebrow's
`#64748b` 4.37:1 - both failing on every diagram ever rendered. `#475569` clears
it at 6.9-7.2:1.

### D2. Non-text contrast meets WCAG AA - AUTOMATABLE

Card borders, connectors and arrowheads reach 3:1 against what is adjacent.

Check: border against card fill and canvas; connector against canvas. Stock
values pass - borders 4.4-5.2:1, grey connector 4.76:1 on white. The divider
`#cbd5e1` is 1.65:1, acceptable only because it is supplementary; confirm rows
also separate by whitespace.

### D3. Colour is never the sole carrier - JUDGEMENT with automatable test

Any distinction that matters is also carried by a label, an icon, a dash or a
position.

Check: desaturate the PNG and reread it. Everything statable from the colour
version must still be statable.

### D4. It survives colour-blind viewing and print - AUTOMATABLE

Check: simulate deuteranopia and protanopia over the PNG and desaturate a third
copy. In all three, text still meets D1 on the transformed colours, and no two
hues D3 depends on collapse together. Stock green `#15803d` and red `#dc2626`
are a classic deuteranopia collision - acceptable only because failure edges
carry labels, so verify the label is there whenever both appear.

### D5. The accessible name and description are real - AUTOMATABLE presence, JUDGEMENT quality

The SVG carries `role="img"`, a `<title>`, and a `<desc>` that tells a
screen-reader user what a sighted reader learns.

Check: all three present and wired by `aria-labelledby`, and `<desc>` not equal
to the fallback `" -> ".join(titles)`, which reads as word salad aloud. A shipped
diagram sets `description` in its JSON. If SVGs are ever inlined into a page,
the fixed `id="title"`/`id="desc"` collide - suffix them per diagram.

## Section E - Restraint

### E1. Carries only what was asked for - JUDGEMENT

Every element is there because it is needed. Dropped content is actually gone,
not shrunk or moved.

Check: read the request back against the render. A subtitle nobody asked for, a
center heading that repeats the article title, a label that duplicates the
arrows - each one costs room that the remaining elements need.

### E2. Every visual difference is a semantic difference - JUDGEMENT with automatable inventory

Two elements that look different claim to be different kinds of thing.
Decoration that varies without meaning - a hue per card because six hues exist -
spends the reader's attention on noise.

Check: inventory every axis of variation in the JSON - colours, icons, variants,
eyebrows, edge styles - and state the rule deciding which element gets which
value. An axis with no statable rule fails.

### E3. Nothing is said twice - AUTOMATABLE for the known cases

Check: a `number-*` icon beside a title that also starts with a digit; a centre
title equal to the diagram or article title; a subtitle restating its title
(token overlap above 60 percent); an edge label equal to an endpoint's title.

### E4. Annotation earns its space - AUTOMATABLE

A center annotation sits on the true ring center, its label fits inside it with
real clearance, and any caption clears the circle instead of cutting through it.

Check: annotation `cx`/`cy` equal the computed ring center; `_text_width` of the
title plus about 16 px of breathing room fits inside the circle at the title's
baseline; the caption baseline is below `cy + r`.

## Section F - The set and the artifact

Apply when the diagram ships alongside others; N/A for a lone diagram, except F3.

### F1. One system across the set - AUTOMATABLE

Resolved title size, subtitle size, connector colour, corner radius and the
hue-to-meaning map are identical across the set unless a canvas difference forces
a documented `font_scale`.

Check: diff the resolved style values across every SVG in the article; zero
differences at the same scale. Merge the `colour -> meaning` maps and require no
contradiction - green cannot mean "deployed" in one figure and "success" in
another.

### F2. One apparent scale across the set - AUTOMATABLE

Cards look the same physical size in every figure once the page scales each
canvas to one column width.

Check: `card_width / canvas_width` for every diagram; spread at most 1.3x, or the
outlier needs a reason.

### F3. The artifact is intact - AUTOMATABLE

Check: PNG pixel dimensions match the SVG's intrinsic size; the PNG is newer than
its JSON and SVG; the corner pixel equals the declared background; no staging
directory is left behind.

## Beyond the checklist

The criteria catch structure, geometry, meaning and access. They do not catch whether the
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
- Equal length (2) and exact contact (3) cannot both hold for rectangles on a
  circle. The renderer resolves this one for you: length is guaranteed, contact
  is bounded.
- A compact canvas reads better on a phone - it is scaled down less, so every
  size on it survives - but leaves less room for everything else.

For a diagram that will be read on a phone, start from the canvas: pick the
smallest one that still holds the content, then let the type sizes follow. A
1180 px canvas on a 390 px screen shrinks 20 px type to under 7 px.
