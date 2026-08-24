#!/usr/bin/env bash
set -e

INSTALL_DIR="${1:-$HOME/.local/opt/jcl-clicker}"

mkdir -p "$INSTALL_DIR"
cp jcl-clicker jcl-clicker.png "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/jcl-clicker"

mkdir -p "$HOME/.local/share/applications"
sed "s|/opt/jcl-clicker|$INSTALL_DIR|g" autoclicker.desktop > "$HOME/.local/share/applications/autoclicker.desktop"
chmod +x "$HOME/.local/share/applications/autoclicker.desktop"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
echo "Instalado em $INSTALL_DIR"
