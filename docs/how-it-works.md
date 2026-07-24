# Renderer Design

The first diagram started as this ASCII workflow:

```text
groom (PM)  ->  implement (engineer)  ->  test (QA)  ->  done
                       ^                        |
                       +--------- FAIL ---------+
```

The PNG needed to preserve the same graph while improving its presentation.
A generative image model could change labels or arrows, so the renderer uses
deterministic drawing commands instead.

## From text to a diagram

The ASCII version contains four nodes, three forward edges, and one feedback
edge.

The JSON specification records those relationships explicitly:

- Nodes appear in their left-to-right display order.
- Forward edges connect the main workflow.
- An edge with `route: "below"` returns to an earlier node.
- The feedback edge has the `FAIL` label.

The renderer calculates equal card widths and gaps from the canvas width.

It draws each part in this order:

1. Create the solid background.
2. Draw the edges, including their arrowheads.
3. Route feedback edges below the cards.
4. Draw the label pill over the feedback line.
5. Draw rounded cards with a small offset shadow.
6. Center each title and optional role inside its card.
7. Save the finished canvas as an optimized PNG.

Drawing edges before cards keeps connection points hidden under the cards.
This produces clean joins without clipping or masking.

## Typography and colors

Pillow loads DejaVu Sans when it's available and falls back to its bundled
default font. Each named palette contains a light card fill, a stronger
outline, and separate title and subtitle colors.

The main arrows use a neutral gray. A successful final edge can use green,
while a feedback loop can use red. These colors reinforce the flow without
changing its meaning.

## Reproduce the example

Run:

```bash
uv run diagram-creator examples/agent-workflow.json examples/agent-workflow.png
```

The command reads the JSON, validates every node and edge reference, renders
the 1440 by 360 canvas, and writes
[`examples/agent-workflow.png`](../examples/agent-workflow.png).
