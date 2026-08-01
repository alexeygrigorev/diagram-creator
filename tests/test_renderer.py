import json

from PIL import Image

from diagram_creator.cli import main
from diagram_creator.renderer import render_diagram
from diagram_creator.spec import DiagramSpec


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


def test_renders_a_five_node_ring_as_svg(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "title": "Continuous FAQ loop",
            "canvas": {"width": 1100, "height": 550},
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
    assert 'width="1100" height="550"' in svg
    assert 'transform="translate(420 20)"' in svg
    assert 'transform="translate(760 155)"' in svg
    assert 'd="M680 70C770 70 840 105 870 155"' in svg
    assert 'd="M230 155C260 105 330 70 420 70"' in svg
    assert '<symbol id="icon-database"' in svg
    assert ">@</text>" in svg
    assert 'textLength="188"' in svg
    assert "Each failure improves the data" in svg
