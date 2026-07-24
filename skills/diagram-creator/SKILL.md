---
name: diagram-creator
description: Create polished horizontal workflow diagrams as PNG files from compact JSON specifications. Use when Codex needs to turn a process, agent lifecycle, state flow, or ASCII workflow into a deterministic diagram with forward arrows and labeled feedback loops.
---

# Diagram Creator

Create a JSON specification, render it with the CLI, and inspect the PNG.

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
