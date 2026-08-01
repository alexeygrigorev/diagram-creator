---
name: diagram-creator
description: Create polished workflow diagrams as deterministic PNG files from compact JSON specifications or as custom SVGs with reusable icon glyphs. Use when Codex needs to visualize a process, agent lifecycle, state flow, branching workflow, or ASCII diagram, especially when Mermaid rendering is too plain or inflexible.
---

# Diagram Creator

Use the CLI for a standard horizontal PNG. Use a custom SVG for branching
layouts, compact article graphics, or icon-enhanced nodes. Always inspect the
rendered output.

For a custom SVG diagram, reuse the single-glyph symbols in
`assets/icons.svg`. Copy only the needed `<symbol>` elements into the output
SVG's `<defs>`, then place each icon with `<use href="#icon-name">`. Available
icons are `github`, `search`, `database`, `openai`, `issue`, `document`, `user`,
`api`, `settings`, `pull-request`, `rank-fusion`, `message`, `video`,
`sparkles`, `check`, `warning`, and `close`.

Keep icons monochrome and subordinate to node labels. Use brand glyphs only
when the node directly represents that service; do not recolor or distort them.
Place each icon close enough to its label that they read as one unit. Aim for a
6–12 px gap between the icon and the text, center the combined icon-label group
within the node when practical, and inspect the render for collisions.

## Custom SVG design system

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

Build nodes in local coordinates and place them only with `transform`. Reuse
this compact icon-card component; change the transform, semantic classes, icon,
and copy, but not its internal coordinates:

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
2. Create a JSON file with `nodes` and `edges`.
3. Use `route: "below"` for a feedback edge that returns to an earlier node.
4. Choose node colors from `purple`, `blue`, `amber`, `green`, `red`, or `gray`.
5. Choose edge colors from `gray`, `green`, `red`, `blue`, `purple`, or `amber`.
6. Render from a checkout:

```bash
uv run diagram-creator input.json output.png
```

Render without cloning the project:

```bash
uvx --from git+https://github.com/alexeygrigorev/diagram-creator \
  diagram-creator input.json output.png
```

Use `--width` and `--height` only when the default 1440 by 360 canvas does not
fit the workflow.

## JSON shape

```json
{
  "nodes": [
    {"id": "plan", "title": "Plan", "subtitle": "PM", "color": "purple"},
    {"id": "build", "title": "Build", "subtitle": "Engineer", "color": "blue"}
  ],
  "edges": [
    {"from": "plan", "to": "build"},
    {
      "from": "build",
      "to": "plan",
      "label": "FAIL",
      "color": "red",
      "route": "below"
    }
  ]
}
```

## Validate the output

Inspect the image after rendering. Check every label, arrow direction, feedback
loop, and crop. Keep an existing asset unchanged unless the user explicitly
asks to replace it; otherwise write a new filename.
