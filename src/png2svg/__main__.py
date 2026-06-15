"""Allow `python -m png2svg` to invoke the CLI."""

from png2svg.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
