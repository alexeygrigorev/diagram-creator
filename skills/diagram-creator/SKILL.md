---
name: diagram-creator
description: Create polished workflow diagrams as deterministic SVG and PNG files from compact JSON specifications with reusable layouts, cards, icons, and connectors. Use when Codex needs to visualize a process, agent lifecycle, state flow, branching workflow, circular improvement loop, or ASCII diagram, especially when Mermaid rendering is too plain or inflexible.
---

# Diagram Creator

Create a JSON source first, render SVG while iterating, and render PNG only when
publishing. Keep the JSON beside the generated asset or in the project’s
diagram-source directory so later changes do not require hand-editing SVG.

## Design the figure before the JSON

Every figure that shipped without rework started from a one-sentence brief;
every figure that skipped this step was rebuilt from scratch. Write the brief
first: the `title`, plus a `description` stating the one thing the figure
teaches that prose cannot ("dashboards do not generate alerts", "the agent does
not fix production directly"). The description becomes the SVG `<desc>` and the
article's alt text, and writing it first is what exposes a figure with no job.

Pick the shape from the relationship, not from paragraph order:

- A left-to-right **chain** only when each stage genuinely hands work to the
  next. A chain of boxes that restates the surrounding text in order is an
  automatic reject, and replacing it with a busier non-linear layout is not
  the fix - the fix is finding the relationship worth drawing.
- A **fork** for one decision: one entry path, one fork, labelled branches,
  zero crossings.
- **Parallel lanes** for an automatic path above a manual path.
- A **stack with no edges** for peers and layers. Peers are not a sequence:
  if the items do not causally produce each other, do not draw arrows between
  them. Let position carry the relationship - a wide foundation card below,
  peer cards in a row, a cap above - and use eyebrows (`START HERE`, `LAST`)
  as the reading-order cue.
- **Staged rows with dividers** for consecutive snapshots of one system, or
  **two whole figures with identical geometry** for a before/after pair - copy
  the accepted figure's coordinates verbatim and change only what changed.
- **Specimen cards** when the subject is data: `42 requests/s` teaches what
  "Rates and counts" cannot.

Budget five to seven nodes. Nodes that never survive review: terminal outcome
nodes ("Job ends", "Record the incident"), abstraction nodes that stand for a
set - name the three concrete things instead - and policy or process statements
with no visual referent. If the caption sentence reads fine without a node,
cut the node. The same test kills most labels: arrow annotations, subtitles
that restate their title, units, and provenance notes.

Give the figure one or two star cards and demote everything else. Plumbing a
reader already understands (an alert, a queue, a trigger function) becomes a
standalone `"variant": "icon"` glyph, not a full card with a subtitle. Gray is
for inert or not-yet-real elements; at most one red node per figure, for
alerts. De-emphasising the peers is what makes the star readable.

Derive the edge list from the description sentence: every relationship the
caption asserts gets exactly one edge, and no edge exists that the caption
does not assert. Adjacency is not a connection - a relationship implied by
geometry but never drawn is the most common missing edge. The reverse failure
is drawing arrows because nodes are near each other.

Writing `"controls": [[x, y], [x, y]]` means the layout has already lost:
hand-tuned curves are the signature of a shape the diagram cannot support.
Step back to the shape menu instead of tuning the curve.

Across an article, one concept keeps one name, one icon, one shape, and one
color in every figure. When extending an accepted figure, reuse its node
coordinates unchanged and append; do not re-layout what the reader has
already learned.

When a figure is rejected, diagnose before restructuring: "bad" means either
*adds no insight* (a content problem - redesign the shape) or *not aligned,
not straight, uneven* (a geometry problem - fix coordinates and change nothing
else). Restructuring an aligned-but-plain figure and polishing an
insightful-but-crooked one are opposite fixes, and applying the wrong one
loses accepted work. For a content redesign, sketch two or three genuinely
distinct concepts cheaply first - ASCII inline is enough - and confirm the
direction before rendering.

## Layouts

Use `horizontal` for one row, `grid` for deliberate rows and columns, `ring`
for a circular loop of three or more stages, `staircase` for a sequence that
only moves forward, and `manual` for free-form branches and mixed positions.
Grid nodes use `row` and `column`, and each column and row sizes to its
largest node; manual nodes use explicit `x` and `y`.

**Ring.** Declare nodes clockwise starting at the top and connect each node to
the next with `route: "ring"`. The renderer spaces the cards evenly on a
circle, fits the largest circle the canvas allows, and draws every connector
as an arc of that same circle - do not recreate the ring with manual
coordinates. Give a ring a roughly square canvas: a wide one only produces a
small circle with large side margins. A `940×800` canvas with `260×100` cards
suits five nodes, and rendering fails with a suggested canvas size when the
cards would overlap; keep cards near square so the arcs come out even. Set
`layout.margin` to change the gap kept around the cards. Optionally add a
`center` annotation (`title`, `subtitle`, `detail`): it is quiet annotation,
not a workflow node - no arrows attach to it, and `detail` renders as a
caption below the circle. Keep every loop arrow the same stroke, marker, and
color; a different color on only the closing edge makes one continuous loop
look broken.

**Staircase.** Declare nodes in step order and leave the edges unrouted -
`forward` becomes the staircase elbow. Use `descending` when later stages
narrow or dig deeper, and `ascending` for progress upward. Keep every card the
same width, and mark order with the `number-1`–`number-3` icons or an eyebrow;
the cascade already carries direction, so do not also number the titles. The
cascade needs a wide canvas - seven 320×96 cards want about `1680×880` - and
rendering fails with a suggested size when it does not fit. Set `step_x` and
`step_y` only when a specific overlap is the point, once for the whole
diagram.

Complete JSON for both is in the repository
[README](https://github.com/alexeygrigorev/diagram-creator#examples).

## Write the spec

```json
{
  "title": "Build and deploy",
  "description": "Sources feed the index build, and the built index deploys.",
  "canvas": {"width": 940, "height": 280},
  "layout": {"type": "manual", "card_width": 220, "card_height": 100},
  "nodes": [
    {"id": "source", "title": "Sources", "icon": "document", "x": 40, "y": 90},
    {"id": "build", "title": "Build index", "icon": "settings", "color": "amber", "x": 360, "y": 90},
    {"id": "deploy", "title": "Deploy", "icon": "check", "color": "green", "x": 680, "y": 90}
  ],
  "edges": [
    {"from": "source", "to": "build"},
    {"from": "build", "to": "deploy", "color": "green"}
  ]
}
```

### Colors and icons

Node colors are `purple`, `blue`, `amber`, `green`, `red`, and `gray`. Use
them semantically and consistently across an article: blue for human actors,
sources, and environments; purple for the pipeline, frontend sessions, and
integrations; amber for build steps and backend processing; green for
persistence, production, and success; red for alerts only, at most one node
per figure; gray for inert or not-yet-real elements. Color an edge to match
the domain it enters and leave structural edges gray. The renderer pairs a
light tint fill with a saturated border and icon.

Available icons are `aws`, `github`, `search`, `shield`, `container`,
`database`, `volume`, `openai`, `issue`, `document`, `user`, `browser`,
`websocket`, `api`, `settings`, `pull-request`, `rank-fusion`, `message`,
`video`, `sparkles`, `check`, `warning`, `close`, `mention`, `number-1`,
`number-2`, `number-3`, `workflow`, `robot`, `observability`, `environment`,
`registry`, `collector`, `alert`, `queue`, `lambda`, `terminal`, and `shell`.
Use `terminal` for a terminal-emulator window and `shell` for the command
interpreter or prompt inside it. Use the numbered icons to mark ordered stages
and `mention` for the `@` glyph. Keep icons monochrome and subordinate to
labels, and use a brand glyph only when the node directly represents that
service. If a needed icon does not exist, do not substitute an unrelated one -
add it to the renderer first (see the repository's design-system doc).

### Node variants

- `"variant": "icon"` - a standalone symbol with its `title` underneath and no
  card, for actors and simple endpoints where a full card adds weight. Set
  `"show_label": false` to drop the visible label but keep `title` for
  accessibility, and `"icon_size"` for an explicit override. The renderer
  applies shared standalone sizes automatically and anchors connectors to the
  visible glyph ink rather than its transparent padding.
- `"variant": "plain"` - a card without its rectangle: the same grid cell,
  icon column, and typography, but no fill, border, or shadow. For row and
  stage labels that name a group of nodes instead of participating in the
  flow.
- `"variant": "boundary"` - a dashed infrastructure or runtime boundary behind
  related nodes. Give it explicit `x`, `y`, `width`, and `height`, or set
  `contains` to node IDs and let the renderer derive the box. Derived margins
  default to 60 px above (including the title), 20 px on each side, and 30 px
  below; override any side with `"margin": {...}`.
- `"variant": "attached"` - a small sidecar or agent that visually belongs to
  a larger card. `attach_to` names the parent, `attach_side` is `left`,
  `right`, `top`, or `bottom` (default `right`), `attach_align` is `start`,
  `center`, or `end`, and `attach_overlap` sets how far the badge overlaps the
  parent. Edges connected to the badge start there rather than at the parent
  card.
- `"variant": "specimen"` - a card that resembles the data it explains. Add a
  `specimen` object with a `mode` of `series`, `record`, or `waterfall` and
  exactly three short `items`. Keep specimen cards at least 360×140 px, and
  use them when visual form teaches a distinction that parallel prose cards
  cannot.

### Dividers

`"dividers": [{"after_row": 0}]` separates grid rows with a dashed rule drawn
halfway between that row and the one below. In a manual layout,
`{"after_node": "id"}` draws the rule below one named node instead. Prefer a
divider over a connector when consecutive rows are separate snapshots of one
system rather than steps that hand work to each other.

### Edges

- Omit `route` when the connector's rendered anchors align exactly; the
  default rejects off-axis endpoints, and a slightly inclined arrow is always
  a defect. Use `orthogonal` for offset endpoints, `below` for feedback,
  `ring` inside a ring layout, and `step` for one rounded elbow between two
  offset cards. Reserve an explicit `straight` diagonal for the very rare
  case where diagonal direction itself carries meaning, and say why in the
  figure brief.
- `curve` with explicit control points is a last resort that usually signals
  the wrong shape - step back to the shape menu instead of tuning the curve.
- `"bidirectional": true` needs at least 48 px between the visible endpoints
  because the two arrowheads collide. `"directed": false` removes arrowheads;
  `"dashed": true` marks a secondary control relationship rather than the
  main application flow.
- Edge labels are rare - about one edge in six, at most 16 characters, and
  only for what direction alone cannot say: a trigger (`Manual promotion`), a
  protocol (`HTTPS / WSS`), an artifact (`Version tag`), a fork condition
  (`Bug reproduced`). The renderer sizes label pills from measured text and
  rejects a label whose gutter cannot hold it clear of the arrowheads.
- Draw paired connectors as reflections of each other. When the edge into a
  card and the edge out of it play symmetric roles, such as down to a lower
  lane and back up, give them the same route reflected. If one leaves a side
  and enters a bottom, the other leaves a bottom and enters a side. Set
  `from_anchor` and `to_anchor` on both edges.
- Use `left_top`, `left_bottom`, `right_top`, or `right_bottom` anchors when
  parallel inputs must attach to distinct points on one card edge.

### Text budgets

Subtitles are one verb phrase, at most ~30 characters. Use `·` to fold
management context into a boundary title (`AWS EC2 instance ·
CloudFormation-managed`). Eyebrows have two jobs: a category stamp
(`CONTAINER`) or a reading-order cue (`START HERE`, `LAST`) - not a second
subtitle. Size the canvas from the finished content - the node bounding box
plus roughly 40 px of margin on every side, dimensions in multiples of 10 -
so content fills 60–90% of the canvas. The CLI prints `note:` advisories on
stderr for dead margin or a missing description; treat them as review
findings and fix the spec, not noise.

## Styles

Every diagram renders in one named style, which decides colors, fonts, and
the default canvas background: `default` (the original light look),
`asl-light`, or `asl-dark`. Set `"style"` at the top level of the JSON, or
override per render with `--style` without touching the spec. An explicit
`canvas.background` still wins. When a page serves one image for both themes,
render both variants from the same spec and pick the one the page needs; do
not hand-edit hexes in the generated SVG.

## Render

1. Preserve the user's node names, roles, edge directions, and loop labels.
2. Write the JSON with `title`, `description`, `canvas`, `layout`, `nodes`,
   and `edges`, description first.
3. Render SVG while iterating:

```bash
uv run diagram-creator input.json output.svg
```

Without cloning the project:

```bash
uvx --from git+https://github.com/alexeygrigorev/diagram-creator \
  diagram-creator input.json output.svg
```

4. Render `output.png` only when publishing; Chromium renders the generated
   SVG so the two formats match. Prefer canvas dimensions in JSON; `--width`
   and `--height` are one-off overrides.

## Validate and publish

Inspect the image after rendering at full resolution: every label, arrow
direction, feedback loop, and crop. A montage is useful for consistency but
hides 1–10 px overflow and clipped labels.

Keep an existing asset unchanged unless the user explicitly asks to replace
it; otherwise write a new filename. When deriving a variant from an accepted
figure, copy its JSON to the new name and extend the copy - never mutate the
accepted file. Commit the accepted state before a risky change, and when
feedback names one defect, change only that defect; a targeted complaint is
not license to restructure.

Score the render against [`rubric.md`](rubric.md) before shipping - 34
criteria in six sections, most of them measurable against the SVG or the
rendered PNG. Measure rather than eyeball, and report the score with the
failing criteria named. A diagram that renders is not a diagram that is done.
When a diagram passes the rubric but still looks wrong, run the designer
review in [`agents/designer.md`](agents/designer.md) with the PNG path, the
JSON spec path, and a list of anything already being fixed.

To publish an article, convert every SVG it references to PNG:

```bash
python scripts/publish_svgs.py article.md
```

Run the script from the skill directory or use its absolute path. It renders
with Chromium, retains the SVG sources, and rewrites the Markdown only after
every referenced SVG succeeds. Rerun it after editing SVG sources.

Design tokens, SVG component internals, house numbers, and the full audit
checklist live in the repository rather than in this skill:
<https://github.com/alexeygrigorev/diagram-creator/blob/main/docs/design-system.md>
