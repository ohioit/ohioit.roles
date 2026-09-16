#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Define the paths to the requirement files and installation directories
COLLECTIONS_REQUIREMENTS="${PROJECT_HOME}/collections/requirements.yml"
ROLES_REQUIREMENTS="${PROJECT_HOME}/roles/requirements.yml"
COLLECTIONS_PATH="${PROJECT_HOME}/collections"
ROLES_PATH="${PROJECT_HOME}/roles"
COLLECTIONS_DIR="${PROJECT_HOME}/collections/ansible_collections"

# Remove the ansible_collections directory if it exists
if [[ -d "$COLLECTIONS_DIR" ]]; then
    echo "Removing existing $COLLECTIONS_DIR..."
    rm -rf "$COLLECTIONS_DIR"
fi

# Check if the collections requirements file exists and run the ansible-galaxy command
if [[ -f "$COLLECTIONS_REQUIREMENTS" ]]; then
    echo "Installing Ansible collections from $COLLECTIONS_REQUIREMENTS..."
    ansible-galaxy collection install -r "$COLLECTIONS_REQUIREMENTS" -p "$COLLECTIONS_PATH" --force
else
    echo "Collection requirements file not found at $COLLECTIONS_REQUIREMENTS"
fi

# Check if the roles requirements file exists and run the ansible-galaxy command
if [[ -f "$ROLES_REQUIREMENTS" ]]; then
    echo "Installing Ansible roles from $ROLES_REQUIREMENTS..."
    ansible-galaxy role install -r "$ROLES_REQUIREMENTS" -p "$ROLES_PATH" --force
else
    echo "Role requirements file not found at $ROLES_REQUIREMENTS"
fi
