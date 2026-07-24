from __future__ import annotations

import argparse
from collections.abc import Sequence

from diagram_creator.__version__ import __version__
from diagram_creator.renderer import render_diagram
from diagram_creator.spec import SpecError, load_spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a polished horizontal workflow diagram from JSON."
    )
    parser.add_argument("input", help="Path to the JSON diagram specification")
    parser.add_argument("output", help="Path for the generated PNG")
    parser.add_argument("--width", type=int, default=1440, help="Canvas width in pixels")
    parser.add_argument("--height", type=int, default=360, help="Canvas height in pixels")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.input)
        output = render_diagram(spec, args.output, width=args.width, height=args.height)
    except (OSError, SpecError) as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
