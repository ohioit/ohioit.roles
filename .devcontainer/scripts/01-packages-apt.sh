#!/bin/bash
set -e

# Sudo required
REQUIRES_SUDO=true

DEBIAN_FRONTEND=noninteractive
PKG_MGR=apt

# List of packages to install
PACKAGES=(
    bat
    btop
    dnsutils
    fd-find
    fping
    iputils-ping
    ncat
    nmap
    tldr
    vim
    which
    xclip
    xsel
)

: "${PKG_MGR:?PKG_MGR is not set}"
: "${PACKAGES:?PACKAGES is not set}"

# Update and install packages
${PKG_MGR} update && \
${PKG_MGR} -y full-upgrade && \
${PKG_MGR} install -y "${PACKAGES[@]}"

# Clean up steps
${PKG_MGR} autoclean -y && \
${PKG_MGR} autoremove -y --purge && \
rm -Rf /var/cache/apt/archives

unset DEBIAN_FRONTEND
