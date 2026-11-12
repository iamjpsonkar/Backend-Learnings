#!/usr/bin/env python3
"""Validate documentation and Locust examples without contacting test targets."""

from __future__ import annotations

import ast
import json
import re
import runpy
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FENCE = "`" * 3
GUIDE_RANGES = {
    "docs/03-locust/02-installing-and-running-locust.md": range(1, 3),
    "docs/03-locust/03-testing-http-methods.md": range(3, 8),
    "docs/03-locust/04-organizing-tasks.md": range(8, 13),
    "docs/03-locust/05-load-models-and-custom-shapes.md": range(13, 17),
    "docs/03-locust/06-advanced-patterns.md": range(17, 22),
    "docs/03-locust/07-automation-and-distributed-scaling.md": range(22, 25),
}
DOC_SEQUENCES = {
    "01-foundations": 2,
    "02-optimization-strategies": 4,
    "03-locust": 7,
    "04-complex-systems": 19,
}
LINK_PATTERN = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
PYTHON_BLOCK_PATTERN = re.compile(
    re.escape(FENCE) + r"python\n(.*?)" + re.escape(FENCE),
    re.DOTALL,
)


def validate_markdown() -> None:
    guides = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    missing_links: list[str] = []

    for guide in guides:
        text = guide.read_text(encoding="utf-8")
        if text.count(FENCE) % 2:
            raise AssertionError(
                f"Unbalanced code fences in {guide.relative_to(ROOT)}"
            )

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                raise AssertionError(
                    f"Trailing whitespace in "
                    f"{guide.relative_to(ROOT)}:{line_number}"
                )
            if len(line) > 160:
                raise AssertionError(
                    f"Markdown line exceeds 160 characters: "
                    f"{guide.relative_to(ROOT)}:{line_number}"
                )

        for target in LINK_PATTERN.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue

            local_target = target.split("#", maxsplit=1)[0]
            if not (guide.parent / local_target).exists():
                missing_links.append(f"{guide.relative_to(ROOT)}: {target}")

    if missing_links:
        raise AssertionError("Missing local links:\n" + "\n".join(missing_links))

    print(f"Markdown: {len(guides)} guides passed")


def validate_document_sequences() -> None:
    for directory_name, expected_count in DOC_SEQUENCES.items():
        directory = ROOT / "docs" / directory_name
        actual_prefixes = [
            path.name.split("-", maxsplit=1)[0]
            for path in sorted(directory.glob("*.md"))
        ]
        expected_prefixes = [
            f"{number:02d}" for number in range(1, expected_count + 1)
        ]
        if actual_prefixes != expected_prefixes:
            raise AssertionError(
                f"Invalid guide sequence in {directory.relative_to(ROOT)}: "
                f"{actual_prefixes}"
            )

    print(f"Sequences: {len(DOC_SEQUENCES)} documentation tracks passed")


def validate_source_mappings() -> list[Path]:
    expected_paths = [
        ROOT / f"locust_tests/locust_{number:03d}/locustfile.py"
        for number in range(1, 25)
    ]
    actual_paths = sorted(ROOT.glob("locust_tests/locust_*/locustfile.py"))

    if actual_paths != expected_paths:
        raise AssertionError("Expected a continuous locust_001 through locust_024 set")

    for guide_name, example_numbers in GUIDE_RANGES.items():
        guide = ROOT / guide_name
        blocks = PYTHON_BLOCK_PATTERN.findall(guide.read_text(encoding="utf-8"))
        numbers = list(example_numbers)

        if len(blocks) != len(numbers):
            raise AssertionError(
                f"{guide_name} has {len(blocks)} Python blocks; "
                f"expected {len(numbers)}"
            )

        for block, number in zip(blocks, numbers, strict=True):
            source_path = ROOT / (
                f"locust_tests/locust_{number:03d}/locustfile.py"
            )
            source = source_path.read_text(encoding="utf-8")
            if block.strip() != source.strip():
                raise AssertionError(
                    f"Documentation differs from {source_path.relative_to(ROOT)}"
                )

    print(f"Mappings: {len(expected_paths)} documented examples match source")
    return expected_paths


def validate_notebook(paths: list[Path]) -> None:
    notebook_path = ROOT / "all_locust_tests.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    if notebook.get("nbformat") != 4:
        raise AssertionError("The Locust notebook must use notebook format 4")

    code_cells = [
        cell
        for cell in notebook.get("cells", [])
        if "locust-test" in cell.get("metadata", {}).get("tags", [])
    ]
    if len(code_cells) != len(paths):
        raise AssertionError(
            f"Notebook contains {len(code_cells)} Locust cells; "
            f"expected {len(paths)}"
        )

    for cell, path in zip(code_cells, paths, strict=True):
        relative_path = path.relative_to(ROOT).as_posix()
        if cell.get("metadata", {}).get("locustfile") != relative_path:
            raise AssertionError(
                f"Notebook cell path does not match {relative_path}"
            )

        cell_source = "".join(cell.get("source", []))
        file_source = path.read_text(encoding="utf-8")
        if cell_source != file_source:
            raise AssertionError(
                f"Notebook cell differs from {relative_path}"
            )

    print(f"Notebook: all {len(paths)} Locust cells match source")


def validate_python(paths: list[Path], label: str) -> None:
    for path in paths:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))

        for line_number, line in enumerate(source.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                raise AssertionError(
                    f"Trailing whitespace in {path.relative_to(ROOT)}:{line_number}"
                )
            if len(line) > 88:
                raise AssertionError(
                    f"Python line exceeds 88 characters: "
                    f"{path.relative_to(ROOT)}:{line_number}"
                )

    print(f"Python: {len(paths)} {label} parsed and formatted")


def validate_optimization_examples() -> None:
    paths = sorted((ROOT / "optimization_examples").glob("*.py"))
    if not paths:
        raise AssertionError("No optimization examples found")

    validate_python(paths, "optimization examples")

    for path in paths:
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            relative_path = path.relative_to(ROOT)
            output = result.stdout + result.stderr
            raise AssertionError(f"Example failed: {relative_path}\n{output}")

    print(f"Examples: all {len(paths)} optimization demonstrations passed")


def validate_discovery(paths: list[Path]) -> None:
    for path in paths:
        result = subprocess.run(
            [sys.executable, "-m", "locust", "-f", str(path), "--list"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        if result.returncode or "Available Users:" not in output:
            relative_path = path.relative_to(ROOT)
            raise AssertionError(f"Locust discovery failed for {relative_path}\n{output}")

    print(f"Discovery: Locust loaded all {len(paths)} examples")


def validate_shape_boundaries() -> None:
    cases = {
        13: {
            "class": "ConstantLoadShape",
            "ticks": {0: (10, 2), 59.9: (10, 2), 60: None},
        },
        15: {
            "class": "StepLoadShape",
            "ticks": {
                0: (5, 2),
                30: (10, 2),
                60: (15, 2),
                90: (20, 2),
                120: None,
            },
        },
        16: {
            "class": "SpikeLoadShape",
            "ticks": {0: (5, 2), 30: (30, 15), 45: (5, 15), 75: None},
        },
    }

    for number, case in cases.items():
        path = ROOT / f"locust_tests/locust_{number:03d}/locustfile.py"
        namespace = runpy.run_path(str(path))
        shape = namespace[str(case["class"])]()

        for run_time, expected in dict(case["ticks"]).items():
            shape.get_run_time = lambda value=run_time: value
            actual = shape.tick()
            if actual != expected:
                raise AssertionError(
                    f"Shape {number:03d} at {run_time}s returned {actual}; "
                    f"expected {expected}"
                )

    print(f"Shapes: {len(cases)} boundary suites passed")


def validate_images() -> None:
    images = sorted(ROOT.glob("locust_tests/**/*.jpg"))
    for image in images:
        data = image.read_bytes()
        if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
            raise AssertionError(f"Invalid JPEG file: {image.relative_to(ROOT)}")

    print(f"Images: {len(images)} JPEG files passed integrity checks")


def main() -> None:
    validate_markdown()
    validate_document_sequences()
    paths = validate_source_mappings()
    validate_notebook(paths)
    validate_python(paths, "locustfiles")
    validate_optimization_examples()
    validate_discovery(paths)
    validate_shape_boundaries()
    validate_images()
    print("Repository validation passed")


if __name__ == "__main__":
    main()
