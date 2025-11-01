#!/bin/bash

codexbuild() {
  local PROJ_DIR=""
  local flags=()

  for arg in "$@"; do
    if [[ "$arg" == -- ]]; then
      continue
    fi
    if [[ "$arg" == -* ]]; then
      flags+=("$arg")
    else
      if [[ -z "$PROJ_DIR" ]]; then
        PROJ_DIR="$arg"
      else
        flags+=("$arg")
      fi
    fi
  done

  PROJ_DIR="${PROJ_DIR:-$PWD}"
  PROJ_DIR="$(cd "$PROJ_DIR" && pwd)"

  local UID_VAL
  local GID_VAL
  UID_VAL="$(id -u)"
  GID_VAL="$(id -g)"

  pushd "$PROJ_DIR" >/dev/null
  docker build \
    --build-arg HOST_UID="$UID_VAL" \
    --build-arg HOST_GID="$GID_VAL" \
    -f "$PROJ_DIR/Dockerfile" \
    -t "$(basename "$PROJ_DIR")" \
    "${flags[@]}" \
    "$PROJ_DIR"
  popd >/dev/null
}

codexstart() {
  local PROJ_DIR="${1:-$PWD}"
  local MODE="${2:-auto}"
  PROJ_DIR="$(cd "$PROJ_DIR" && pwd)"

  pushd "$PROJ_DIR" >/dev/null

  if [ "$MODE" = "tty" ]; then
    docker run -it --rm \
      --privileged \
      -v "$PROJ_DIR":/workspace \
      -v "$HOME/.codex":/home/dev/.codex \
      -v "$HOME/.gitconfig":/home/dev/.gitconfig:ro \
      --group-add "$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo 0)" \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$HOME/.ssh":/home/dev/.ssh:ro \
      -e OPENAI_API_KEY \
      -e GITHUB_USER \
      -e GITHUB_KEY \
      -w /workspace \
      "$(basename "$PROJ_DIR")" bash
  else
    docker run -it --rm \
      --privileged \
      -v "$PROJ_DIR":/workspace \
      -v "$HOME/.codex":/home/dev/.codex \
      -v "$HOME/.gitconfig":/home/dev/.gitconfig:ro \
      --group-add "$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo 0)" \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$HOME/.ssh":/home/dev/.ssh:ro \
      -e OPENAI_API_KEY \
      -e GITHUB_USER \
      -e GITHUB_KEY \
      -w /workspace \
      "$(basename "$PROJ_DIR")" \
      bash -lc "codex --yolo"
  fi

  popd >/dev/null
}

export -f codexbuild
export -f codexstart
