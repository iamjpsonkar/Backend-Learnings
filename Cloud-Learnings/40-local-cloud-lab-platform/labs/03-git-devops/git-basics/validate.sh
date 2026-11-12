#!/usr/bin/env bash
# Validate lab: git-basics
set -euo pipefail

echo "=== Git Basics Lab Validation ==="
TMPDIR_LAB=$(mktemp -d)
trap 'rm -rf "$TMPDIR_LAB"' EXIT

# Check git is installed
if git --version &>/dev/null; then
    GIT_VER=$(git --version | awk '{print $3}')
    echo "PASS: git $GIT_VER is installed"
else
    echo "FAIL: git not installed"
    exit 1
fi

# Test: init a repo
cd "$TMPDIR_LAB"
git init -q testlab
cd testlab
git config user.email "lab@cloudlab.local"
git config user.name "Lab User"

if [ -d ".git" ]; then
    echo "PASS: git init creates .git directory"
else
    echo "FAIL: git init failed"
fi

# Test: first commit
echo "# Lab" > README.md
git add README.md
git commit -q -m "feat: initial commit"

COMMIT_COUNT=$(git log --oneline | wc -l)
if [ "$COMMIT_COUNT" -ge 1 ]; then
    echo "PASS: First commit recorded ($COMMIT_COUNT commit(s))"
else
    echo "FAIL: No commits found"
fi

# Test: branching
git checkout -q -b feature/test
echo "feature content" > feature.txt
git add feature.txt
git commit -q -m "feat: add feature file"

git checkout -q main 2>/dev/null || git checkout -q master 2>/dev/null

# Test: merge
git merge -q feature/test
if git log --oneline | grep -q "feat: add feature file"; then
    echo "PASS: Feature branch merged into main"
else
    echo "FAIL: Merge did not include feature commit"
fi

# Test: stash
echo "wip content" >> README.md
git stash push -q -m "wip: test stash"
STASH_COUNT=$(git stash list | wc -l)
if [ "$STASH_COUNT" -ge 1 ]; then
    echo "PASS: git stash works ($STASH_COUNT entry)"
else
    echo "FAIL: git stash did not save anything"
fi

git stash pop -q
if grep -q "wip content" README.md; then
    echo "PASS: git stash pop restores work-in-progress"
else
    echo "FAIL: Stash pop did not restore content"
fi

# Test: history
LOG_OUTPUT=$(git log --oneline --graph 2>/dev/null)
if [ -n "$LOG_OUTPUT" ]; then
    echo "PASS: git log shows project history"
    echo "  Commits:"
    git log --oneline | while IFS= read -r line; do echo "    $line"; done
else
    echo "FAIL: git log returned empty"
fi

echo ""
echo "=== Validation complete ==="
