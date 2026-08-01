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
