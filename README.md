# Diagram Creator

[![tests](https://github.com/alexeygrigorev/diagram-creator/actions/workflows/tests.yml/badge.svg)](https://github.com/alexeygrigorev/diagram-creator/actions/workflows/tests.yml)

Diagram Creator turns a compact JSON specification into a deterministic SVG or
PNG. The same renderer handles horizontal workflows, explicitly positioned
rows and columns, and five-step circular loops with reusable icons.

## Quick start

Install the project and render an example:

```bash
uv sync --dev
uv run diagram-creator examples/faq-curation-loop.json examples/faq-curation-loop.svg
```

Choose the format with the output extension. PNG output is rendered from the
same SVG with Chromium, so both formats use identical layout, fonts, and icons:

```bash
uv run diagram-creator input.json output.svg
uv run diagram-creator input.json output.png
```

Canvas dimensions belong in JSON. `--width` and `--height` can override them
for a one-off render.

## Examples

Each image below is generated from the linked JSON source.

### Horizontal workflow

The default layout evenly spaces a workflow from left to right and can route a
feedback edge below the main flow.

![Horizontal agent workflow with a feedback edge](examples/agent-workflow.png)

[JSON source](examples/agent-workflow.json) · [SVG output](examples/agent-workflow.svg)

### Manual rows and columns

Manual layout gives nodes explicit positions while retaining the same cards,
icons, anchors, and curved connectors.

![Three knowledge sources merging into an index and FAQ assistant](examples/manual-pipeline.png)

[JSON source](examples/manual-pipeline.json) · [SVG output](examples/manual-pipeline.svg)

### Circular improvement loop

Ring layout places five equal cards clockwise and derives mirrored connector
curves automatically.

![FAQ curation and improvement loop](examples/faq-curation-loop.png)

[JSON source](examples/faq-curation-loop.json) · [SVG output](examples/faq-curation-loop.svg)

## Diagram specification

Every diagram has nodes and edges. The original compact form remains valid and
uses a 1440×360 horizontal layout:

```json
{
  "nodes": [
    {"id": "plan", "title": "Plan", "subtitle": "PM", "color": "purple"},
    {"id": "build", "title": "Build", "subtitle": "Engineer", "color": "blue"}
  ],
  "edges": [
    {"from": "plan", "to": "build"},
    {"from": "build", "to": "plan", "label": "FAIL", "color": "red", "route": "below"}
  ]
}
```

Use a ring layout for a five-stage improvement cycle. Nodes are declared
clockwise starting at the top, and the renderer produces symmetric cards and
curves:

```json
{
  "title": "Continuous improvement loop",
  "canvas": {"width": 1100, "height": 550, "background": "#ffffff"},
  "layout": {"type": "ring", "card_width": 260, "card_height": 100},
  "nodes": [
    {"id": "one", "title": "Contribute", "color": "blue", "icon": "issue"},
    {"id": "two", "title": "Curate", "color": "purple", "icon": "message"},
    {"id": "three", "title": "Deploy", "color": "green", "icon": "database"},
    {"id": "four", "title": "Answer", "color": "purple", "icon": "mention"},
    {"id": "five", "title": "Evaluate", "color": "red", "icon": "warning"}
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

The complete source for the diagram above is
[`examples/faq-curation-loop.json`](examples/faq-curation-loop.json).

### Layouts

- `horizontal` places every node in one evenly spaced row.
- `ring` places exactly five equal cards clockwise around a center annotation.
- `manual` uses each node's `x` and `y`; set shared `card_width` and
  `card_height` in `layout`, or override `width` and `height` on a node.

Manual layouts still use reusable cards and icons—the JSON controls placement,
not raw SVG markup:

```json
{
  "canvas": {"width": 900, "height": 500},
  "layout": {"type": "manual", "card_width": 220, "card_height": 100},
  "nodes": [
    {"id": "source", "title": "Sources", "x": 40, "y": 60, "icon": "document"},
    {"id": "index", "title": "Build index", "x": 340, "y": 280, "icon": "settings"}
  ],
  "edges": [
    {
      "from": "source",
      "to": "index",
      "route": "curve",
      "from_anchor": "right",
      "to_anchor": "top",
      "controls": [[300, 110], [450, 190]]
    }
  ]
}
```

### Components and tokens

Node colors are `purple`, `blue`, `amber`, `green`, `red`, and `gray`.
Available icons are `github`, `search`, `database`, `openai`, `issue`,
`document`, `user`, `api`, `settings`, `pull-request`, `rank-fusion`,
`message`, `video`, `sparkles`, `check`, `warning`, `close`, and `mention`.

Cards use one component system: a 16 px inset, 28 px icon viewport, fixed text
axis, centered subtitle, 2 px semantic border, 18 px radius, and a shared
shadow. Long titles are fitted into the available text column automatically.

Edge routes are `forward`, `below`, `straight`, `curve`, and `ring`. Explicit
edges accept `from_anchor` and `to_anchor` values of `left`, `right`, `top`, or
`bottom`. A curve takes exactly two absolute `[x, y]` control points.

## Codex skill

The repository includes a reusable skill in
[`skills/diagram-creator`](skills/diagram-creator). Copy that directory into a
Codex skills directory to make it available across projects.

The skill also contains `scripts/publish_svgs.py`. It renders every local SVG
referenced by a Markdown article as a same-name PNG and changes the article
references only after all renders succeed:

```bash
python skills/diagram-creator/scripts/publish_svgs.py path/to/article.md
```

## Development

Run the checks:

```bash
make lint
make test
```

Read [How the renderer works](docs/how-it-works.md) for the drawing and routing
model.
