---
name: diagram-creator
description: Create polished workflow diagrams as deterministic SVG and PNG files from compact JSON specifications with reusable layouts, cards, icons, and connectors. Use when Codex needs to visualize a process, agent lifecycle, state flow, branching workflow, circular improvement loop, or ASCII diagram, especially when Mermaid rendering is too plain or inflexible.
---

# Diagram Creator

Create a JSON source first, render SVG while iterating, and render PNG only when
publishing. Keep the JSON beside the generated asset or in the project’s
diagram-source directory so later changes do not require hand-editing SVG.

Use `horizontal` for one row, `grid` for deliberate rows and columns, `ring`
for a five-stage circular loop, and `manual` for free-form branches and mixed
positions. Grid nodes use `row` and `column`; grid columns and rows size to
their largest node while `column_gap` and `row_gap` remain equal. Set
`column_width` and `row_height` when every grid cell should use fixed
dimensions. Manual layout keeps explicit `x` and `y` available when the grid
is not appropriate.

Available icons are `github`, `search`, `database`, `openai`, `issue`,
`document`, `user`, `browser`, `websocket`, `api`, `settings`, `pull-request`,
`rank-fusion`, `message`, `video`, `sparkles`, `check`, `warning`, `close`,
`mention`, `number-1`, `number-2`, and `number-3`. Use the numbered icons to
mark ordered stages instead of writing the step number into the title.

If a diagram needs an icon that is not available, create it instead of using
an unrelated substitute. Add it to the renderer's icon library and accepted
icon set, match the existing monochrome style, and validate it in the rendered
diagram.

Keep icons monochrome and subordinate to node labels. Use brand glyphs only
when the node directly represents that service; do not recolor or distort them.
Place each icon close enough to its label that they read as one unit. Aim for a
6–12 px gap between the icon and the text, center the combined icon-label group
within the node when practical, and inspect the render for collisions.

Use `"variant": "icon"` for a standalone symbol with its `title` underneath
and no card. Use this for actors and simple endpoints when a full card adds
unnecessary visual weight. Set `"show_label": false` when the icon should have
no visible label; keep `title` because it is still used for accessibility. Use
`"icon_size"` for an explicit override. Prefer the reusable standalone sizes:
56×56 px for `user`, 160×112 px for `browser`, and 84×84 px for `database`.
The renderer applies these automatically when no override is present.

Use `"variant": "plain"` for a card without its rectangle. It keeps the grid
cell, icon column, and typography of a card but drops the fill, border, and
shadow. Use it for row and stage labels that name a group of nodes instead of
participating in the flow, and keep its subtitle on the title axis.

In a grid diagram, use `"dividers": [{"after_row": 0}]` to separate rows with a
dashed rule drawn halfway between that row and the one below. Prefer a divider
over a connector when consecutive rows are separate snapshots of one system
rather than steps that hand work to each other.

## Design system

Lay out the diagram on a grid before drawing individual nodes. Prefer clear
rows and columns over independently positioned elements.

- Give each stage one column and related alternatives one shared row or stack.
- Use equal card widths within a diagram. Align card edges and centers exactly.
- Use one x-coordinate for every card in a column and one y-coordinate for
  every card in a row.
- Keep horizontal gutters equal. Start at 60 px and use 48–72 px when the
  diagram needs adjustment.
- Keep repeated vertical gaps equal. Start at 20 px inside a stack.
- Route connectors through the center of the gutters. Equal relationships
  should have equal arrow lengths.
- Increase the canvas before compressing cards or their contents.

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

For a compact node with an icon, treat the icon and the two text lines as one
component:

- Fix one icon axis and one text axis for every comparable card. Never move an
  icon to compensate for a shorter or longer label.
- Use a 24–28 px icon viewport. Center it vertically against the full title and
  subtitle block.
- Left-align both title and subtitle on the same text axis when labels vary in
  length. Keep 6–12 px between the icon viewport and the longest line.
- If centered text is required, reserve a fixed icon column and center both
  lines inside the remaining text column; do not center each icon-label pair
  independently.

For a taller node with an icon, place the icon and title on one primary row and
center the subtitle beneath them. Reuse the same icon axis, title axis, and
baselines for all cards in that row or column. Keep the icon out of the
subtitle's line box.

For a node without an icon, center the title and subtitle on the card center.
Do not reserve an empty icon column. Use the same typography, line spacing,
padding, border, and corner tokens as icon-bearing peers so the visual weight
stays consistent.

Use semantic colors consistently within one diagram: blue for sources, purple
for conversations and integrations, amber for processing, green for datasets
and deployed services, red for failures, and gray for neutral structure. Use a
light tint for fills, a saturated hue for borders/icons, `#172033` for primary
text, `#64748b` for secondary text and connectors, and one subtle shadow for
all cards.

## Circular loop illustrations

Use a symmetric ring when the final step improves or restarts the first step.
For five nodes, place one card at the top, two at the sides, and two at the
bottom. Keep every card the same size and keep opposite positions mirrored
around the canvas center.

Use a `1100×550` canvas with `260×100` cards. Declare nodes clockwise starting
at the top and connect each node to the next with `route: "ring"`. The renderer
places the five cards in symmetric slots, mirrors opposite Bézier curves, and
uses a straight horizontal arrow between the bottom cards. Do not recreate the
ring with manual coordinates.

```json
{
  "canvas": {"width": 1100, "height": 550, "background": "#ffffff"},
  "layout": {"type": "ring", "card_width": 260, "card_height": 100},
  "nodes": [
    {"id": "one", "title": "Contribute", "icon": "issue", "color": "blue"},
    {"id": "two", "title": "Curate", "icon": "message", "color": "purple"},
    {"id": "three", "title": "Deploy", "icon": "database", "color": "green"},
    {"id": "four", "title": "Answer", "icon": "mention", "color": "purple"},
    {"id": "five", "title": "Evaluate", "icon": "warning", "color": "red"}
  ],
  "edges": [
    {"from": "one", "to": "two", "route": "ring"},
    {"from": "two", "to": "three", "route": "ring"},
    {"from": "three", "to": "four", "route": "ring"},
    {"from": "four", "to": "five", "route": "ring"},
    {"from": "five", "to": "one", "route": "ring"}
  ],
  "center": {"title": "CURATION", "subtitle": "LOOP", "detail": "Keep improving"}
}
```

Keep all loop arrows the same stroke, marker, and color unless a semantic
exception is explicitly important. A different color on only the closing edge
can make one continuous loop look broken.

Optionally place a small neutral dashed circle in the center with a two-line
label such as `CURATION / LOOP`. Treat it as annotation, not another workflow
node: do not attach arrows to it, and keep it visually quieter than the cards.

When one edge looks wrong, fix the reusable ring router rather than overriding
one generated path. Inspect the rendered loop for bilateral symmetry,
consistent arrow curvature, clear card-edge attachment, and unobstructed center
whitespace.

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
- Put long request/response semantics in card subtitles when a 60 px connector
  cannot hold the label. If an edge label is essential, widen the relevant
  gutters consistently or route it through open space.

## Audit before handoff

1. Render every SVG with Chromium, not a different SVG engine.
2. Inspect every PNG at full resolution. A montage is useful for consistency
   but can hide 1–10 px overflow and clipped labels.
3. Check icon viewport, title axis, subtitle baseline, border width, radius,
   semantic color, column gutter, stack gap, connector attachment, and crop.
4. Confirm each PNG has the SVG's intrinsic dimensions and is newer than its
   source. Rerun the publisher after the final SVG edit.
5. When exact browser fidelity matters, render the SVG independently with the
   same Chromium flags and require zero differing pixels against the PNG.
6. For a multi-diagram set, perform a second independent visual audit after
   all fixes. Re-audit the current artifacts, not remembered coordinates from
   an earlier revision.
7. After an interrupted publish, remove any leftover `.diagram-publish-*`
   staging directory before committing.

## Publish SVG diagrams as PNG

Keep SVG references while iterating. When the user asks to publish, convert all
local SVG images referenced by one or more Markdown files and replace those
references with PNG:

```bash
python scripts/publish_svgs.py article.md
```

Run the script from the skill directory or use its absolute path. It renders
with Chromium so the PNG matches the browser-rendered SVG. It retains the SVG
sources, writes same-name PNG files beside them, and changes Markdown only
after every referenced SVG renders successfully. Use `--scale 2` when a
higher-density raster is needed. PNG output has a white background by default;
pass `--background transparent` when transparency is intentional. Rerun the
same command to refresh PNGs after editing their retained SVG sources.

## Render a diagram

1. Preserve the user's node names, roles, edge directions, and loop labels.
2. Create a JSON file with `canvas`, `layout`, `nodes`, and `edges`.
3. Add `icon` to icon-bearing nodes; use `mention` for the `@` glyph. Use
   `"variant": "icon"` for an icon with an optional label and no card.
4. Use `route: "below"` for feedback, `ring` for a circular loop, or `curve`
   with two control points for a manual layout. Use `"bidirectional": true`
   for one connector with arrowheads at both ends.
5. Choose node colors from `purple`, `blue`, `amber`, `green`, `red`, or `gray`.
6. Render SVG from a checkout while iterating:

```bash
uv run diagram-creator input.json output.svg
```

Render without cloning the project:

```bash
uvx --from git+https://github.com/alexeygrigorev/diagram-creator \
  diagram-creator input.json output.svg
```

Render `output.png` when needed; Chromium renders the generated SVG so the two
formats match. Prefer canvas dimensions in JSON. Use `--width` and `--height`
only for one-off overrides.

## JSON shape

```json
{
  "title": "Build and deploy",
  "canvas": {"width": 900, "height": 500},
  "layout": {"type": "manual", "card_width": 220, "card_height": 100},
  "nodes": [
    {"id": "source", "title": "Sources", "icon": "document", "x": 40, "y": 60},
    {"id": "build", "title": "Build index", "icon": "settings", "x": 340, "y": 280}
  ],
  "edges": [
    {
      "from": "source",
      "to": "build",
      "route": "curve",
      "from_anchor": "right",
      "to_anchor": "top",
      "controls": [[300, 110], [450, 190]]
    }
  ]
}
```

## Validate the output

Inspect the image after rendering. Check every label, arrow direction, feedback
loop, and crop. Keep an existing asset unchanged unless the user explicitly
asks to replace it; otherwise write a new filename.
