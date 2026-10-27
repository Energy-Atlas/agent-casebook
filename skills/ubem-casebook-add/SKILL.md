---
name: ubem-casebook-add
description: >-
  Add a case record to the UBEM Agent Casebook (expected agent behavior in
  urban building energy modeling workflows). Drafts the case from the user's
  input, validates it, commits it on a local branch, previews it for approval,
  then pushes the branch and opens a pull request. Use when the user asks to
  add, record, or file a UBEM casebook case, or runs
  `ubem-casebook-add [case name] [category] [context] [fetch-context=false] [skip-approval=false]`.
argument-hint: "[case-name] [category] [context] [fetch-context=false] [skip-approval=false]"
---

# ubem-casebook-add

Add one case to the UBEM Agent Casebook repository: draft it, validate it,
commit it on its own local branch, and, once approved, push the branch and open
a pull request.

```text
ubem-casebook-add [case name] [case category] [context] [fetch-context=false] [skip-approval=false]
```

Work through the steps in order. Do not skip the preflight checks, the
validation, or the confidentiality check, whatever the options say.

## 1. Parse the arguments

Read the text that follows the skill invocation.

- **Options.** `fetch-context=<bool>` and `skip-approval=<bool>`, in any
  position. Accept `true/false`, `yes/no`, `1/0`, any case, and treat a bare
  `fetch-context`, `--fetch-context`, `skip-approval`, or `--skip-approval` as
  `true`. Both default to `false`.
- **Explicit fields.** `name=<slug>`, `category=<category>`, and
  `context=<text>` are accepted and take precedence over positional values.
- **Positional values**, after removing options and explicit fields:
  - a token that equals a casebook category is the **category**;
  - a leading kebab-case token (lowercase letters, digits, hyphens, no spaces)
    that is not a category is the **case name**;
  - everything else, quoted or not, is the **context**.
- If a token could be either a name or context, treat it as context and infer
  the name later.

### Where the case content may come from

- `fetch-context=false` (default): use **only the text the user passed to the
  skill**. Do not draw case content from earlier conversation, open files,
  tool outputs, or other repositories. Reading the casebook repository itself
  for format, rules, existing cases, and tags is always allowed.
  If the context is empty or too thin to write a Situation and Expected
  behavior, ask the user for more, or let them cancel. Do not fill gaps by
  guessing.
- `fetch-context=true`: also use the conversation history, files and tool
  outputs in this session, and project context you can see, to determine the
  case. Keep a list of the sources you used; it goes in the preview and the
  pull request.

Either way, the scenario itself (the situation, what was observed, and the
expected and undesirable behavior) must come from those sources. You may add
general domain knowledge to explain it, mainly in Rationale, along with
references you can verify. Say in the preview what you added beyond the input.

## 2. Find the casebook repository

Do this before writing anything or running any git command that changes state.

A directory is the casebook when it is a git work tree that contains all of
`scripts/casebook.py`, `templates/case.md`, `docs/cases/`, and `AGENTS.md`, and
its `mkdocs.yml` has `site_name: UBEM Agent Casebook`.

Check, in order:

1. the git top level (`git rev-parse --show-toplevel`) of the shell's working
   directory and, if your session has a different project directory, of that
   directory too;
2. the path in the `UBEM_CASEBOOK_DIR` environment variable, if set.

Do not search the disk beyond these. If neither is the casebook, **stop and
warn** that the casebook repository was not found, then ask the user to either
give the path to a local checkout (and check it as above) or cancel. If they
cancel, do nothing else. Do not clone the repository unless the user asks you
to and gives the URL.

Call the result `REPO`. Then:

- Read `REPO/AGENTS.md`. It is the authority on case format, writing,
  confidentiality, and commit conventions; where it disagrees with this skill,
  follow AGENTS.md.
- Read `REPO/templates/case.md` and the `CATEGORIES` list in
  `REPO/scripts/casebook.py`. That list is authoritative; at the time of
  writing it is `preprocessing`, `model-config`, `simulation`, `validation`,
  `calibration`, `results`, `scenarios`.
- Pick the Python interpreter: `REPO/.venv/Scripts/python` (Windows) or
  `REPO/.venv/bin/python` if it exists, otherwise `python3` or `python`.
  The validator needs PyYAML. The site build needs everything in
  `REPO/requirements.txt` (MkDocs and the Material theme). If PyYAML is
  missing, ask the user whether to install `requirements.txt` into a
  temporary virtual environment, or cancel. Never install packages globally.

## 3. Prepare a branch without touching the user's checkout

The user's checkout may be on another branch or have uncommitted changes.
Leave it alone: build the case in a separate worktree.

1. **Base.** If `git -C REPO remote get-url origin` succeeds, run
   `git -C REPO fetch origin main` and use `origin/main`. If the fetch fails,
   warn that the remote is unreachable and use local `main`. Without a
   remote, use local `main`.
2. **Category.** Use the given one if it is in `CATEGORIES`; if it is not, say
   so and ask. Otherwise infer the workflow stage where the behavior occurs.
   Never add a category.
3. **Case name.** Use the given one if it is kebab-case; otherwise derive a
   short kebab-case name (two to four words) that names the behavior or
   situation. It must not clash with an existing case
   (`git -C REPO ls-tree -r --name-only <base> docs/cases`).
4. **Branch.** `case/<category>/<case-name>`. Check that it exists neither
   locally (`git -C REPO rev-parse --verify --quiet refs/heads/<branch>`) nor
   on `origin` (`git -C REPO ls-remote --heads origin <branch>`; skip this if
   the remote is unreachable). If it does, ask the user for a different name
   or cancel.
5. **Worktree**, in a temporary directory outside the repository. Use
   `--no-track` so the branch never tracks `main`:

   ```bash
   git -C REPO worktree add --no-track -b <branch> <tmpdir>/<case-name> <base>
   ```

   Call it `WT`. All file edits, validation, and commits happen in `WT`.
   If the name or category changes later, rename the branch with
   `git -C WT branch -m <new-branch>`.

## 4. Draft the case

1. **Search for duplicates.** Look through `WT/docs/cases/` for a case that
   already covers the behavior. If one does, tell the user and ask whether to
   continue, adjust the scope, or cancel.
2. **Id.** Run `<python> scripts/casebook.py next-id` in `WT`.
3. **Write `WT/docs/cases/<category>/<case-name>.md`** from the template,
   following AGENTS.md:
   - front matter with the id from `next-id`, today's date, `stage` equal to
     the category, and kebab-case tags, reusing existing tags where they fit
     (`grep -h "^tags:" -r docs/cases`);
   - `origin`, `data_availability`, and `eval_readiness` from the allowed
     values; choose conservatively and say in the preview why;
   - the required sections, plus optional ones when you can write them from
     the allowed sources (see step 1), without the `(optional)` suffix and
     without the template's prompt text. Without an Evaluation potential
     section, `eval_readiness` is `conceptual`;
   - links to related cases as relative links;
   - only references you can verify; no invented citations, URLs, or data.
4. **Confidentiality check.** The repository is public. If the draft would
   contain real addresses, owner or person names, account or meter ids,
   building-identifying details from private data, excerpts of private or
   copyrighted material, or anything the user marked confidential, **stop and
   ask**, even when `skip-approval=true`. Offer a generalized wording.

## 5. Validate and commit

Inside `WT`:

```bash
<python> scripts/casebook.py check
```

```bash
<python> -m mkdocs build --strict --site-dir <tmpdir>/site
```

Tell problems with the case apart from problems with the environment:

- **Environment problems.** MkDocs, the Material theme, or another package
  from `requirements.txt` is missing, or the same build also fails on the
  base. These are not reasons to stop. Note that the strict build did not run
  locally and that CI will run it, and continue. Do not install packages for
  this without the user's agreement.
- **Problems with the case.** Fix the case and rerun until both checks pass.
  If you cannot make them pass, do not commit: report the errors, remove the
  worktree and branch, and stop.

Then commit only the case file, with the message format from AGENTS.md (add
the commit trailers your agent normally uses):

```bash
git -C WT add docs/cases/<category>/<case-name>.md
git -C WT commit -m "feat(<category>): add <case-name> case"
```

The branch is local at this point. No approval is needed up to here.

## 6. Preview and approval

If `skip-approval=true`, go to step 7.

Otherwise show the user:

- branch, base, and commit hash;
- id, category, and case name, each marked as given or inferred;
- the choices for `origin`, `data_availability`, and `eval_readiness`, with
  one line of reasoning each;
- the context sources used (the skill input only, or the list from
  `fetch-context=true`);
- validation results, including any check that did not run locally and why;
- what you added beyond the input, and confidentiality findings if any;
- the full case file.

Then ask the user to choose (use your question tool if you have one):

- **Approve**: push the branch and open a pull request (step 7).
- **Revise**: apply the requested changes in `WT`, revalidate, amend the
  commit after staging, and preview again. If the case name or category
  changed, move the file, rename the branch, and amend with the new commit
  message; otherwise `git -C WT commit --amend --no-edit` is enough.
- **Keep local**: stop. The branch stays local; tell the user its name and the
  explicit push command (`git -C REPO push -u origin <branch>`).
- **Discard**: remove the worktree and delete the branch
  (`git -C REPO branch -D <branch>`). Only on this explicit choice.

## 7. Push and open the pull request

1. **Remote.** If `origin` is missing, warn that there is nowhere to push; the
   branch stays local. Stop.
2. **Push.**

   ```bash
   git -C WT push -u origin case/<category>/<case-name>
   ```

   If the push fails for authentication, permission (e.g. 403, "permission
   denied", no write access), network, or branch-protection reasons, or your
   own tool-permission system refuses it, **warn** with the error message,
   keep the branch local, and give the user the push command to run once
   access is sorted out. Do not look for a workaround: do not change
   credentials, run `gh auth login` for them, force-push, or push to another
   remote. You may
   mention that a contributor without write access can push to a fork and open
   the pull request from there.
3. **Pull request.** If `origin` is not a GitHub repository (a local path,
   GitLab, or another host), do not run `gh`: report that the branch is
   pushed and that the pull request has to be opened on that host. Otherwise,
   if the GitHub CLI is available and `gh auth status` succeeds:

   ```bash
   gh pr create --repo <owner>/<repo> --base main --head case/<category>/<case-name> \
     --title "feat(<category>): add <case-name> case" --body-file <tmpdir>/pr-body.md
   ```

   `<owner>/<repo>` comes from the `origin` URL. The body gives the case id,
   title, category, file path, a two- to three-sentence summary, what was
   inferred, the context sources, and validation results, plus the
   pull-request trailer your agent normally uses.

   If `gh` is missing, unauthenticated, or the call fails, warn: the branch is
   pushed but no pull request was opened. For a GitHub remote, give the compare
   URL `https://github.com/<owner>/<repo>/compare/main...case/<category>/<case-name>?expand=1`.

Never push to `main`, merge the pull request, or enable auto-merge.

## 8. Clean up and report

Remove the worktree (`git -C REPO worktree remove <WT>`) and the rest of the
temporary directory (site build output, PR body file); the branch remains.
Leave the user's checkout as it was.

Report in a few lines: case id and title, file path, branch, commit, and the
pull request URL, or else where the work stopped and why (kept local, push
failed, no PR). With `skip-approval=true`, include the inferred name and
category and the context sources, since the user has not seen a preview.

If another open pull request takes the same id first, the later one renumbers
its case before merging; CI reports duplicate ids.
