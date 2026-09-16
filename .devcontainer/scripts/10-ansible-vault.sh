#!/bin/bash
set -e

ANSIBLE_CONFIG="${HOST_HOME}/.ansible.cfg"
VAULT_STANDARD="${HOST_HOME}/.vault-pass.standard"
VAULT_PRIVILEGED="${HOST_HOME}/.vault-pass.privileged"

# Function to create symbolic link if the file exists
create_symlink() {
    local src=$1
    local dest=$2
    if [ -f "$src" ]; then
        echo "Creating symbolic link from $src to $dest"
        ln -sfn "$src" "$dest"
    else
        echo "File $src does not exist. Skipping symlink creation."
    fi
}

# Check and create symlinks for .ansible.cfg and .vault-pass files
create_symlink "$ANSIBLE_CONFIG" "$HOME/.ansible.cfg"
create_symlink "$VAULT_STANDARD" "$HOME/.vault-pass.standard"
create_symlink "$VAULT_PRIVILEGED" "$HOME/.vault-pass.privileged"
