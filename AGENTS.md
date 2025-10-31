PROJECT_DIR = rcdv
PROJECT_NAME = codex-github-integration

# Agent Playbook
Reference guide for AI coding agents working inside this repository.

## Environment Snapshot
- Running inside a privileged Docker-in-Docker container at `/workspace`
- Full sudo access; network is open; filesystem has no sandbox restrictions
- Default shell is `bash`; commands run via `["bash","-lc","<cmd>"]`
- Launch command for context:
  ```bash
  docker run -it --rm \
    -v "$PROJ_DIR":/workspace \
    --privileged \
    -v "$HOME/.config/codex":/home/dev/.config/codex \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e OPENAI_API_KEY \
    -w /workspace \
    "$(basename "$PROJ_DIR")" \
    bash -lc "codex --yolo"
  ```

## Project Layout
- `.devcontainers/Dockerfile` — Container environment definition
- `.devcontainers/codex-functions.sh` — Helper functions (`codexbuild`, `codexstart`)
- `.devcontainers/CODEX-SETUP.md` — Setup and usage documentation
- `AGENTS.md` — This playbook

## Workflow Expectations
- Always create a feature branch per task: `git checkout -b feature/<task>`
- Work freely and commit as needed; keep messages in `<type>: <description>` format (`feat`, `fix`, `test`, …)
- Maintain a clean branch before hand-off: tidy history, code ready for review, and thorough self-testing
- After validation, request approval to squash-merge into `develop`

## Repository Workflow
- Project coordinates: `PROJECT_DIR` and `PROJECT_NAME` are declared at the top of this file.
- Environment variables: only `GITHUB_USER` (GitHub username tied to the PAT) and `GITHUB_KEY` (fine-grained PAT) are injected.

1. Create the remote via the MCP `create_repository` tool (repos toolset). Use the sandbox org declared above (`owner="rcdv"`, same as `PROJECT_DIR`) and `name="$PROJECT_NAME"`; this calls GitHub’s `/orgs/{owner}/repos` endpoint, which is what our fine-grained PAT is scoped for.
2. Initialize locally and branch: run `git init`, stage the starter files, and `git checkout -b feature/<task>` (or `fix/<bug>`). The first push from this branch seeds the repo; subsequent work should continue on feature/fix branches rather than `main`.
3. Wire the remote using the coordinates above:
   ```bash
   git remote add origin https://github.com/<PROJECT_DIR>/<PROJECT_NAME>.git
   ```
4. Push commits (always from your feature/fix branch):
   ```bash
   git push -u origin feature/<task>
- GitHub sandbox automation supports: creating repositories via the MCP `create_repository` tool, initializing a matching local repo (`git init`, first commit), wiring the remote to the sandbox org, and pushing commits using the scoped PATH.
- GitHub MCP capabilities (toolsets you can rely on):
  - **Repositories (`repos` toolset)** – Create repositories and branches, list commits/tags, push file updates (`create_repository`) - you should push from local (using remote).
  - **Issues (`issues` toolset)** – Search, read, create, update, label, comment on, and close/reopen issues; mark duplicates or change state reasons.
  - **Pull Requests (`pull_requests` toolset)** – Open or update PRs, request reviews, list commits/files, submit reviews, merge (`merge_pull_request` supports merge/squash/rebase), and manage draft state.
  - **Actions (`actions` toolset)** – Inspect workflows (`list_workflows`), track runs/jobs/logs, download artifacts, rerun or cancel workflows, and trigger manual runs (`run_workflow`, `rerun_workflow_run`, `cancel_workflow_run`, etc.).
   ```

## Operating Guidelines for Agents
- Prefer `rg`/`rg --files` for searches; fall back to other tools only if necessary
- Set the `workdir` parameter on every shell invocation; avoid `cd` chains
- Default to ASCII when editing; introduce non-ASCII only if the file already uses it and it adds value
- Use `apply_patch` for targeted manual edits; reserve generators or formatters for bulk/auto changes
- Do not revert user-authored changes; never run destructive git commands unless explicitly instructed
- For multi-step tasks, create a plan (skip only the most trivial requests) and update it as steps complete

## Coding & Documentation Standards
- Favor self-explanatory code and naming; add comments only when the intent is non-obvious
- Keep documentation minimal—capture essential “why” decisions, architectural nuances, or setup requirements
- Apply DRY principles and prefer configuration-as-code over prose

## Testing & Validation
- Execute relevant test suites or checks before asking for review
- Confirm no breaking changes and that new functionality is covered
- Document any unverified areas when reporting back to the user

## Tooling & MCP Notes
- You may add or configure MCP servers; place project-specific config in `~/.config/codex/config.toml`
- Research integrations as needed to accelerate tasks; keep configurations under version control when appropriate

## Communication & Handoff
- Responses should be concise, action-focused, and reference paths with line numbers when citing code (`path/to/file:42`)
- Always autonomously proceed with logical follow-up steps (tests, builds, commits) before handing work back to the user

## Safety & Ephemeral Storage
- YOLO mode: commands run without approval prompts—exercise judgment before destructive actions
- Container state is ephemeral; changes outside `/workspace` are lost after exit
