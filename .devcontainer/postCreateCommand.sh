#!/bin/bash

# Define the directory
SCRIPT_DIR="$PROJECT_HOME/.devcontainer/scripts"

echo $SCRIPT_DIR

# Check if the directory exists
if [[ -d "$SCRIPT_DIR" ]]; then
    # Find all .sh files in the directory and its subdirectories
    for script in "$SCRIPT_DIR"/*.sh; do
        # Check if the file exists
        if [[ -f "$script" ]]; then
            # Make the script executable
            chmod +x "$script"

            # Check if the script contains the REQUIRES_SUDO variable
            if grep -q 'REQUIRES_SUDO=true' "$script"; then
                echo "Running $script with sudo as it requires elevated privileges."
                sudo "$script"
            else
                echo "Running $script without sudo."
                "$script"
            fi
        fi
    done
else
    echo "Directory $SCRIPT_DIR does not exist."
fi
