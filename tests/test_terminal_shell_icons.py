from diagram_creator.renderer import ICON_INK, render_diagram
from diagram_creator.spec import DiagramSpec


def test_terminal_and_shell_icons_are_accepted_distinct_and_embedded(tmp_path):
    spec = DiagramSpec.from_dict(
        {
            "nodes": [
                {"id": "terminal", "title": "Terminal", "icon": "terminal"},
                {"id": "shell", "title": "Shell", "icon": "shell"},
            ],
            "edges": [{"from": "terminal", "to": "shell"}],
        }
    )

    assert [node.icon for node in spec.nodes] == ["terminal", "shell"]
    assert ICON_INK["terminal"] != ICON_INK["shell"]

    output = render_diagram(spec, tmp_path / "terminal-shell.svg")
    svg = output.read_text()
    terminal_symbol = svg.split('<symbol id="icon-terminal"', 1)[1].split("</symbol>", 1)[0]
    shell_symbol = svg.split('<symbol id="icon-shell"', 1)[1].split("</symbol>", 1)[0]

    assert "<rect" in terminal_symbol
    assert "<rect" not in shell_symbol
    assert terminal_symbol != shell_symbol
    assert 'href="#icon-terminal"' in svg
    assert 'href="#icon-shell"' in svg
