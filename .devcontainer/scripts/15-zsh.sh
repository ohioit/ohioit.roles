#!/bin/bash
set -e

ZSHRC="$HOME/.zshrc"
OH_MY_ZSH_CUSTOM="${HOME}/.oh-my-zsh/custom"

# List of plugins
PLUGINS=(
  ansible
  colorize
  copyfile
  copypath
  dirhistory
  docker
  git
  ubuntu
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# List of aliases
ALIASES=(
  'kubectl="kubecolor"'
)

# List of exports
EXPORTS=(
  'EDITOR=vim'
)

# List of custom ZSH plugins with their Git repository URLs
CUSTOM_PLUGINS=(
  "https://github.com/zsh-users/zsh-syntax-highlighting.git"
  "https://github.com/zsh-users/zsh-autosuggestions.git"
  # Add more plugins here
)

# Function to update plugins
update_plugins() {
  local plugins_line="plugins=(${PLUGINS[*]})"
  if grep -q "^plugins=" "$ZSHRC"; then
    sed -i "s/^plugins=.*/$plugins_line/" "$ZSHRC"
  else
    echo "$plugins_line" >> "$ZSHRC"
  fi
}

# Function to update aliases
update_aliases() {
  local aliases_section="# Custom aliases"
  for alias in "${ALIASES[@]}"; do
    aliases_section+="\nalias $alias"
  done

  if ! grep -q "^# Custom aliases" "$ZSHRC"; then
    echo -e "\n$aliases_section" >> "$ZSHRC"
  else
    sed -i "/^# Custom aliases/,+$((${#ALIASES[@]} + 1))d" "$ZSHRC"
    echo -e "\n$aliases_section" >> "$ZSHRC"
  fi
}

# Function to update exports
update_exports() {
  local exports_section="# Custom exports"
  for export in "${EXPORTS[@]}"; do
    exports_section+="\nexport $export"
  done

  if ! grep -q "^# Custom exports" "$ZSHRC"; then
    echo -e "\n$exports_section" >> "$ZSHRC"
  else
    sed -i "/^# Custom exports/,+$((${#EXPORTS[@]} + 1))d" "$ZSHRC"
    echo -e "\n$exports_section" >> "$ZSHRC"
  fi
}

# Function to install custom ZSH plugins
install_custom_plugins() {
  mkdir -p "${OH_MY_ZSH_CUSTOM}/plugins"
  for plugin_url in "${CUSTOM_PLUGINS[@]}"; do
    if [[ "$plugin_url" == *.git ]]; then
      plugin_name=$(basename "$plugin_url" .git)
    else
      plugin_name=$(basename "$plugin_url")
    fi
    if [ ! -d "${OH_MY_ZSH_CUSTOM}/plugins/${plugin_name}" ]; then
      git clone --depth=1 "$plugin_url" "${OH_MY_ZSH_CUSTOM}/plugins/${plugin_name}"
    else
      echo "Plugin ${plugin_name} already installed."
    fi
  done
}

# Update .zshrc
update_plugins
update_aliases
update_exports
install_custom_plugins

echo "Updated ~/.zshrc and installed custom plugins successfully."
