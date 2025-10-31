# OpenAI Codex Minimal Docker Setup

Minimal Docker environment for running OpenAI Codex with unrestricted access.

## Quick Start

### 1. Source the helper functions

```bash
source .devcontainers/codex-functions.sh
```

Add to your `~/.bashrc` or `~/.zshrc` for persistence:
```bash
source /path/to/project/.devcontainers/codex-functions.sh
```

### 2. Set your OpenAI API key

```bash
export OPENAI_API_KEY="sk-..."
```

### 3. Build and run

```bash
codexbuild              # Build the image
codexstart              # Run Codex in YOLO mode
codexstart . tty        # Just get a shell
```

## What's Included

**Minimal installation:**
- Alpine Linux base
- Node.js + npm (for Codex CLI)
- Python 3 (for basic scripting)
- Git + SSH
- Docker CLI (Docker-in-Docker support)
- OpenAI Codex CLI (`@openai/codex`)

**No bloat:**
- No extra language runtimes
- No additional SDKs
- No unnecessary tools

## Functions

### codexbuild [PROJECT_DIR] [docker-flags...]
Build the Codex Docker image for a project.

```bash
codexbuild                    # Build for current directory
codexbuild ~/my-project       # Build for specific project
codexbuild . --no-cache       # Build with docker flags
```

### codexstart [PROJECT_DIR] [MODE]
Start Codex in a Docker container.

**Modes:**
- `auto` (default) - YOLO mode (`--yolo` flag)
- `tty` - Interactive shell without starting Codex

```bash
codexstart                    # Start Codex in YOLO mode
codexstart ~/my-project       # Start in specific project
codexstart . tty              # Just get a shell
```

## Environment Variables

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key

## Architecture

**Image naming:** Project directory basename (e.g., `my-project`)

**Volume mounts:**
- Project directory → `/workspace` (read-write)
- SSH keys → `/home/dev/.ssh` (read-only)
- Docker socket → `/var/run/docker.sock` (Docker-in-Docker)
- Codex config → `/home/dev/.config/codex` (persistent)

**User setup:**
- User: `dev` (UID/GID match host for file permissions)
- Full sudo access
- Docker group membership

## YOLO Mode

By default, `codexstart` runs Codex with the `--yolo` flag:
- No sandbox restrictions
- No approval prompts
- Full unrestricted access
- Docker container provides isolation

This is safe because the Docker container provides the security boundary.

## Examples

### Basic usage
```bash
cd ~/my-project
codexbuild
codexstart
# Codex runs in YOLO mode, ask it to implement features
```

### Debug mode
```bash
codexstart . tty
# Inside container:
codex --help
codex "write a hello world script"
```

### Custom flags
```bash
codexbuild --no-cache
```

## Dockerfile Details

**Location:** `.devcontainers/Dockerfile`

**Size:** ~570MB (Alpine + Node.js + Codex)

**Based on:** Alpine Linux (minimal)

**Installed packages:**
- nodejs, npm
- git
- curl, ca-certificates
- bash, sudo
- python3 (basic runtime)
- openssh-client
- docker (CLI only)

**Global npm packages:**
- `@openai/codex`

## Security

The Docker container provides isolation, so running Codex with `--yolo` inside is safe:
- Actions confined to container
- Only specified directories mounted
- Docker provides network boundaries
- UID/GID mapping keeps host safe

## Troubleshooting

### Codex not found
```bash
codexbuild --no-cache
```

### Docker socket permission denied
The `--group-add` flag in `codexstart` handles this automatically.

### API key not set
```bash
export OPENAI_API_KEY="sk-..."
```

### Check if running
```bash
docker ps
```

## References

- [OpenAI Codex CLI](https://github.com/openai/codex)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
