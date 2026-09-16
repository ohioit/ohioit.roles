#!/bin/sh
set -e

if ! command -v uv >/dev/null 2>&1; then
  if command -v mise >/dev/null 2>&1; then
    mise exec -- uv sync
    exit 0
  fi
  echo "uv not found on PATH" >&2
  exit 0
fi

uv sync
