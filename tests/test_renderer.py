import json
import math
import re
from pathlib import Path

import pytest
from PIL import Image

from diagram_creator.cli import main
from diagram_creator.renderer import render_diagram
from diagram_creator.spec import DiagramSpec, SpecError, load_spec


EXAMPLE_SPECS = tuple(sorted(Path("examples").glob("*.json")))
NODE_TRANSFORM = re.compile(r'<g class="node[^"]*" transform="translate\(([-\d.]+) ([-\d.]+)\)"')
STEP_EDGE = re.compile(
    r'<path class="edge" d="M([-\d.]+) ([-\d.]+)H[-\d.]+'
    r"Q([-\d.]+) [-\d.]+ [-\d.]+ [-\d.]+V([-\d.]+)\""
)


def ring_spec(width, height, *, count=5, margin=None, card=(170, 140)):
    layout = {"type": "ring", "card_width": card[0], "card_height": card[1]}
    if margin is not None:
        layout["margin"] = margin
    return DiagramSpec.from_dict(
        {
            "canvas": {"width": width, "height": height},
            "layout": layout,
            "nodes": [{"id": f"step-{index}", "title": f"Step {index}"} for index in range(count)],
            "edges": [
                {"from": f"step-{index}", "to": f"step-{(index + 1) % count}", "route": "ring"}
                for index in range(count)
            ],
            "center": {"title": "LOOP", "detail": "Each round tells you what to fix"},
        }
    )


def ring_card_centers(svg, card_width, card_height):
    return [
        (float(x) + card_width / 2, float(y) + card_height / 2)
        for x, y in NODE_TRANSFORM.findall(svg)
    ]


def ring_center(centers):
    """Evenly spaced points on a circle average out to its center."""
    return (
        sum(x for x, _ in centers) / len(centers),
        sum(y for _, y in centers) / len(centers),
    )


def ring_angles(centers, center_x, center_y):
    """Clockwise degrees between each pair of neighboring cards."""
    bearings = [math.degrees(math.atan2(x - center_x, center_y - y)) % 360 for x, y in centers]
    return [
        (bearings[(index + 1) % len(bearings)] - bearing) % 360
        for index, bearing in enumerate(bearings)
    ]


def staircase_spec(width=900, height=520, *, count=4, direction=None):
    layout = {"type": "staircase", "card_width": 220, "card_height": 90}
    if direction is not None:
        layout["direction"] = direction
    return DiagramSpec.from_dict(
        {
            "canvas": {"width": width, "height": height},
            "layout": layout,
            "nodes": [{"id": f"step-{index}", "title": f"Step {index}"} for index in range(count)],
            "edges": [
                {"from": f"step-{index}", "to": f"step-{index + 1}"} for index in range(count - 1)
            ],
        }
    )


def staircase_cards(svg):
    return [(float(x), float(y)) for x, y in NODE_TRANSFORM.findall(svg)]


def workflow_spec():
    return DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "plan", "title": "Plan", "subtitle": "PM", "color": "purple"},
                {"id": "build", "title": "Build", "subtitle": "Engineer", "color": "blue"},
                {"id": "test", "title": "Test", "subtitle": "QA", "color": "amber"},
            ],
            "edges": [
                {"from": "plan", "to": "build"},
                {"from": "build", "to": "test"},
                {
                    "from": "test",
                    "to": "build",
                    "label": "FAIL",
                    "color": "red",
                    "route": "below",
                },
            ],
        }
    )


def test_renders_a_png_at_the_requested_size(tmp_path):
    output = tmp_path / "diagram.png"

    render_diagram(workflow_spec(), output, width=900, height=320)

    with Image.open(output) as image:
        assert image.format == "PNG"
        assert image.size == (900, 320)
        assert image.mode == "RGB"


def test_cli_renders_a_json_spec(tmp_path):
    source = tmp_path / "diagram.json"
    output = tmp_path / "diagram.png"
    source.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "one", "title": "One"},
                    {"id": "two", "title": "Two", "color": "green"},
                ],
                "edges": [{"from": "one", "to": "two", "color": "green"}],
            }
        )
    )

    assert main([str(source), str(output)]) == 0
    assert output.exists()


def test_renders_a_bidirectional_edge_with_two_arrowheads(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "frontend", "title": "Frontend"},
                {"id": "contract", "title": "OpenAPI"},
            ],
            "edges": [
                {
                    "from": "frontend",
                    "to": "contract",
                    "color": "purple",
                    "bidirectional": True,
                }
            ],
        }
    )
    output = tmp_path / "bidirectional.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert 'id="arrow-start-purple"' in svg
    assert 'marker-start="url(#arrow-start-purple)"' in svg
    assert 'marker-end="url(#arrow-purple)"' in svg


def test_grid_layout_uses_equal_gutters_between_variable_width_nodes(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "canvas": {"width": 880, "height": 400},
            "layout": {
                "type": "grid",
                "card_width": 240,
                "card_height": 110,
                "column_gap": 80,
                "column_width": 240,
                "row_height": 112,
            },
            "nodes": [
                {
                    "id": "frontend",
                    "title": "Frontend",
                    "icon": "browser",
                    "variant": "icon",
                    "row": 0,
                    "column": 0,
                },
                {"id": "contract", "title": "OpenAPI", "row": 0, "column": 1},
                {"id": "backend", "title": "Backend", "row": 0, "column": 2},
            ],
            "edges": [
                {"from": "frontend", "to": "contract"},
                {"from": "contract", "to": "backend"},
            ],
        }
    )
    output = tmp_path / "grid.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert 'transform="translate(40 144)"' in svg
    assert 'transform="translate(320 145)"' in svg
    assert 'transform="translate(640 145)"' in svg


def test_renders_browser_and_websocket_symbols(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "browser", "title": "Browser", "icon": "browser"},
                {"id": "socket", "title": "WebSocket", "icon": "websocket"},
            ],
            "edges": [{"from": "browser", "to": "socket"}],
        }
    )
    output = tmp_path / "icons.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert '<symbol id="icon-browser" viewBox="0 0 32 22">' in svg
    assert '<symbol id="icon-websocket"' in svg
    assert 'href="#icon-browser"' in svg
    assert 'href="#icon-websocket"' in svg


def test_renders_an_icon_node_with_its_label_but_without_a_card(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual", "card_width": 220, "card_height": 100},
            "nodes": [
                {
                    "id": "person",
                    "title": "User",
                    "icon": "user",
                    "variant": "icon",
                    "icon_size": 48,
                    "x": 40,
                    "y": 60,
                    "width": 80,
                    "height": 56,
                },
                {"id": "app", "title": "App", "x": 300, "y": 40},
            ],
            "edges": [{"from": "person", "to": "app"}],
        }
    )
    output = tmp_path / "icon-node.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    icon_group = svg.split('<g class="node-icon-only', 1)[1].split("</g>", 1)[0]
    assert 'href="#icon-user"' in icon_group
    assert 'width="48" height="48"' in icon_group
    assert ">User</text>" in icon_group
    assert "<rect" not in icon_group


def test_renders_an_icon_node_without_a_visible_label(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual"},
            "nodes": [
                {
                    "id": "person",
                    "title": "User",
                    "icon": "user",
                    "variant": "icon",
                    "show_label": False,
                    "x": 40,
                    "y": 60,
                    "width": 80,
                    "height": 56,
                },
                {"id": "app", "title": "App", "x": 300, "y": 40},
            ],
            "edges": [{"from": "person", "to": "app"}],
        }
    )
    output = tmp_path / "unlabeled-icon-node.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    icon_group = svg.split('<g class="node-icon-only', 1)[1].split("</g>", 1)[0]
    assert 'href="#icon-user"' in icon_group
    assert ">User</text>" not in icon_group


def test_uses_reusable_sizes_for_standalone_browser_and_database_icons(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual"},
            "nodes": [
                {
                    "id": "browser",
                    "title": "Frontend",
                    "icon": "browser",
                    "variant": "icon",
                    "x": 40,
                    "y": 60,
                },
                {
                    "id": "database",
                    "title": "SQLite",
                    "icon": "database",
                    "variant": "icon",
                    "x": 300,
                    "y": 88,
                },
            ],
            "edges": [{"from": "browser", "to": "database"}],
        }
    )
    output = tmp_path / "semantic-icon-sizes.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert 'href="#icon-browser" x="0" y="0" width="160" height="112"' in svg
    assert 'href="#icon-database" x="0" y="0" width="84" height="84"' in svg
    # Stroke weight scales with the glyph everywhere, so one value reads the same
    # in a card and standalone. A fixed device width would not.
    database_symbol = svg.split('<symbol id="icon-database"', 1)[1].split("</symbol>", 1)[0]
    assert "non-scaling-stroke" not in database_symbol

    user_spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "user", "title": "User", "icon": "user"},
                {"id": "app", "title": "App"},
            ],
            "edges": [{"from": "user", "to": "app"}],
        }
    )
    user_output = tmp_path / "user-stroke.svg"
    render_diagram(user_spec, user_output)
    user_symbol = (
        user_output.read_text().split('<symbol id="icon-user"', 1)[1].split("</symbol>", 1)[0]
    )
    assert "non-scaling-stroke" not in user_symbol


def test_renders_a_five_node_ring_as_svg(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "title": "Continuous FAQ loop",
            "canvas": {"width": 940, "height": 947},
            "layout": {"type": "ring", "card_width": 260, "card_height": 247},
            "nodes": [
                {
                    "id": "contribute",
                    "title": "Student contributions",
                    "subtitle": "Issues improve the FAQ dataset",
                    "color": "blue",
                    "icon": "issue",
                },
                {
                    "id": "curate",
                    "title": "Curate discussions",
                    "subtitle": "Slack → reviewed FAQ records",
                    "color": "purple",
                    "icon": "message",
                },
                {
                    "id": "deploy",
                    "title": "Index + deploy",
                    "subtitle": "Fresh dataset ships with Lambda",
                    "color": "green",
                    "icon": "database",
                },
                {
                    "id": "answer",
                    "title": "Answer questions",
                    "subtitle": "Au-Tomator responds in Slack",
                    "color": "purple",
                    "icon": "mention",
                },
                {
                    "id": "evaluate",
                    "title": "Evaluate failures",
                    "subtitle": "Missing answers reveal next fixes",
                    "color": "red",
                    "icon": "warning",
                },
            ],
            "edges": [
                {"from": "contribute", "to": "curate", "route": "ring"},
                {"from": "curate", "to": "deploy", "route": "ring"},
                {"from": "deploy", "to": "answer", "route": "ring"},
                {"from": "answer", "to": "evaluate", "route": "ring"},
                {"from": "evaluate", "to": "contribute", "route": "ring"},
            ],
            "center": {
                "title": "CURATION",
                "subtitle": "LOOP",
                "detail": "Each failure improves the data",
            },
        }
    )
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert 'width="940" height="947"' in svg
    centers = ring_card_centers(svg, 260, 247)
    assert len(centers) == 5
    center_x, center_y = ring_center(centers)
    radii = [math.hypot(x - center_x, y - center_y) for x, y in centers]
    assert max(radii) - min(radii) < 0.5
    # The first card sits at the top of the circle and the rest follow clockwise.
    assert centers[0] == pytest.approx((center_x, center_y - radii[0]), abs=0.5)
    assert ring_angles(centers, center_x, center_y) == pytest.approx([72] * 5, abs=0.5)
    # Connectors follow the ring itself, except where it only grazes a corner.
    arcs = re.findall(r'<path class="edge" d="M[-\d. ]+A([\d.]+) ([\d.]+) 0 0 1', svg)
    assert len(arcs) == 5
    assert all(float(arc[0]) == pytest.approx(radii[0], abs=0.5) for arc in arcs)
    assert '<symbol id="icon-database"' in svg
    assert ">@</text>" in svg
    assert 'class="node-title icon-copy"' in svg  # titles carry an explicit, scalable size
    assert "Each failure improves the data" in svg


def ring_arcs(svg):
    return [
        tuple(float(v) for v in edge)
        for edge in re.findall(
            r'<path class="edge" d="M([-\d.]+) ([-\d.]+)A([\d.]+) [\d.]+ 0 0 1 ([-\d.]+) ([-\d.]+)"',
            svg,
        )
    ]


def test_ring_connectors_are_all_the_same_length(tmp_path):
    # Every connector spans one shared angle centred in its slot, so equal
    # arrows are structural - no card size can produce a ring of mixed lengths.
    output = tmp_path / "loop.svg"
    for card in ((170, 140), (150, 150), (190, 130)):
        render_diagram(ring_spec(726, 673, card=card), output)
        arcs = ring_arcs(output.read_text())
        chords = [math.hypot(a[3] - a[0], a[4] - a[1]) for a in arcs]
        assert max(chords) - min(chords) < 0.5, card
        assert max(a[2] for a in arcs) - min(a[2] for a in arcs) < 0.01, card


def test_ring_connectors_reach_the_cards_they_join(tmp_path):
    spec = ring_spec(726, 673)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    arcs = ring_arcs(svg)
    assert len(arcs) == 5
    boxes = [
        (x, y, x + 170, y + 140) for x, y in (map(float, n) for n in NODE_TRANSFORM.findall(svg))
    ]

    def off_card(point):
        """How far a point sits from the nearest card's outline."""
        return min(
            max(x0 - point[0], point[0] - x1, y0 - point[1], point[1] - y1, 0)
            + max(min(point[0] - x0, x1 - point[0], point[1] - y0, y1 - point[1]), 0)
            for x0, y0, x1, y1 in boxes
        )

    # One shared sweep means the ends needing least room stop a little short;
    # the renderer bounds how far, so no connector visibly floats.
    for start_x, start_y, _, end_x, end_y in arcs:
        assert off_card((start_x, start_y)) <= 42
        assert off_card((end_x, end_y)) <= 42


def test_block_icons_fill_a_square_card_better_than_inline(tmp_path):
    # A ring needs near-square cards for equal connectors, and a square card
    # holding one short row is mostly empty. Stacking the icon over the title
    # roughly doubles the content height, which is what fills it.
    def content_height(position):
        spec = DiagramSpec.from_dict(
            {
                "canvas": {"width": 812, "height": 770},
                "layout": {
                    "type": "ring",
                    "card_width": 180,
                    "card_height": 165,
                    "font_scale": 1.35,
                    "icon_position": position,
                },
                "nodes": [
                    {"id": f"s{index}", "title": "Build", "icon": "github", "eyebrow": "STEP"}
                    for index in range(5)
                ],
                "edges": [
                    {"from": f"s{index}", "to": f"s{(index + 1) % 5}", "route": "ring"}
                    for index in range(5)
                ],
            }
        )
        output = tmp_path / f"{position}.svg"
        render_diagram(spec, output)
        card = output.read_text().split('<g class="node', 1)[1].split("</g>", 1)[0]
        tops = [float(v) for v in re.findall(r'<text[^>]* y="([-\d.]+)"', card)]
        icon = re.search(r'<use [^>]*y="([-\d.]+)"[^>]*height="([\d.]+)"', card)
        return max(tops + [float(icon.group(1)) + float(icon.group(2))]) - min(
            tops + [float(icon.group(1))]
        )

    assert content_height("block") > content_height("inline") * 1.3
    assert content_height("block") / 165 > 0.5  # a square card is otherwise mostly empty


def test_ring_rejects_a_card_its_connectors_cannot_reach(tmp_path):
    # A very flat card covers a wide angle at the sides and a narrow one at the
    # top, so one shared sweep leaves the narrow ends far short. The renderer
    # refuses rather than shipping connectors that visibly float.
    with pytest.raises(SpecError, match="short of its card"):
        render_diagram(ring_spec(1040, 1010, card=(220, 55)), tmp_path / "loop.svg")


def test_center_detail_sits_clear_of_the_annotation_circle(tmp_path):
    spec = ring_spec(726, 673)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    circle = re.search(
        r'class="center-annotation" cx="([-\d.]+)" cy="([-\d.]+)" r="([-\d.]+)"', svg
    )
    detail = re.search(r'<text class="center-detail" x="[-\d.]+" y="([-\d.]+)"', svg)
    assert circle is not None and detail is not None
    assert float(detail.group(1)) > float(circle.group(2)) + float(circle.group(3))


def test_ring_layout_centers_the_annotation_on_the_circle(tmp_path):
    spec = ring_spec(726, 673)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    center_x, center_y = ring_center(ring_card_centers(svg, 170, 140))
    annotation = re.search(r'<circle class="center-annotation" cx="([-\d.]+)" cy="([-\d.]+)"', svg)
    assert annotation is not None
    assert (float(annotation.group(1)), float(annotation.group(2))) == pytest.approx(
        (center_x, center_y), abs=0.5
    )


@pytest.mark.parametrize("count", [3, 4, 6, 7])
def test_ring_layout_supports_other_node_counts(count, tmp_path):
    output = tmp_path / "loop.svg"
    # Cards small relative to the radius keep the connectors even at any count;
    # the shape that does so at a given count is otherwise count-dependent.
    render_diagram(ring_spec(1120, 1100, count=count, card=(150, 140)), output)

    centers = ring_card_centers(output.read_text(), 150, 140)
    assert len(centers) == count
    center_x, center_y = ring_center(centers)
    radii = [math.hypot(x - center_x, y - center_y) for x, y in centers]
    assert max(radii) - min(radii) < 0.5
    assert ring_angles(centers, center_x, center_y) == pytest.approx([360 / count] * count, abs=0.5)


def test_ring_layout_rejects_a_canvas_that_overlaps_cards(tmp_path):
    spec = ring_spec(1000, 300)

    with pytest.raises(SpecError, match="ring layout cards overlap"):
        render_diagram(spec, tmp_path / "loop.svg")


def test_ring_layout_margin_shrinks_the_circle(tmp_path):
    def radius(margin):
        spec = ring_spec(900, 840, margin=margin)
        output = tmp_path / f"loop-{margin}.svg"
        render_diagram(spec, output)
        centers = ring_card_centers(output.read_text(), 170, 140)
        center_x, center_y = ring_center(centers)
        return math.hypot(centers[0][0] - center_x, centers[0][1] - center_y)

    assert radius(120) < radius(40)


def test_staircase_layout_steps_down_one_card_at_a_time(tmp_path):
    output = tmp_path / "stairs.svg"

    render_diagram(staircase_spec(), output)

    cards = staircase_cards(output.read_text())
    assert len(cards) == 4
    advances_x = [later[0] - earlier[0] for earlier, later in zip(cards, cards[1:])]
    advances_y = [later[1] - earlier[1] for earlier, later in zip(cards, cards[1:])]
    # Every tread and every riser is the same size, so the cascade reads as one shape.
    assert max(advances_x) - min(advances_x) < 0.01
    assert max(advances_y) - min(advances_y) < 0.01
    # Cards overlap sideways but never share a row.
    assert 0 < advances_x[0] < 220
    assert advances_y[0] >= 90
    # The whole staircase is centered on the canvas.
    assert cards[0][0] == pytest.approx(900 - (cards[-1][0] + 220), abs=0.5)
    assert cards[0][1] == pytest.approx(520 - (cards[-1][1] + 90), abs=0.5)


def test_staircase_layout_can_climb_instead_of_descend(tmp_path):
    output = tmp_path / "stairs.svg"

    render_diagram(staircase_spec(direction="ascending"), output)

    cards = staircase_cards(output.read_text())
    assert [card[0] for card in cards] == sorted(card[0] for card in cards)
    assert [card[1] for card in cards] == sorted((card[1] for card in cards), reverse=True)


@pytest.mark.parametrize("direction", ["descending", "ascending"])
def test_staircase_connectors_are_one_elbow_repeated(direction, tmp_path):
    output = tmp_path / "stairs.svg"

    render_diagram(staircase_spec(direction=direction), output)

    svg = output.read_text()
    cards = staircase_cards(svg)
    elbows = STEP_EDGE.findall(svg)
    assert len(elbows) == 3
    for index, elbow in enumerate(elbows):
        start_x, start_y, turn_x, end_y = (float(value) for value in elbow)
        source, target = cards[index], cards[index + 1]
        # Out of the source's right edge, turning halfway across the tread, into
        # the top edge below or the bottom edge above.
        assert (start_x, start_y) == pytest.approx((source[0] + 220, source[1] + 45), abs=0.01)
        assert turn_x == pytest.approx((source[0] + target[0] + 440) / 2, abs=0.01)
        assert end_y == pytest.approx(target[1] if direction == "descending" else target[1] + 90)
        assert target[0] <= turn_x <= target[0] + 220
    runs = [(float(e[2]) - float(e[0]), abs(float(e[3]) - float(e[1]))) for e in elbows]
    assert max(runs) == pytest.approx(min(runs), abs=0.01)


def test_staircase_rejects_a_canvas_that_cannot_hold_the_cascade(tmp_path):
    spec = staircase_spec(700, 400, count=5)

    with pytest.raises(SpecError, match="too small for this staircase"):
        render_diagram(spec, tmp_path / "stairs.svg")


def test_step_route_joins_two_cards_outside_a_staircase(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "canvas": {"width": 800, "height": 400},
            "layout": {"type": "grid", "card_width": 220, "card_height": 90},
            "nodes": [
                {"id": "one", "title": "One", "row": 0, "column": 0},
                {"id": "two", "title": "Two", "row": 1, "column": 1},
            ],
            "edges": [{"from": "one", "to": "two", "route": "step"}],
        }
    )
    output = tmp_path / "step.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    cards = staircase_cards(svg)
    elbow = STEP_EDGE.search(svg)
    assert elbow is not None
    assert float(elbow.group(4)) == pytest.approx(cards[1][1], abs=0.01)


@pytest.mark.parametrize("source", EXAMPLE_SPECS, ids=lambda path: path.stem)
def test_example_never_stretches_or_squeezes_type(source, tmp_path):
    output = tmp_path / source.with_suffix(".svg").name

    render_diagram(load_spec(source), output)

    # Every glyph renders at its natural width. Fitting copy is done by choosing
    # a size and wrapping, never by distorting letterforms.
    svg = output.read_text()
    assert "textLength" not in svg
    assert "lengthAdjust" not in svg
    assert "font-stretch" not in svg


def test_titles_share_one_size_rather_than_being_squeezed(tmp_path):
    # "Interview" is far wider than "Apply", so a per-card fit would squeeze it
    # while leaving its neighbour untouched - visibly different letterforms.
    spec = DiagramSpec.from_dict(
        {
            "canvas": {"width": 726, "height": 673},
            "layout": {"type": "ring", "card_width": 170, "card_height": 140},
            "nodes": [
                {"id": "a", "title": "Interview", "icon": "message"},
                {"id": "b", "title": "Apply", "icon": "document"},
                {"id": "c", "title": "Build", "icon": "github"},
                {"id": "d", "title": "Network", "icon": "user"},
                {"id": "e", "title": "Reflect", "icon": "search"},
            ],
            "edges": [
                {"from": x, "to": y, "route": "ring"}
                for x, y in (("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a"))
            ],
        }
    )
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert "textLength" not in svg
    sizes = set(re.findall(r'class="node-title[^"]*"[^>]*font-size="(\d+)"', svg))
    assert len(sizes) == 1

    # And the size chosen is the largest that leaves every title undistorted.
    from diagram_creator.renderer import TITLE_WEIGHT, _text_width

    size = int(sizes.pop())
    for title in ("Interview", "Apply", "Build", "Network", "Reflect"):
        assert _text_width(title, size, TITLE_WEIGHT) <= 170 - 32


@pytest.mark.parametrize("source", EXAMPLE_SPECS, ids=lambda path: path.stem)
def test_checked_in_example_svg_matches_its_json(source, tmp_path):
    output = tmp_path / source.with_suffix(".svg").name

    render_diagram(load_spec(source), output)

    assert output.read_bytes() == source.with_suffix(".svg").read_bytes()


def test_renders_a_plain_node_without_a_card(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {
                    "id": "stage",
                    "title": "Prototype",
                    "subtitle": "Test the experience",
                    "icon": "number-1",
                    "variant": "plain",
                    "color": "blue",
                },
                {"id": "app", "title": "App", "subtitle": "Frontend"},
            ],
            "edges": [{"from": "stage", "to": "app"}],
        }
    )
    output = tmp_path / "plain.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert '<symbol id="icon-number-1"' in svg
    assert svg.count("<rect") == 2  # the canvas background and the one real card
    assert 'class="node node-plain node-blue"' in svg
    assert 'filter="url(#shadow)">\n    <rect' in svg  # only the card keeps the shadow
    assert '<text class="node-subtitle" x="129.6"' in svg  # centered like every other card


def test_card_with_an_icon_shares_one_text_axis_and_centers_its_block(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual", "card_width": 240, "card_height": 110},
            "nodes": [
                {
                    "id": "docs",
                    "title": "Docs",
                    "subtitle": "Published guides",
                    "icon": "document",
                    "x": 40,
                    "y": 40,
                },
                {"id": "app", "title": "App", "x": 400, "y": 40},
            ],
            "edges": [{"from": "docs", "to": "app"}],
        }
    )
    output = tmp_path / "card.svg"

    render_diagram(spec, output)

    card = output.read_text().split('transform="translate(40 40)"', 1)[1].split("</g>", 1)[0]
    icon_x, icon_y = (
        float(v) for v in re.search(r'<use [^>]*x="([-\d.]+)" y="([-\d.]+)"', card).groups()
    )
    title_x = float(re.search(r'class="node-title[^"]*" x="([-\d.]+)"', card).group(1))
    subtitle_x, subtitle_y = (
        float(v)
        for v in re.search(r'class="node-subtitle[^"]*" x="([-\d.]+)" y="([-\d.]+)"', card).groups()
    )
    # Icon and title form one group centered on the card, so both lines share
    # the card's center axis and neither leaves the far half of the card empty.
    from diagram_creator.renderer import (
        ICON_GUTTER,
        ICON_INK,
        ICON_SIZE,
        TITLE_SIZE,
        TITLE_WEIGHT,
        _text_width,
    )

    # Centred on ink, not on the icon's box: the document glyph fills barely half
    # its box, so a box-centred group sits visibly left.
    ink_start, ink_end = ICON_INK["document"]
    ink_left = icon_x + ink_start * ICON_SIZE
    group_end = title_x + _text_width("Docs", TITLE_SIZE, TITLE_WEIGHT)
    assert (ink_left + group_end) / 2 == pytest.approx(240 / 2, abs=0.5)
    assert subtitle_x == pytest.approx(240 / 2, abs=0.5)
    assert title_x == pytest.approx(icon_x + ink_end * ICON_SIZE + ICON_GUTTER, abs=0.5)
    # Icon top through subtitle descender is centered on the 110px card.
    assert (icon_y + subtitle_y + 4) / 2 == pytest.approx(55, abs=2)


def test_card_without_an_icon_keeps_both_lines_centered(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "plan", "title": "Plan", "subtitle": "PM"},
                {"id": "app", "title": "App"},
            ],
            "edges": [{"from": "plan", "to": "app"}],
        }
    )
    output = tmp_path / "card.svg"

    render_diagram(spec, output)

    card = output.read_text().split('<g class="node node-blue"', 1)[1].split("</g>", 1)[0]
    assert '<text class="node-title" x=' in card
    assert '<text class="node-subtitle" x=' in card
    assert "icon-copy" not in card  # no icon, so the title needs no start anchor


def test_long_subtitle_wraps_instead_of_being_squeezed(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual", "card_width": 200, "card_height": 130},
            "nodes": [
                {
                    "id": "docs",
                    "title": "Docs",
                    "subtitle": "A subtitle far too long for this narrow card",
                    "x": 40,
                    "y": 40,
                },
                {"id": "app", "title": "App", "x": 400, "y": 40},
            ],
            "edges": [{"from": "docs", "to": "app"}],
        }
    )
    output = tmp_path / "card.svg"

    render_diagram(spec, output)

    card = output.read_text().split('transform="translate(40 40)"', 1)[1].split("</g>", 1)[0]
    subtitles = re.findall(r'class="node-subtitle"[^>]*>([^<]+)<', card)
    assert len(subtitles) > 1
    assert " ".join(subtitles) == "A subtitle far too long for this narrow card"
    assert "textLength" not in card  # wrapping means nothing needs compressing


def test_draws_a_dashed_divider_between_grid_rows(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "canvas": {"width": 800, "height": 400},
            "layout": {"type": "grid", "card_width": 220, "card_height": 100},
            "nodes": [
                {"id": "top", "title": "Top", "row": 0, "column": 0},
                {"id": "top_end", "title": "Top end", "row": 0, "column": 1},
                {"id": "bottom", "title": "Bottom", "row": 1, "column": 0},
                {"id": "bottom_end", "title": "Bottom end", "row": 1, "column": 1},
            ],
            "edges": [{"from": "top", "to": "top_end"}],
            "dividers": [{"after_row": 0}],
        }
    )
    output = tmp_path / "dividers.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    assert svg.count('class="divider"') == 1
    assert '<line class="divider" x1="126" y1="200" x2="674" y2="200"/>' in svg
