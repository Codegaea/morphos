# Instructions for coding agents (Claude Code, Codex and others)

This repository is **MORPHOS**, Codegaea's categorical reasoning OS: "a persistent probabilistic categorical reasoning engine" (`README.md`). Knowledge is stored as categories enriched over [0,1]: concepts are objects, relationships are typed morphisms with proof terms and truth degrees, analogies are functors found by CSP search, belief revision runs on a Heyting algebra, and the shape of a domain is measured by persistent homology. It is Python: the engine in `engine/`, a FastAPI server (`server.py`, Swagger at `/docs`), a CLI (`morphos_cli.py`), and one React file, `morphos-app.jsx`, that talks to the server at `http://localhost:8000` and has no build step. There is nothing to build: the sources are what ships.

Two agents may work here: **Claude** (Claude Code) and **ChatGPT** (Codex). Both follow this file. There is no hand-over document yet; `CONTRIBUTING.md` and `docs/ARCHITECTURE.md` are the closest thing.

## Read first

0. **Open pull requests and issues.**
   - `gh api 'repos/Codegaea/morphos/pulls?state=open' --jq '.[]|[.number,.head.ref,.title]|@tsv'`
   - `gh api 'repos/Codegaea/morphos/issues?state=open' --jq '.[]|select(.pull_request==null)|[.number,.title]|@tsv'`
   - An open `claude/…` or `codex/…` pull request can hold newer records than `main`: read them (`git fetch origin && git show origin/<branch>:docs/HANDOFF.md`, once that file exists). If it is your own agent's, build on that branch or ask Patrick to merge it first. If it is the other agent's, don't push to it.
1. `README.md`: what MORPHOS is, the layers, the API, "Project Status" (what is built and what isn't: the knowledge ingestion pipeline is the top open problem).
2. `CONTRIBUTING.md`: the development rules (below) and the priorities.
3. `docs/ARCHITECTURE.md`, completely: layer by layer, with the gotchas marked CRITICAL. Then `docs/MATH.md` (the definitions). `docs/REASONING_OS.md`, `docs/INTELLECTUAL_ANCESTRY.md` and `docs/REFACTOR_KERNEL_BOUNDARY.md` (a proposal, not implemented) when your work touches them.
4. Verify before changing anything (Python 3.12, as in CI):
   ```
   pip install -r requirements.txt
   python -m pytest tests/ -q                 # "190 passed"
   python -c "import server"                  # no error
   python examples/solar_system_vs_atom.py    # ends with "Done."
   python examples/electrical_vs_fluid.py     # ends with "Done."
   ```

## Ground rules

- **The tests must pass: 190 or more, 0 failures** (CONTRIBUTING, rule 1; README, "Non-negotiable rules"). Never merge code that breaks this.
- **GF(2) homology uses `_rank_gf2()`** in `engine/topology.py`, never `np.linalg.matrix_rank`, which computes rank over the reals and gives wrong Betti numbers. Don't remove the comment that says so (CONTRIBUTING, rule 2; ARCHITECTURE, "CRITICAL: GF(2) rank").
- **No SQL inside topology engine loops.** Load a `CategorySnapshot` once (CONTRIBUTING, rule 3).
- **API responses are JSON-serializable:** convert numpy types with `.tolist()` or `float()` (CONTRIBUTING, rule 4).
- **Every new public function gets at least one test; a change to a mathematical definition needs a citation** (CONTRIBUTING, rule 5).
- **The gotchas in `docs/ARCHITECTURE.md` are rules:** `add_morphism(domain_id, label, source, target, …)` takes the label second; call `make_filtration_non_decreasing()` before GUDHI's `compute_persistence()`; double-negation elimination fails on purpose for UNDETERMINED values; filtration value is `1 - truth_degree`.
- **After any edit to `morphos-app.jsx`,** run the brace and paren balance check in `docs/ARCHITECTURE.md` ("Layers 5 & 6"); both must print 0.
- **Where new code goes** (ARCHITECTURE, "OS Kernel Framing"): a data source is a driver in `engine/` that produces `Category` objects; a reasoning algorithm goes in `engine/` with a task type in `TASK_TYPES` and an endpoint; user-facing features stay in the UI or CLI, with the reasoning in `engine/`.
- **Style** (CONTRIBUTING, "Code Style"): PEP 8, type hints on public functions, docstrings on classes, standard mathematical symbols in comments.
- **The pull-request checklist** in `.github/PULL_REQUEST_TEMPLATE.md` applies to every pull request: paste the test output and tick what you ran.
- **Don't change `LICENSE`.** The repository's visibility and license are being decided separately by Patrick.
- **No secrets or personal data in the repository.** `.gitignore` keeps out `*.db`, `.env` and virtualenvs; keep it that way. `main`'s history can't be rewritten, so anything pushed there stays.

## Handoff, roadmap, notes and artifacts

- There is no handoff file yet. The first session that has something to hand over creates `docs/HANDOFF.md` (state, what was done, what is next, what waits on Patrick). The roadmap is README's "Project Status" table and CONTRIBUTING's "What We Need Most"; a session that needs more than those holds creates `docs/ROADMAP.md`. Loose notes go in `docs/NOTES.md`. Don't create empty files ahead of time.
- **Before stopping,** a session updates `docs/HANDOFF.md` on its branch so the next session can pick up, and the "Project Status" table in `README.md` if a component's status changed.
- **Material Patrick brings** from his claude.ai chats, Projects, published artifacts or Drive belongs in this repository, in its existing layout: engine code in `engine/`, its tests in `tests/`, runnable demos in `examples/`, design documents and proposals in `docs/` (like `docs/REFACTOR_KERNEL_BOUNDARY.md`), UI changes in `morphos-app.jsx`; hand-over messages in `docs/HANDOFF.md`, roadmaps in `docs/ROADMAP.md`, notes in `docs/NOTES.md`. Record the claude.ai URL of any published artifact page in `docs/HANDOFF.md`.

## Branches, pull requests and releases

- **Branches.** Claude works on `claude/…` branches: its cloud sessions can't push `main` or tags. ChatGPT/Codex works on `codex/…` branches. Open a pull request and let Patrick merge it. (CONTRIBUTING's "fork and branch" names like `feat/…` and `fix/…` are for outside contributors.)
- **One pull request at a time.** Each agent keeps one pull request open. Before asking for a merge, merge `origin/main` into your branch and resolve the conflicts yourself: Patrick merges from his phone and can't.
- **Say who wrote it.** Both agents act as Patrick's account (pmlohan), so every pull-request description and comment starts with "Written by Claude" or "Written by ChatGPT (Codex)". Then fill in `.github/PULL_REQUEST_TEMPLATE.md`.
- A pull request that changes `.github/` says so in its title: it changes the gate itself.
- **Commit messages** follow CONTRIBUTING: `feat(scope): description`, `fix(scope): description`, `math(scope): description`.
- There are no version numbers, tags or releases.

## The checks on GitHub

- **`.github/workflows/tests.yml`, job `test`, named "Quick checks"**: on Python 3.12, installs `requirements.txt`, runs `python -m pytest tests/ -v --tb=short`, checks that `server` and `engine.topology` import, and runs both examples. It runs on every pull request to `main` and every push to `main` or `dev`. To run it locally, run the commands in "Read first", step 4.
- **The Codegaea organization's ruleset `main`** (it applies to every Codegaea repository): changes reach `main` only by pull request, merged with a merge commit (the only method allowed), after "Quick checks" has passed; `main` can't be force-pushed or deleted. The ruleset waits for a check with exactly that name, so don't rename the job's `name: Quick checks` in `.github/workflows/tests.yml`, or every pull request is blocked.
- **From a Claude session** the Actions API and the runs' logs are closed; the Checks API is open.
  - The result: `gh api repos/Codegaea/morphos/commits/<sha>/check-runs --jq '.check_runs[]|[.name,.status,.conclusion,.id]|@tsv'`.
  - What failed: `gh api repos/Codegaea/morphos/check-runs/<id>/annotations --jq '.[].message'`. pytest writes no annotations, so reproduce a failure locally.
  - To run the checks again, push a commit (`git commit --allow-empty -m "Run the checks again"`).
- **Dependabot** (`.github/dependabot.yml`) watches `requirements.txt` for security updates only (no version-update pull requests), and the actions in `tests.yml`, with one pull request a month.

## Codex and other agents without Claude's tools

- **Setup:** Python 3.12 and `pip install -r requirements.txt` (GUDHI, NumPy, SciPy, FastAPI and the rest; the agent itself may have no network, so do it in the environment's setup script). Node only for the JSX balance check.
- **What waits for Claude:** reading Patrick's claude.ai chats, Projects and published artifacts. Testing `morphos-app.jsx` against a running server needs a browser.
- **Branches** are `codex/…`; descriptions and comments start with "Written by ChatGPT (Codex)".

## Working alongside the other agent

- **Claim before you start.** Comment on the GitHub issue: who you are, your branch, the files you expect to touch. If the other agent has claimed it, leave it or ask there.
- **Never change the other agent's work in progress.** Don't push to, rebase, close or take over its branch or pull request; comment instead. Reviews go in a comment headed "Review by Claude" or "Review by ChatGPT (Codex)": what you checked, what fails, how to reproduce it.
- **Shared records: merge, don't overwrite.** Both agents edit `AGENTS.md`, `README.md` (its "Project Status" table and the test count), `CONTRIBUTING.md`, the docs in `docs/` and, once it exists, `docs/HANDOFF.md`. When merging `origin/main` brings conflicts, keep both sides. If a test count changes, recompute it from what `pytest` actually runs and update README, CONTRIBUTING, the PR template and `docs/ARCHITECTURE.md` together.
- **Disagreements go to Patrick**, in the issue or pull request: the options and what each costs, in a few lines.

## Working with Patrick

- He reports problems briefly, sometimes with a screenshot. Believe the report and reproduce it first.
- He merges in the GitHub app on his Android phone: open the pull request, tap MERGE, then MERGE again on the commit-message sheet.
- He prefers that you act first, write files early and keep replies short and plain: what changed, what was tested, what he should try.
- Ask before decisions that are hard to undo: anything public (the repository is public today), anything that costs money, accounts, a license or the brand name.
