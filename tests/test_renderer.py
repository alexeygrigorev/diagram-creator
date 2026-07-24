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
