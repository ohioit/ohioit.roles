#!/bin/sh
set -e

if ! command -v mise >/dev/null 2>&1; then
  exit 0
fi

if [ -f ".mise.toml" ]; then
  mise trust -y
  mise install -y
fi

add_line_if_missing() {
  file="$1"
  line="$2"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if ! grep -Fq "$line" "$file" 2>/dev/null; then
    printf '\n%s\n' "$line" >> "$file"
  fi
}

# shellcheck disable=SC2016
add_line_if_missing "$HOME/.bashrc" 'eval "$(mise activate bash)"'
# shellcheck disable=SC2016
add_line_if_missing "$HOME/.zshrc" 'eval "$(mise activate zsh)"'
add_line_if_missing "$HOME/.config/fish/config.fish" 'mise activate fish | source'
