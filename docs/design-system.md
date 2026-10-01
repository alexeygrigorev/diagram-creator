# Design system

The renderer applies this design system automatically; a spec chooses only
semantic colors, icons, variants, and geometry. This document is the reference
for auditing rendered output and for evolving the renderer. The drawing and
routing model is in [how-it-works.md](how-it-works.md).

## Tokens

Use these default tokens for article diagrams. Scale them together when the
canvas or typography changes.

Copy this block into the SVG `<style>` element and reuse the values throughout
the diagram:

```css
:root {
  --ds-space-xs: 6px;
  --ds-space-sm: 10px;
  --ds-space-md: 16px;
  --ds-space-lg: 20px;
  --ds-space-xl: 30px;
  --ds-column-gap: 60px;

  --ds-card-width: 220px;
  --ds-compact-height: 65px;
  --ds-action-height: 100px;
  --ds-endpoint-height: 120px;
  --ds-radius: 16px;
  --ds-radius-lg: 18px;
  --ds-radius-xl: 20px;

  --ds-icon-inset: 16px;
  --ds-compact-icon-size: 26px;
  --ds-action-icon-size: 28px;
  --ds-compact-copy-x: 54px;
  --ds-action-copy-x: 56px;

  --ds-border-width: 2px;
  --ds-connector-width: 2.5px;
  --ds-title-size: 17px;
  --ds-compact-title-size: 16px;
  --ds-subtitle-size: 14px;
  --ds-eyebrow-size: 12px;

  --ds-text: #172033;
  --ds-muted: #64748b;
  --ds-blue: #2563eb;
  --ds-blue-fill: #eff6ff;
  --ds-purple: #7c3aed;
  --ds-purple-fill: #f5f3ff;
  --ds-amber: #c2410c;
  --ds-amber-fill: #fff7ed;
  --ds-green: #15803d;
  --ds-green-fill: #ecfdf5;
  --ds-red: #dc2626;
  --ds-red-fill: #fef2f2;
}
```

| Token | Default | Use |
| --- | ---: | --- |
| `space-xs` | 6 px | Minimum icon-to-label gap |
| `space-sm` | 10 px | Normal icon-to-label gap |
| `space-md` | 16 px | Card inset and small separation |
| `space-lg` | 20 px | Gap between stacked cards |
| `space-xl` | 30 px | Outer canvas margin |
| `column-gap` | 60 px | Gap between workflow columns |
| `card-width` | 220 px | Standard node width |
| `compact-height` | 65 px | Two-line source or input node |
| `action-height` | 100 px | Process or integration node |
| `endpoint-height` | 120 px | Emphasized service or endpoint |
| `radius` | 16 px | Compact card corner radius |
| `radius-lg` | 18–20 px | Action or endpoint radius |
| `border` | 2 px | Card outline |
| `connector` | 2.5 px | Arrow and bus stroke |
| `title-size` | 17 px | Node title |
| `compact-title-size` | 16 px | Compact icon-card title |
| `subtitle-size` | 14 px | Supporting text |
| `eyebrow-size` | 12 px | Optional service/category label |
| `standalone-user-size` | 56×56 px | Person or actor primitive |
| `standalone-browser-size` | 160×112 px | Browser or frontend primitive |
| `standalone-database-size` | 84×84 px | Database cylinder primitive |

## Semantic colors

Use semantic colors consistently within one diagram and across an article:
blue for human actors, sources, and environments; purple for the pipeline,
frontend sessions, and integrations; amber for build steps and backend
processing; green for persistence, production, and success; red for alerts
only, at most one red node per figure; gray for inert or not-yet-real
elements. Color an edge to match the domain it enters (green into the
database, purple into the pipeline); leave structural edges gray. Use a
light tint for fills, a saturated hue for borders/icons, `#172033` for primary
text, `#64748b` for secondary text and connectors, and one subtle shadow for
all cards.

## Component internals

The renderer builds nodes in local coordinates and places them with one outer
transform. These are the component internals produced by JSON; use them as an
audit reference, not as a reason to edit the generated SVG:

```svg
<g class="node node-compact node-with-icon"
   transform="translate(30 20)" filter="url(#shadow)">
  <rect class="source" width="220" height="65" rx="16"/>
  <use href="#icon-document" x="16" y="19" width="26" height="26"/>
  <text class="title icon-copy" x="54" y="27">Docs website</text>
  <text class="subtitle icon-copy" x="54" y="50">datatalks.club/docs</text>
</g>
```

Use `text-anchor: start` for `.icon-copy`. For an icon-free compact card, omit
the `<use>`, remove `.icon-copy`, and place both text lines at `x="110"` so
they are centered in the 220 px card.

Reuse these local coordinates for taller components:

```svg
<!-- 220×100 action card -->
<g class="node node-action node-with-icon" transform="translate(310 30)">
  <rect class="process" width="220" height="100" rx="18"/>
  <use href="#icon-settings" x="16" y="36" width="28" height="28"/>
  <text class="title icon-copy" x="56" y="56">Build index</text>
  <text class="subtitle" x="110" y="81">Create the new index</text>
</g>

<!-- 220×120 endpoint card with an eyebrow -->
<g class="node node-endpoint node-with-icon" transform="translate(590 185)">
  <rect class="endpoint" width="220" height="120" rx="20"/>
  <text class="eyebrow" x="110" y="29">AWS LAMBDA</text>
  <use href="#icon-database" x="16" y="41" width="28" height="28"/>
  <text class="title icon-copy" x="56" y="61">FAQ assistant</text>
  <text class="subtitle" x="110" y="91">Search index + answer API</text>
</g>
```

Treat these coordinates as component internals. Move a node with its group
transform; do not retune its icon or text coordinates per label. Represent a
text glyph such as `@` as a pseudo-icon centered in the same 28 px icon column.

For a compact node with an icon, treat the icon and the two text lines as one
component:

- Fix one icon axis and one text axis for every comparable card. Never move an
  icon to compensate for a shorter or longer label.
- Grid and manual layouts share those axes by default; set
  `"fixed_icon_axis": false` only when a lone card should optically center its
  icon-title pair, and `true` to opt an automatic layout in.
- Use a 24–28 px icon viewport. Center it vertically against the full title and
  subtitle block.
- Left-align both title and subtitle on the same text axis when labels vary in
  length. Keep 6–12 px between the icon viewport and the longest line.
- If centered text is required, reserve a fixed icon column and center both
  lines inside the remaining text column; do not center each icon-label pair
  independently.

For a taller node with an icon, place the icon and title on one primary row and
put the subtitle beneath them on the icon's left margin. The two lines share one
axis - a left-aligned title over a centered subtitle reads as two competing
alignments. Center the whole block on the card rather than centering the icon
row and letting the subtitle hang below it. Reuse the same icon axis, title
axis, and baselines for all cards in that row or column. Keep the icon out of
the subtitle's line box.

For a node without an icon, center the title and subtitle on the card center.
Do not reserve an empty icon column. Use the same typography, line spacing,
padding, border, and corner tokens as icon-bearing peers so the visual weight
stays consistent.

Keep each icon close enough to its label that they read as one unit: a 6–12 px
gap between the icon and the text, with the combined icon-label group centered
within the node when practical. Keep icons monochrome, and do not recolor or
distort brand glyphs. Standalone icons use shared reusable sizes - 56×56 px for
`user`, 160×112 px for `browser`, 84×84 px for `database` and `volume`, and
112×56 px for the horizontal `queue` tube - and connector anchors follow the
glyph's visible ink rather than its transparent SVG viewport.

## House numbers

Lay out the diagram on a grid before drawing individual nodes. Prefer clear
rows and columns over independently positioned elements. Numbers that recur
across every accepted article figure:

- Cards are 220×100. Inside a boundary holding three cards, narrow all three
  to 210 so the boundary keeps 40 px gaps. Compact resource rows (three small
  cards inside an access boundary) are 150×70. Stacked store cards shorten to
  240×80–90. A full-width baseline or cap card (spanning the peers above or
  below it) is deliberate meaning, not a defect - but only one per figure.
- Canvas dimensions are multiples of 10. A four-to-seven-node figure lands at
  940–1110 wide. Size the canvas from the finished content: the node bounding
  box plus roughly 40 px of margin on every side, symmetric on both axes.
  Content should fill 60–90% of the canvas. The CLI prints a `note:` on stderr
  when a manual layout leaves dead margin - fix the spec, do not ignore it.
- Standalone icons sitting on a card row: place a 56 px glyph at the row's
  `y + 22` so its center matches a 100 px card's center. The label prints
  below the glyph, so rows of icons end lower than rows of cards.
- Give each stage one column and related alternatives one shared row or stack.
  Use equal card widths within a diagram, one x-coordinate for every card in a
  column, one y-coordinate for every card in a row, and equal horizontal
  gutters starting at 60 px (48–72 px when the diagram needs adjustment).
  Keep repeated vertical gaps equal, starting at 20 px inside a stack. Route
  connectors through the center of the gutters so equal relationships get
  equal arrow lengths.
- Bidirectional connectors need at least 48 px between their visible
  endpoints; the renderer rejects shorter spans because the two arrowheads
  collide.
- Increase the canvas before compressing cards or their contents.

## Prevent layout drift

Apply tokens in the SVG itself; a token table does not help if nodes still use
independently tuned absolute coordinates.

- Render before deciding that copy fits. SVG coordinates describe anchors, not
  the rendered ink bounds of a particular font.
- Keep at least 12–16 px of visible padding between rendered text and the card
  edge. Inspect long titles, decision labels, and edge labels at full size.
- If a label overflows, shorten redundant copy or widen every peer card and
  move the entire column grid. Never move only its icon, change only its text
  axis, or widen one peer card.
- Keep peer cards the same width even when one label is short. Increase the
  canvas before reducing padding or font size.
- Keep equal gutters between columns. Route split/merge buses through gutter
  centers so equivalent connector segments have equal lengths.
- Attach dependency lines to the actual producer and consumer nodes. Do not
  start a dashed or labeled relationship in an empty gutter merely because the
  line looks nearby.
- Keep edge-label pills at least 14 px clear of arrowheads. The renderer sizes
  pills from measured text and rejects labels that cannot fit safely; widen the
  gutter or shorten the label instead of allowing a pill to cover a marker.
- Connectors that enter or leave a dashed boundary receive a background halo
  automatically. Confirm the resulting port is visible and the boundary does
  not merge with the connector or arrowhead.
- Put long request/response semantics in card subtitles when a 60 px connector
  cannot hold the label. If an edge label is essential, widen the relevant
  gutters consistently or route it through open space.

## Audit before handoff

1. Render every SVG with Chromium, not a different SVG engine.
2. Inspect every PNG at full resolution. A montage is useful for consistency
   but can hide 1–10 px overflow and clipped labels.
3. Check icon viewport, title axis, subtitle baseline, border width, radius,
   semantic color, column gutter, stack gap, connector attachment, and crop.
   Parse every ordinary edge path as well: each segment must be horizontal or
   vertical within 0.5 px. Any unexplained `L` segment whose x and y both
   change is a shipping blocker, including a one-pixel incline that is easy to
   miss in a montage.
4. Confirm each PNG has the SVG's intrinsic dimensions and is newer than its
   source. Rerun the publisher after the final SVG edit.
5. When exact browser fidelity matters, render the SVG independently with the
   same Chromium flags and require zero differing pixels against the PNG.
6. For a multi-diagram set, perform a second independent visual audit after
   all fixes. Re-audit the current artifacts, not remembered coordinates from
   an earlier revision.
7. After an interrupted publish, remove any leftover `.diagram-publish-*`
   staging directory before committing.

For ring layouts, also inspect the rendered loop for bilateral symmetry,
consistent arrow curvature, clear card-edge attachment, and unobstructed
center whitespace. When one generated edge looks wrong, fix the reusable ring
router in the renderer rather than overriding one generated path.

## Extending the icon library

If a diagram needs an icon that is not available, create it instead of using
an unrelated substitute. Add a monochrome `<symbol>` to
[`skills/diagram-creator/assets/icons.svg`](../skills/diagram-creator/assets/icons.svg)
and register the name in the `ICONS` dictionary in `diagram_creator/spec.py`,
matching the existing style, then validate the icon in a rendered diagram.
