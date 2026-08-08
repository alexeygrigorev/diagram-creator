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


def ring_spec(width, height, *, count=5, margin=None):
    layout = {"type": "ring", "card_width": 220, "card_height": 90}
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
    assert 'vector-effect="non-scaling-stroke"' in svg


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
    database_symbol = svg.split('<symbol id="icon-database"', 1)[1].split("</symbol>", 1)[0]
    assert database_symbol.count('vector-effect="non-scaling-stroke"') == 2

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
    assert user_symbol.count('vector-effect="non-scaling-stroke"') == 2


def test_renders_a_five_node_ring_as_svg(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "title": "Continuous FAQ loop",
            "canvas": {"width": 940, "height": 800},
            "layout": {"type": "ring", "card_width": 260, "card_height": 100},
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
    assert 'width="940" height="800"' in svg
    centers = ring_card_centers(svg, 260, 100)
    assert len(centers) == 5
    center_x, center_y = ring_center(centers)
    radii = [math.hypot(x - center_x, y - center_y) for x, y in centers]
    assert max(radii) - min(radii) < 0.5
    # The first card sits at the top of the circle and the rest follow clockwise.
    assert centers[0] == pytest.approx((center_x, center_y - radii[0]), abs=0.5)
    assert ring_angles(centers, center_x, center_y) == pytest.approx([72] * 5, abs=0.5)
    # Connectors follow the ring itself, except where it only grazes a corner.
    arcs = re.findall(r'<path class="edge" d="M[-\d. ]+A([\d.]+) ([\d.]+) 0 0 1', svg)
    assert len(arcs) == 4
    assert all(float(x) == pytest.approx(radii[0], abs=0.5) for arc in arcs for x in arc)
    assert '<symbol id="icon-database"' in svg
    assert ">@</text>" in svg
    assert 'textLength="188"' in svg
    assert "Each failure improves the data" in svg


def test_ring_layout_joins_bottom_cards_without_sagging_under_them(tmp_path):
    spec = ring_spec(940, 800)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    # The circle dips below two cards that straddle the bottom, so their connector
    # runs between their facing sides instead of arcing past the corners.
    straight = re.findall(r'<path class="edge" d="M([-\d.]+) ([-\d.]+)L([-\d.]+) ([-\d.]+)"', svg)
    assert len(straight) == 1
    start_x, start_y, end_x, end_y = (float(value) for value in straight[0])
    bottom = sorted(ring_card_centers(svg, 220, 90), key=lambda point: -point[1])[:2]
    assert start_y == pytest.approx(bottom[0][1], abs=0.5)
    assert end_y == pytest.approx(bottom[0][1], abs=0.5)
    assert min(point[0] for point in bottom) < end_x < start_x < max(point[0] for point in bottom)


def test_center_detail_sits_clear_of_the_annotation_circle(tmp_path):
    spec = ring_spec(940, 800)
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
    spec = ring_spec(940, 800)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    svg = output.read_text()
    center_x, center_y = ring_center(ring_card_centers(svg, 220, 90))
    annotation = re.search(r'<circle class="center-annotation" cx="([-\d.]+)" cy="([-\d.]+)"', svg)
    assert annotation is not None
    assert (float(annotation.group(1)), float(annotation.group(2))) == pytest.approx(
        (center_x, center_y), abs=0.5
    )


@pytest.mark.parametrize("count", [3, 4, 6, 7])
def test_ring_layout_supports_other_node_counts(count, tmp_path):
    spec = ring_spec(940, 940, count=count)
    output = tmp_path / "loop.svg"

    render_diagram(spec, output)

    centers = ring_card_centers(output.read_text(), 220, 90)
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
        spec = ring_spec(940, 800, margin=margin)
        output = tmp_path / f"loop-{margin}.svg"
        render_diagram(spec, output)
        centers = ring_card_centers(output.read_text(), 220, 90)
        center_x, center_y = ring_center(centers)
        return math.hypot(centers[0][0] - center_x, centers[0][1] - center_y)

    assert radius(120) < radius(40)


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
    assert '<text class="node-subtitle icon-copy" x="56"' in svg


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
    icon_y = float(re.search(r'<use [^>]*y="([-\d.]+)"', card).group(1))
    subtitle_y = float(
        re.search(r'class="node-subtitle[^"]*" x="[-\d.]+" y="([-\d.]+)"', card).group(1)
    )
    # The icon anchors the left margin, so the subtitle starts there too.
    assert '<text class="node-subtitle icon-copy" x="16"' in card
    assert '<use href="#icon-document" x="16"' in card
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
    assert "icon-copy" not in card


def test_long_subtitle_is_fitted_to_the_card(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "manual", "card_width": 200, "card_height": 110},
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
    assert 'class="node-subtitle" x="100" y="76" textLength="168"' in card


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
