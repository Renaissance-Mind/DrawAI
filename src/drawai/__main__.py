"""Allow `python -m drawai` to run the console CLI."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
