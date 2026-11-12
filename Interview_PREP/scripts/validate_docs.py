#!/usr/bin/env python3
"""Validate the repository's Markdown and Jupyter learning material."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^```(?P<language>[\w+-]*)\s*$")
LOCAL_LINK = re.compile(r"\[[^]]+\]\((?!https?://|#|mailto:)([^)]+)\)")


def validate_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    display_path = path.relative_to(ROOT)
    language: str | None = None
    code: list[str] = []
    opening_line = 0

    for line_number, line in enumerate(source.splitlines(), start=1):
        match = FENCE.match(line)
        if not match:
            if language is not None:
                code.append(line)
            continue

        if language is None:
            language = match.group("language").lower()
            opening_line = line_number
            code = []
        else:
            if language in {"py", "python"}:
                try:
                    ast.parse("\n".join(code), filename=f"{display_path}:{opening_line}")
                except SyntaxError as exc:
                    errors.append(f"{display_path}:{opening_line}: invalid Python: {exc.msg}")
            language = None
            code = []

    if language is not None:
        errors.append(f"{display_path}:{opening_line}: unclosed code fence")

    for match in LOCAL_LINK.finditer(source):
        raw_target = match.group(1).split("#", maxsplit=1)[0]
        target = (ROOT / raw_target).resolve()
        if not target.exists():
            errors.append(f"{display_path}: local link does not exist: {raw_target}")

    return errors


def validate_notebook(path: Path, *, require_clean_outputs: bool = False) -> list[str]:
    errors: list[str] = []
    display_path = path.relative_to(ROOT)
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{display_path}: cannot read notebook: {exc}"]

    if notebook.get("nbformat") != 4:
        errors.append(f"{display_path}: expected notebook format 4")

    if not isinstance(notebook.get("cells"), list):
        return [*errors, f"{display_path}: cells must be a list"]

    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        try:
            ast.parse(source, filename=f"{display_path}:cell-{index + 1}")
        except SyntaxError as exc:
            errors.append(f"{display_path}:cell-{index + 1}: invalid Python: {exc.msg}")

        if require_clean_outputs and (
            cell.get("execution_count") is not None or cell.get("outputs")
        ):
            errors.append(f"{display_path}:cell-{index + 1}: clear outputs before committing")

    return errors


def main() -> int:
    errors = [
        *(error for path in ROOT.glob("*.md") for error in validate_markdown(path)),
        *(
            error
            for path in ROOT.glob("*.ipynb")
            for error in validate_notebook(
                path, require_clean_outputs=path.name == "README.ipynb"
            )
        ),
    ]
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
