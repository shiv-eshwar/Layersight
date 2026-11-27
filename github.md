# GitHub

How to commit and push LayerSight, and the authorship rules every commit must follow.

| | |
|---|---|
| Repository | https://github.com/shiv-eshwar/Layersight |
| Remote | `origin` → `https://github.com/shiv-eshwar/Layersight.git` |
| Default branch | `main` |
| Only contributor | **shiv-eshwar** |

## 1. Authorship rules (mandatory on every commit)

These rules apply to every commit, whoever or whatever writes the code: a person, an editor, or an AI coding agent. There are no exceptions.

1. **shiv-eshwar is the only author, committer and contributor.** Every commit must have:
   - author: `shiv-eshwar <bl.en.u4cse23072@bl.students.amrita.edu>`
   - committer: `shiv-eshwar <bl.en.u4cse23072@bl.students.amrita.edu>`
2. **Never credit Cursor or any AI agent.** No `Cursor Agent`, no `cursoragent@cursor.com`, as author, committer, co-author or anywhere in the message.
3. **No co-author trailers at all.** No `Co-authored-by:`, `Made-with:`, `Generated-by:` or `Assisted-by:` lines, and no "Generated with …" / "Made with …" text in commit messages or pull request descriptions.
4. **Never override the identity.** Don't use `--author`, and don't set `GIT_AUTHOR_*` or `GIT_COMMITTER_*` to anything else.
5. **Never bypass the hooks.** Don't use `--no-verify` on `git commit` or `git push`.
6. **Push after every commit.** `main` on GitHub should always match local `main`.
7. **Verify before every push** (section 5). If anything other than shiv-eshwar appears, fix it before pushing (section 7).

The second email, `149902164+shiv-eshwar@users.noreply.github.com`, is shiv-eshwar's GitHub no-reply address. The hooks accept it too, so commits made with it still count as shiv-eshwar's.

## 2. How the rules are enforced

Two git hooks live in `.githooks/` and are committed with the repo:

| Hook | When it runs | What it does |
|---|---|---|
| `commit-msg` | Every `git commit` | Rejects the commit unless both author and committer are shiv-eshwar with an allowed email. Strips any `Co-authored-by` / `Made-with` / `Generated-by` / `Assisted-by` trailer. Rejects messages that credit Cursor. |
| `pre-push` | Every `git push` | Re-checks every commit being pushed: author, committer, and message. Blocks the push if any commit breaks the rules. |

Git doesn't enable hooks from a clone automatically, so run the setup in section 3 once on every machine.

## 3. One-time setup

### On a fresh machine

```bash
git clone https://github.com/shiv-eshwar/Layersight.git
cd Layersight
```

### On every machine (including the current one)

```bash
# Identity for this repository (overrides any global identity)
git config --local user.name  "shiv-eshwar"
git config --local user.email "bl.en.u4cse23072@bl.students.amrita.edu"

# Turn on the authorship hooks
git config --local core.hooksPath .githooks
chmod +x .githooks/*

# Keep editor and agent folders out of the repo
printf '.cursor/\n.vscode/\n.idea/\n.DS_Store\n' >> .git/info/exclude

# GitHub authentication (once per machine)
gh auth login        # choose GitHub.com, HTTPS, log in as shiv-eshwar
gh auth setup-git
```

Check the setup:

```bash
git var GIT_AUTHOR_IDENT      # must start with: shiv-eshwar <bl.en.u4cse23072@bl.students.amrita.edu>
git var GIT_COMMITTER_IDENT   # same
git config core.hooksPath     # must print: .githooks
gh auth status                # must show: Logged in to github.com account shiv-eshwar
```

## 4. Everyday workflow

```bash
git pull --rebase origin main        # start from the latest main
# ... make changes ...
git status                           # review what changed
git add <files>                      # stage deliberately; avoid `git add .` with unknown files
git commit -m "feat(engine): add reply-to mismatch rule"
# verify (section 5), then:
git push origin main
```

First push of a new local repository: `git push -u origin main`.

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, imperative mood, at most 72 characters in the summary.

| Type | Use for |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fixes |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Code change with no behavior change |
| `chore` | Tooling, config, dependencies |
| `perf` | Performance |
| `style` | Formatting only |

Scopes: `engine`, `api`, `web`, `data`, `docs`, `infra`.

Examples:

```
feat(engine): score look-alike domains with homoglyph skeletons
fix(api): reject zip uploads with path traversal
docs: record official test data format in context.md
```

Make small, focused commits and push each one.

## 5. Verify before every push

```bash
git log origin/main..HEAD --format='%h  author=%an <%ae>  committer=%cn <%ce>'
git log origin/main..HEAD --format=%B | grep -iE 'co-authored-by|cursor' && echo "FIX BEFORE PUSHING" || echo "messages clean"
```

On the very first push (no `origin/main` yet), use `git log --format=...` without the range.

Every line must show `author=shiv-eshwar` and `committer=shiv-eshwar`, and the second command must print `messages clean`.

After pushing, confirm on GitHub:

```bash
gh api repos/shiv-eshwar/Layersight/commits --jq '.[0:5][] | "\(.sha[0:7]) author=\(.author.login) committer=\(.committer.login)"'
gh api repos/shiv-eshwar/Layersight/contributors --jq '.[].login'   # must list only: shiv-eshwar
```

GitHub's contributor list can take a few minutes to refresh after a push.

## 6. Branches and pull requests

- `main` must always run. During the hackathon, small commits straight to `main` are fine.
- For larger work, use a short-lived branch: `git switch -c feat/simulator-funnel`, push with `git push -u origin feat/simulator-funnel`, open a PR with `gh pr create --fill`, and merge with `gh pr merge --squash`.
- PR titles and descriptions follow the same rules: no AI or Cursor attribution, no "Generated with" footers.
- Merging on GitHub records shiv-eshwar as author but "GitHub" as committer. That adds no contributor, but to keep both fields as shiv-eshwar, merge locally instead:

```bash
git switch main && git pull --rebase origin main
git merge --ff-only feat/simulator-funnel
git push origin main
```

## 7. Fixing a bad commit

### Last commit, not pushed yet

```bash
git commit --amend --reset-author --no-edit     # fixes author and committer
git commit --amend                              # opens the editor; delete any co-author or Cursor lines
```

### Several commits, not pushed yet

```bash
git rebase -i origin/main --exec 'git commit --amend --reset-author --no-edit'
```

To edit messages during the rebase, change `pick` to `reword` for those commits.

### Already pushed

Rewriting published history needs a force push. Only do it on `main` if nobody else has pulled the bad commits:

```bash
git rebase -i <last-good-sha> --exec 'git commit --amend --reset-author --no-edit'
git push --force-with-lease origin main
```

Always use `--force-with-lease`, never plain `--force`.

## 8. Never commit

- Secrets: `.env`, API keys, tokens. Commit `.env.example` with placeholders instead.
- Dependencies and build output: `node_modules/`, `.venv/`, `.next/`, `dist/`, `__pycache__/`.
- Editor and agent folders: `.cursor/`, `.vscode/`, `.idea/`.
- Large binaries and anything not needed to build or run the project.

The official test data in `data/test/` is committed unchanged.

## 9. Pre-push checklist

- [ ] `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` show shiv-eshwar
- [ ] `git config core.hooksPath` prints `.githooks`
- [ ] Section 5 checks pass: only shiv-eshwar, messages clean
- [ ] No secrets or generated files staged
- [ ] Commit message follows Conventional Commits
- [ ] Pushed immediately after committing
