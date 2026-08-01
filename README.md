# Diagram Creator

Diagram Creator turns a small JSON specification into a polished horizontal
workflow diagram. Labels and arrows stay exactly as specified, while cards and
feedback loops use consistent geometry.

![Agent workflow example](examples/agent-workflow.png)

## Quick start

Install the project and render the included example:

```bash
uv sync --dev
uv run diagram-creator examples/agent-workflow.json examples/agent-workflow.png
```

The command accepts an input JSON file and an output PNG path:

```bash
uv run diagram-creator input.json output.png
```

The default canvas is 1440 by 360 pixels.

Set a different size when the workflow needs more room:

```bash
uv run diagram-creator input.json output.png --width 1800 --height 480
```

## Diagram specification

Define nodes in display order and reference their IDs from each edge:

```json
{
  "nodes": [
    {"id": "groom", "title": "Groom", "subtitle": "PM", "color": "purple"},
    {
      "id": "implement",
      "title": "Implement",
      "subtitle": "Engineer",
      "color": "blue"
    },
    {"id": "test", "title": "Test", "subtitle": "QA", "color": "amber"}
  ],
  "edges": [
    {"from": "groom", "to": "implement"},
    {"from": "implement", "to": "test"},
    {
      "from": "test",
      "to": "implement",
      "label": "FAIL",
      "color": "red",
      "route": "below"
    }
  ]
}
```

Use `route: "forward"` for the main flow and `route: "below"` for a feedback
loop. Nodes and edges share six colors: `purple` / `blue` / `amber` / `green` /
`red` / `gray`.

## Codex skill

The repository includes a reusable skill in
[`skills/diagram-creator`](skills/diagram-creator). Copy that directory into
your Codex skills directory to make it available across projects.

### Publishing SVG diagrams as PNG

While editing an article, keep its image references pointed at SVG files. When
the article is ready to publish, use the skill's publishing script:

```bash
python skills/diagram-creator/scripts/publish_svgs.py \
  path/to/article.md
```

The script finds every local SVG image referenced by the supplied Markdown
file, renders a same-name PNG beside it, and replaces the SVG reference with
the PNG reference. It uses Chromium so filters, fonts, icons, and spacing match
the browser-rendered SVG. It retains the original SVG source and updates the
Markdown only after all images render successfully. Pass multiple Markdown
files to process them together, `--scale 2` for higher-density output, or
`--background transparent` to override the default white PNG background. Run
the same command again to refresh PNGs whose article references were already
published.

## How it works

Read [How the renderer was created](docs/how-it-works.md) for the original
ASCII diagram, the drawing sequence, and the layout decisions.

## Development

Run the checks:

```bash
make lint
make test
```

Python and Pillow render each image, `uv` manages the environment, and pytest
and Ruff check the project.
