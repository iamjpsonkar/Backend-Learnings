#!/usr/bin/env python3
"""
check-missing-topics.py — Report content gaps in the Cloud-Learnings repository.

Checks:
  1. Directories that exist but have no README.md
  2. Files listed in a directory's README.md that do not exist on disk
  3. Directories in the target structure that do not exist yet (planned sections)

Usage:
    python3 scripts/check-missing-topics.py
    python3 scripts/check-missing-topics.py --section 05-aws
    python3 scripts/check-missing-topics.py --format json
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Target structure — sections that should eventually exist
# ---------------------------------------------------------------------------
EXPECTED_SECTIONS = [
    "00-foundations",
    "01-cloud-fundamentals",
    "02-linux",
    "03-networking",
    "04-git-devops-basics",
    "05-aws",
    "06-azure",
    "07-gcp",
    "08-other-clouds",
    "09-containers",
    "10-kubernetes",
    "11-terraform-opentofu",
    "12-ansible",
    "13-cicd-gitops",
    "14-security",
    "15-observability",
    "16-sre",
    "17-finops",
    "18-databases",
    "19-disaster-recovery",
    "20-migration",
    "21-multi-cloud",
    "22-projects",
    "23-troubleshooting",
    "24-cheatsheets",
    "25-glossary",
    "26-roadmaps",
    "27-interview-prep",
    "28-references",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Return the repo root (parent of this script's directory)."""
    return Path(__file__).resolve().parent.parent


def extract_md_links(readme: Path) -> list[str]:
    """
    Parse a README.md and return all relative .md file paths mentioned
    in Markdown links: [text](./path.md) or [text](path.md)
    """
    links: list[str] = []
    if not readme.exists():
        return links

    text = readme.read_text(encoding="utf-8", errors="replace")
    # Match [label](./some/path.md) — capture the path
    pattern = re.compile(r'\[(?:[^\]]*)\]\((\.[^)]+\.md)\)')
    for match in pattern.finditer(text):
        raw = match.group(1)
        # Normalise: remove leading ./
        normalised = raw.lstrip("./")
        links.append(normalised)
    return links


def check_directory(directory: Path) -> dict:
    """Run checks on a single directory. Returns a result dict."""
    result = {
        "path": str(directory.relative_to(repo_root())),
        "has_readme": False,
        "missing_files": [],
        "extra_notes": [],
    }

    readme = directory / "README.md"
    result["has_readme"] = readme.exists()

    if not result["has_readme"]:
        return result

    # Extract links from README and check if those files exist
    links = extract_md_links(readme)
    for link in links:
        target = directory / link
        if not target.exists():
            result["missing_files"].append(link)

    return result


# ---------------------------------------------------------------------------
# Main checks
# ---------------------------------------------------------------------------

def check_missing_sections(root: Path) -> list[str]:
    """Return sections in EXPECTED_SECTIONS that do not exist yet."""
    missing = []
    for section in EXPECTED_SECTIONS:
        if not (root / section).is_dir():
            missing.append(section)
    return missing


def check_all_directories(root: Path, section_filter: str | None = None) -> list[dict]:
    """Walk the repo and check every content directory."""
    results = []

    # Directories to skip entirely
    skip_dirs = {".git", ".github", "node_modules", "__pycache__", ".venv"}

    for dirpath in sorted(root.rglob("*")):
        if not dirpath.is_dir():
            continue
        # Skip hidden / tool directories
        if any(part in skip_dirs for part in dirpath.parts):
            continue
        # Skip pure asset directories (images, diagrams source files)
        rel = dirpath.relative_to(root)
        rel_str = str(rel)
        if rel_str.startswith(("assets/images", "assets/diagrams", "assets/prompts")):
            continue
        if section_filter and not rel_str.startswith(section_filter):
            continue

        result = check_directory(dirpath)
        # Only include directories that have at least one issue
        if not result["has_readme"] or result["missing_files"]:
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_text_report(
    dir_results: list[dict],
    missing_sections: list[str],
) -> int:
    """Print a human-readable report. Returns exit code."""
    issues = 0

    print("\n=== Missing top-level sections ===")
    if missing_sections:
        for s in missing_sections:
            print(f"  [PLANNED]  {s}/")
        print(f"\n  {len(missing_sections)} section(s) not yet created (expected per target architecture)")
    else:
        print("  All expected sections exist.")

    print("\n=== Directory issues ===")
    if not dir_results:
        print("  No issues found.")
    else:
        for r in dir_results:
            if not r["has_readme"]:
                print(f"  [NO README]  {r['path']}/")
                issues += 1
            for mf in r["missing_files"]:
                print(f"  [MISSING]    {r['path']}/{mf}")
                issues += 1

    print(f"\n{'='*50}")
    print(f"  Total issues (excluding planned sections): {issues}")
    print(f"{'='*50}\n")

    return 0 if issues == 0 else 1


def print_json_report(dir_results: list[dict], missing_sections: list[str]) -> int:
    """Print a JSON report. Returns exit code."""
    report = {
        "missing_sections": missing_sections,
        "directory_issues": dir_results,
        "summary": {
            "missing_sections": len(missing_sections),
            "directories_without_readme": sum(1 for r in dir_results if not r["has_readme"]),
            "missing_linked_files": sum(len(r["missing_files"]) for r in dir_results),
        },
    }
    print(json.dumps(report, indent=2))
    total_issues = report["summary"]["directories_without_readme"] + report["summary"]["missing_linked_files"]
    return 0 if total_issues == 0 else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report content gaps in the Cloud-Learnings repository."
    )
    parser.add_argument(
        "--section",
        metavar="SECTION",
        help="Limit checks to a specific section (e.g., '05-aws')",
        default=None,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    root = repo_root()
    log.info("Repo root: %s", root)
    log.info("Scanning for content gaps...")

    missing_sections = check_missing_sections(root)
    dir_results = check_all_directories(root, section_filter=args.section)

    if args.format == "json":
        return print_json_report(dir_results, missing_sections)
    return print_text_report(dir_results, missing_sections)


if __name__ == "__main__":
    sys.exit(main())
