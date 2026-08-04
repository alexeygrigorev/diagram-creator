import pytest

from diagram_creator.spec import DiagramSpec, SpecError


def test_rejects_an_edge_with_an_unknown_node():
    data = {
        "nodes": [
            {"id": "one", "title": "One"},
            {"id": "two", "title": "Two"},
        ],
        "edges": [{"from": "one", "to": "missing"}],
    }

    with pytest.raises(SpecError, match="unknown target node"):
        DiagramSpec.from_dict(data)


def test_rejects_duplicate_node_ids():
    data = {
        "nodes": [
            {"id": "same", "title": "One"},
            {"id": "same", "title": "Two"},
        ],
        "edges": [],
    }

    with pytest.raises(SpecError, match="unique"):
        DiagramSpec.from_dict(data)


def test_parses_ring_layout_icons_canvas_and_center_annotation():
    data = {
        "title": "Improvement loop",
        "description": "Five steps improve one another.",
        "canvas": {"width": 1100, "height": 550, "background": "#ffffff"},
        "layout": {"type": "ring", "card_width": 260, "card_height": 100},
        "nodes": [
            {"id": "one", "title": "One", "icon": "issue"},
            {"id": "two", "title": "Two", "icon": "message"},
            {"id": "three", "title": "Three", "icon": "database"},
            {"id": "four", "title": "Four", "icon": "mention"},
            {"id": "five", "title": "Five", "icon": "warning"},
        ],
        "edges": [
            {"from": "one", "to": "two", "route": "ring"},
            {"from": "two", "to": "three", "route": "ring"},
        ],
        "center": {"title": "CURATION", "subtitle": "LOOP", "detail": "Keep improving"},
    }

    spec = DiagramSpec.from_dict(data)

    assert spec.canvas.width == 1100
    assert spec.layout.type == "ring"
    assert spec.nodes[3].icon == "mention"
    assert spec.center is not None
    assert spec.center.detail == "Keep improving"


def test_manual_layout_requires_coordinates_on_every_node():
    data = {
        "layout": {"type": "manual"},
        "nodes": [
            {"id": "one", "title": "One", "x": 10, "y": 20},
            {"id": "two", "title": "Two"},
        ],
        "edges": [],
    }

    with pytest.raises(SpecError, match="requires x and y"):
        DiagramSpec.from_dict(data)


def test_grid_layout_requires_a_unique_row_and_column_for_every_node():
    data = {
        "layout": {"type": "grid"},
        "nodes": [
            {"id": "one", "title": "One", "row": 0, "column": 0},
            {"id": "two", "title": "Two", "row": 0, "column": 0},
        ],
        "edges": [],
    }

    with pytest.raises(SpecError, match="unique cell"):
        DiagramSpec.from_dict(data)


def test_parses_explicit_grid_column_width_and_row_height():
    spec = DiagramSpec.from_dict(
        {
            "layout": {
                "type": "grid",
                "column_width": 240,
                "row_height": 112,
            },
            "nodes": [
                {"id": "one", "title": "One", "row": 0, "column": 0},
                {"id": "two", "title": "Two", "row": 0, "column": 1},
            ],
            "edges": [],
        }
    )

    assert spec.layout.column_width == 240
    assert spec.layout.row_height == 112


def test_curve_route_requires_two_control_points():
    data = {
        "nodes": [
            {"id": "one", "title": "One"},
            {"id": "two", "title": "Two"},
        ],
        "edges": [{"from": "one", "to": "two", "route": "curve"}],
    }

    with pytest.raises(SpecError, match="requires two control points"):
        DiagramSpec.from_dict(data)


def test_parses_a_bidirectional_edge():
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "one", "title": "One"},
                {"id": "two", "title": "Two"},
            ],
            "edges": [{"from": "one", "to": "two", "bidirectional": True}],
        }
    )

    assert spec.edges[0].bidirectional is True


def test_parses_browser_and_websocket_icons():
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "browser", "title": "Browser", "icon": "browser"},
                {"id": "socket", "title": "WebSocket", "icon": "websocket"},
            ],
            "edges": [{"from": "browser", "to": "socket"}],
        }
    )

    assert [node.icon for node in spec.nodes] == ["browser", "websocket"]


def test_icon_variant_requires_an_icon():
    data = {
        "nodes": [
            {"id": "person", "title": "Person", "variant": "icon"},
            {"id": "app", "title": "App"},
        ],
        "edges": [{"from": "person", "to": "app"}],
    }

    with pytest.raises(SpecError, match="icon variant requires an icon"):
        DiagramSpec.from_dict(data)


def test_icon_variant_can_hide_its_visible_label():
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {
                    "id": "person",
                    "title": "Person",
                    "icon": "user",
                    "variant": "icon",
                    "show_label": False,
                },
                {"id": "app", "title": "App"},
            ],
            "edges": [{"from": "person", "to": "app"}],
        }
    )

    assert spec.nodes[0].show_label is False


def test_parses_a_custom_standalone_icon_size():
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {
                    "id": "browser",
                    "title": "Browser",
                    "icon": "browser",
                    "variant": "icon",
                    "icon_size": 112,
                },
                {"id": "app", "title": "App"},
            ],
            "edges": [{"from": "browser", "to": "app"}],
        }
    )

    assert spec.nodes[0].icon_size == 112


def test_parses_row_dividers_for_a_grid():
    spec = DiagramSpec.from_dict(
        {
            "layout": {"type": "grid"},
            "nodes": [
                {"id": "first", "title": "First", "row": 0, "column": 0},
                {"id": "second", "title": "Second", "row": 1, "column": 0},
            ],
            "edges": [],
            "dividers": [{"after_row": 0}],
        }
    )

    assert [divider.after_row for divider in spec.dividers] == [0]


def test_rejects_a_divider_below_the_last_row():
    data = {
        "layout": {"type": "grid"},
        "nodes": [
            {"id": "first", "title": "First", "row": 0, "column": 0},
            {"id": "second", "title": "Second", "row": 1, "column": 0},
        ],
        "edges": [],
        "dividers": [{"after_row": 1}],
    }

    with pytest.raises(SpecError, match="has no row below it"):
        DiagramSpec.from_dict(data)


def test_rejects_dividers_outside_a_grid():
    data = {
        "nodes": [
            {"id": "first", "title": "First"},
            {"id": "second", "title": "Second"},
        ],
        "edges": [],
        "dividers": [{"after_row": 0}],
    }

    with pytest.raises(SpecError, match="requires the grid layout"):
        DiagramSpec.from_dict(data)
