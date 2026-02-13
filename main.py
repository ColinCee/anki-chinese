"""
Entry point — delegates to the CLI.

    uv run anki-chinese --help
    uv run anki-chinese init
    uv run anki-chinese build
"""

from anki_chinese.cli import app

if __name__ == "__main__":
    app()
