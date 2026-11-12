#!/usr/bin/env python3
"""Add top navigation bar to all MD files that have a bottom nav footer.

Mirrors the bottom nav line to the top of each file so readers can navigate
without scrolling to the bottom first.

Safe to re-run — skips files that already have a top nav.

Usage:
    python3 scripts/add-top-nav.py
"""

import logging
import os
import re
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(message)s',
)
log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {
    '.git',
    'docker',
    '40-local-cloud-lab-platform',
    'assets',
    'templates',
    '.claude',
    '.github',
    'scripts',
    'node_modules',
}

# Matches the bottom nav line at any position in the file, e.g.:
#   ← [Previous: Label](path) | [Home](../README.md) | [Next: Label →](path)
NAV_PATTERN = re.compile(r'^(← \[Previous:.+)$', re.MULTILINE)


def process_file(filepath: str) -> str:
    """Process a single MD file.

    Returns one of:
        'updated'      — top nav was added successfully
        'already-done' — file already starts with top nav; skipped
        'no-nav'       — no bottom nav found in file; skipped
    """
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except OSError as exc:
        log.error('read failed: %s — %s', filepath, exc)
        return 'error'

    match = NAV_PATTERN.search(content)
    if not match:
        log.debug('no-nav: %s', filepath)
        return 'no-nav'

    nav_line = match.group(1).rstrip()

    # Idempotency check — already has top nav
    if content.lstrip().startswith('← [Previous:'):
        log.debug('already-done: %s', filepath)
        return 'already-done'

    new_content = nav_line + '\n\n---\n\n' + content
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except OSError as exc:
        log.error('write failed: %s — %s', filepath, exc)
        return 'error'

    log.debug('updated: %s', filepath)
    return 'updated'


def main() -> int:
    counts = {'updated': 0, 'already-done': 0, 'no-nav': 0, 'error': 0}

    log.info('Repo root: %s', REPO_ROOT)
    log.info('Skipping directories: %s', ', '.join(sorted(SKIP_DIRS)))

    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune skip dirs in-place so os.walk doesn't descend into them
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)

        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue

            filepath = os.path.join(root, fname)
            result = process_file(filepath)
            counts[result] += 1

            if result == 'updated':
                rel = os.path.relpath(filepath, REPO_ROOT)
                print(f'  updated: {rel}')

    print()
    print(
        f'Done: {counts["updated"]} updated, '
        f'{counts["already-done"]} already had top nav, '
        f'{counts["no-nav"]} had no nav (skipped), '
        f'{counts["error"]} errors.'
    )

    return 1 if counts['error'] > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
