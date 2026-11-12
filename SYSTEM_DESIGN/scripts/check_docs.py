#!/usr/bin/env python3
"""Validate local links, images, and top-level Markdown structure."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parsed_target(raw_target: str) -> tuple[str | None, str]:
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return (None, "")
    if target.startswith("#"):
        return (None, unquote(parsed.fragment))
    return (unquote(parsed.path), unquote(parsed.fragment))


def anchors_for(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        heading = HEADING.match(line) if not in_fence else None
        if not heading:
            continue
        label = re.sub(r"<[^>]+>", "", heading.group(2))
        label = re.sub(r"[*_`~]", "", label).strip().lower()
        base = re.sub(r"[^\w\- ]", "", label)
        base = re.sub(r"\s+", "-", base)
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return anchors


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    h1_count = 0
    previous_level = 0
    in_fence = False

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            h1_count += level == 1
            if previous_level and level > previous_level + 1:
                errors.append(
                    f"{path.relative_to(ROOT)}:{line_number}: "
                    f"heading jumps from H{previous_level} to H{level}"
                )
            previous_level = level

        targets = MARKDOWN_LINK.findall(line) + HTML_IMAGE.findall(line)
        for raw_target in targets:
            target, fragment = parsed_target(raw_target)
            destination = (path.parent / target).resolve() if target else path.resolve()
            if target and not destination.exists():
                errors.append(
                    f"{path.relative_to(ROOT)}:{line_number}: "
                    f"missing local target {target!r}"
                )
            elif fragment and destination.suffix.lower() == ".md":
                if fragment not in anchors_for(destination):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{line_number}: "
                        f"missing heading anchor #{fragment} in "
                        f"{destination.relative_to(ROOT)}"
                    )

    if h1_count != 1:
        errors.append(
            f"{path.relative_to(ROOT)}: expected exactly one H1, found {h1_count}"
        )
    if in_fence:
        errors.append(f"{path.relative_to(ROOT)}: unclosed fenced code block")
    return errors


def main() -> int:
    markdown_files = sorted(
        path for path in ROOT.rglob("*.md") if ".git" not in path.parts
    )
    errors = [error for path in markdown_files for error in validate(path)]

    solution_files = sorted((ROOT / "system-design-examples").glob("*/SOLUTION.md"))
    if len(solution_files) != 60:
        errors.append(f"expected 60 worked solutions, found {len(solution_files)}")

    required_solution_sections = {
        "architecture": ("architecture", "concrete architecture", "high-level architecture"),
        "capacity": ("capacity assumptions", "capacity estimation"),
        "workflow": ("create flow", "end-to-end flow", "step-by-step workflow", "step-by-step create flow"),
        "implementation": ("implementation path", "implementation plan"),
        "failure handling": ("failure handling", "failure scenarios"),
        "operations": ("observability", "production checks", "observability and slos"),
    }
    for solution in solution_files:
        text = solution.read_text(encoding="utf-8")
        headings = {
            re.sub(r"^\d+\.\s+", "", line[3:].strip().lower())
            for line in text.splitlines()
            if line.startswith("## ")
        }
        for concept, alternatives in required_solution_sections.items():
            if not any(alternative in headings for alternative in alternatives):
                errors.append(
                    f"{solution.relative_to(ROOT)}: missing required {concept} section"
                )
        step_count = sum(
            bool(re.match(r"^\d+\.\s+\S", line)) for line in text.splitlines()
        )
        if step_count < 4:
            errors.append(
                f"{solution.relative_to(ROOT)}: expected at least 4 workflow steps, "
                f"found {step_count}"
            )
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(
        f"Documentation validation passed ({len(markdown_files)} files, "
        f"{len(solution_files)} worked solutions)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
