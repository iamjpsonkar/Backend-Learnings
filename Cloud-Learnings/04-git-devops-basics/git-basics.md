← [Previous: Git & DevOps Basics](./README.md) | [Home](../README.md) | [Next: GitHub Workflow →](./github-workflow.md)

---

# Git Basics

Git is a distributed version control system. Every developer has a full copy of the repository history. Changes are recorded as immutable commits forming a directed acyclic graph (DAG).

---

## Setup

```bash
# Identify yourself (stored in commits)
git config --global user.name "Alice Smith"
git config --global user.email "alice@example.com"

# Default editor for commit messages
git config --global core.editor "vim"           # or nano, code --wait, etc.

# Default branch name (match GitHub's default)
git config --global init.defaultBranch main

# Better diff output
git config --global diff.colorMoved zebra

# Show config
git config --global --list
git config --list --show-origin    # also shows which file each setting comes from
```

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Repository (repo)** | A directory tracked by Git, containing the full history |
| **Working directory** | Files on disk that you are editing |
| **Staging area (index)** | Snapshot prepared for the next commit |
| **Commit** | An immutable snapshot of staged changes, with a SHA-1 hash ID |
| **Branch** | A lightweight, movable pointer to a commit |
| **HEAD** | A pointer to your current position in the repo (usually a branch tip) |
| **Remote** | A reference to another repository (e.g., `origin` on GitHub) |
| **Detached HEAD** | HEAD points directly to a commit, not a branch |

---

## Initialise and Clone

```bash
# Start a new repository
git init my-project
cd my-project

# Clone an existing repository
git clone https://github.com/org/repo.git          # HTTPS
git clone git@github.com:org/repo.git              # SSH (preferred)
git clone git@github.com:org/repo.git my-dir       # clone into specific directory
git clone --depth 1 git@github.com:org/repo.git    # shallow clone (latest commit only)

# View remote URLs
git remote -v
```

---

## Staging and Committing

```bash
# Check what has changed
git status
git status -s                    # short format

# See what changed (unstaged)
git diff
git diff filename.py

# See what is staged for commit
git diff --staged
git diff --staged filename.py

# Stage files
git add filename.py              # stage one file
git add src/                     # stage a directory
git add -p                       # stage interactively (choose hunks)
git add .                        # stage all changes in current directory

# Unstage a file (keeps changes in working directory)
git restore --staged filename.py

# Discard changes in working directory (DESTRUCTIVE — cannot undo)
git restore filename.py          # discard unstaged changes
git restore .                    # discard all unstaged changes

# Commit staged changes
git commit -m "feat: add user authentication endpoint"
git commit                       # opens editor for longer message
git commit -am "fix: correct typo"  # stage and commit all tracked files

# Amend the most recent commit (before pushing)
git commit --amend -m "feat: add user authentication endpoint"
git commit --amend --no-edit     # amend without changing message (e.g., add a forgotten file)
```

---

## Commit Messages

Well-written commit messages are essential for understanding project history. Follow the **Conventional Commits** format:

```
<type>(<optional scope>): <short summary>

<optional body: what and why, not how>

<optional footer: issue refs, breaking changes>
```

**Types:**

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or correcting tests |
| `chore` | Build process, tooling, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |
| `revert` | Reverting a previous commit |

**Examples:**

```
feat(auth): add JWT refresh token rotation

fix(api): return 422 on invalid email format instead of 500

docs: update deployment guide for ECS Fargate

chore: upgrade boto3 from 1.28 to 1.34

feat!: remove deprecated v1 API endpoints

BREAKING CHANGE: /api/v1/* endpoints removed; use /api/v2/*
```

**Rules:**
- First line: 50 characters or fewer, imperative mood ("add" not "added")
- Blank line between summary and body
- Body: wrap at 72 characters; explain the *why*, not the *what*
- Reference issues: `Closes #123`, `Fixes GH-456`

---

## Viewing History

```bash
# Log with various formats
git log                                  # full log
git log --oneline                        # one line per commit
git log --oneline --graph                # ASCII branch graph
git log --oneline --graph --all          # all branches
git log --oneline -10                    # last 10 commits
git log --author="Alice"                 # filter by author
git log --since="2024-01-01"            # filter by date
git log --grep="auth"                    # filter by commit message
git log -- filename.py                   # commits touching a specific file

# Show a specific commit
git show abc1234                         # full diff of commit
git show abc1234:src/app.py             # show a file at that commit

# Find which commit introduced a string
git log -S "def authenticate"            # commits that changed this string
git log -G "authenticate.*token"         # commits matching regex in diff

# Who changed a line?
git blame filename.py
git blame -L 10,20 filename.py          # lines 10–20 only

# Find when a bug was introduced (binary search)
git bisect start
git bisect bad                           # current commit has the bug
git bisect good v1.0.0                  # this tag was known good
# Git checks out the middle commit; you test and mark:
git bisect good    # or bad
# Git continues until it finds the first bad commit
git bisect reset   # when done
```

---

## Branching

```bash
# List branches
git branch                               # local branches
git branch -r                           # remote branches
git branch -a                           # all branches

# Create a branch
git branch feature/user-auth            # create without switching
git checkout -b feature/user-auth       # create and switch (older syntax)
git switch -c feature/user-auth         # create and switch (modern)

# Switch branches
git checkout main                        # older syntax
git switch main                          # modern syntax

# Rename a branch
git branch -m old-name new-name
git branch -M main                       # rename current branch to main

# Delete a branch
git branch -d feature/user-auth         # safe delete (fails if unmerged)
git branch -D feature/user-auth         # force delete
git push origin --delete feature/user-auth  # delete on remote

# Track a remote branch
git checkout --track origin/feature/user-auth
# or simply:
git switch feature/user-auth            # Git auto-tracks if remote exists
```

---

## Merging

```bash
# Merge a branch into current branch
git checkout main
git merge feature/user-auth             # fast-forward if possible

# Always create a merge commit (no fast-forward)
git merge --no-ff feature/user-auth

# Abort a merge in progress
git merge --abort

# After resolving conflicts:
git add conflicted-file.py
git commit                              # completes the merge
```

### Merge Conflict Resolution

```bash
# Conflict markers in a file:
<<<<<<< HEAD
    return authenticate_v2(user)        # your current branch
=======
    return authenticate_v1(user)        # the branch being merged
>>>>>>> feature/user-auth

# Options:
# 1. Keep yours:
git checkout --ours filename.py

# 2. Keep theirs:
git checkout --theirs filename.py

# 3. Edit manually, then:
git add filename.py
git commit

# Use a merge tool
git mergetool                            # opens configured tool (vimdiff, meld, etc.)
```

---

## Rebasing

Rebase replays your commits on top of another branch. It rewrites history — **never rebase shared/public branches**.

```bash
# Rebase current branch onto main
git checkout feature/user-auth
git rebase main

# Interactive rebase: edit, squash, reorder last N commits
git rebase -i HEAD~3                     # last 3 commits
# Commands in the editor:
# pick   = keep as-is
# reword = change commit message
# edit   = pause to amend the commit
# squash = combine with previous commit (keep messages)
# fixup  = combine with previous commit (discard message)
# drop   = remove the commit entirely

# Abort a rebase
git rebase --abort

# Continue after resolving conflicts during a rebase
git add resolved-file.py
git rebase --continue
```

### Merge vs Rebase

| Merge | Rebase |
|-------|--------|
| Preserves full history | Creates linear history |
| Creates merge commits | No merge commits |
| Safe on shared branches | Never rebase shared branches |
| Shows when branches diverged | History appears as if changes were sequential |
| Use for integrating long-lived branches | Use for cleanup before PR |

**Common pattern:**
```
# Before opening a PR: clean up your feature branch
git switch feature/user-auth
git rebase -i main            # squash/fixup WIP commits
git push --force-with-lease   # safer than --force (fails if someone else pushed)
```

---

## Remotes

```bash
# View remotes
git remote -v

# Add a remote
git remote add origin git@github.com:org/repo.git
git remote add upstream git@github.com:original/repo.git   # for forks

# Fetch (download) without merging
git fetch origin                         # fetch all branches
git fetch origin main                   # fetch specific branch

# Pull = fetch + merge (or fetch + rebase)
git pull origin main
git pull --rebase origin main           # pull then rebase (avoids merge commits)

# Push
git push origin feature/user-auth       # push a branch
git push -u origin feature/user-auth    # push and set upstream tracking
git push                                 # push current branch (if tracking set)
git push --force-with-lease             # force push safely (safer than --force)

# Set upstream tracking manually
git branch --set-upstream-to=origin/main main
```

---

## Undoing Changes

```bash
# Undo staged changes (keeps working directory changes)
git restore --staged filename.py

# Discard working directory changes (DESTRUCTIVE)
git restore filename.py
git restore .

# Undo last commit, keep changes staged
git reset --soft HEAD~1

# Undo last commit, keep changes unstaged
git reset HEAD~1                         # default: --mixed

# Undo last commit, discard changes (DESTRUCTIVE)
git reset --hard HEAD~1

# Revert a commit (creates a NEW commit that undoes the changes — safe for shared branches)
git revert abc1234                       # revert a specific commit
git revert HEAD                          # revert the most recent commit
git revert HEAD~3..HEAD                 # revert last 3 commits

# Recover a deleted branch or lost commits
git reflog                               # log of all HEAD movements
git checkout -b recovered abc1234       # recreate branch at a found commit
```

> **Rule of thumb:**
> - Before pushing: `reset` is fine (rewrites local history)
> - After pushing: use `revert` (preserves shared history)

---

## Stashing

Stash saves your uncommitted changes temporarily so you can switch contexts.

```bash
# Save current changes
git stash                                # stash with auto-name
git stash push -m "WIP: auth refactor"  # stash with a name

# List stashes
git stash list

# Apply stash (and keep it in stash list)
git stash apply                          # most recent
git stash apply stash@{2}               # specific stash

# Apply and remove from stash list
git stash pop                            # most recent
git stash pop stash@{2}

# Stash only unstaged changes (keep staged)
git stash --keep-index

# Include untracked files
git stash -u

# View stash diff
git stash show -p stash@{0}

# Delete a stash
git stash drop stash@{0}
git stash clear                          # remove all stashes
```

---

## Tags

```bash
# Create a lightweight tag
git tag v1.0.0

# Create an annotated tag (preferred for releases)
git tag -a v1.0.0 -m "Release version 1.0.0"
git tag -a v1.0.0 abc1234 -m "Tag specific commit"

# List tags
git tag
git tag -l "v1.*"

# Push tags to remote
git push origin v1.0.0                   # specific tag
git push origin --tags                   # all tags

# Delete a tag
git tag -d v1.0.0                        # local
git push origin --delete v1.0.0         # remote
```

---

## .gitignore

```gitignore
# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp
*~

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/

# Node.js
node_modules/
npm-debug.log*

# Terraform
*.tfstate
*.tfstate.backup
.terraform/
*.tfvars         # may contain secrets

# Secrets / credentials — NEVER commit these
.env
.env.*
!.env.example    # exception: example files are OK
*.pem
*.key
id_rsa
*.secrets
credentials.json

# Build output
target/
out/
*.jar
```

```bash
# Check if a file is ignored
git check-ignore -v filename.py

# See all ignored files
git status --ignored

# Force add an ignored file (rarely needed)
git add -f ignored-file.txt

# Global gitignore (applies to all repos)
git config --global core.excludesfile ~/.gitignore_global
```

---

## Useful Aliases

```bash
# Add to ~/.gitconfig
git config --global alias.st "status -s"
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.br "branch -a"
git config --global alias.unstage "restore --staged"
git config --global alias.last "log -1 HEAD --stat"
git config --global alias.undo "reset HEAD~1"
git config --global alias.stash-all "stash push --include-untracked"

# Usage
git st
git lg
git last
```

---

## References

- [Pro Git — free online book](https://git-scm.com/book/en/v2)
- [Git reference manual](https://git-scm.com/docs)
- [Conventional Commits specification](https://www.conventionalcommits.org/)
- [Oh My Git! — interactive learning](https://ohmygit.org/)
- [Git flight rules — how to handle common situations](https://github.com/k88hudson/git-flight-rules)
---

← [Previous: Git & DevOps Basics](./README.md) | [Home](../README.md) | [Next: GitHub Workflow →](./github-workflow.md)
