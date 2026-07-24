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
