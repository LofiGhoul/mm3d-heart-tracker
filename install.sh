#!/usr/bin/env bash
# Adds "Heart Piece Tracker" to your app launcher (per-user, no root needed).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$apps" "$icons" "$HOME/.local/bin"

chmod +x "$here/heart_tracker.py"
ln -sf "$here/heart_tracker.py" "$HOME/.local/bin/mm3d-heart-tracker"
cp "$here/io.github.mm3d_heart_tracker.svg" "$icons/"

cat > "$apps/io.github.mm3d_heart_tracker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Heart Piece Tracker
Comment=See which Majora's Mask 3D Pieces of Heart you still need
Exec=python3 "$here/heart_tracker.py" %f
Icon=io.github.mm3d_heart_tracker
Terminal=false
Categories=Game;
Keywords=zelda;majora;mm3d;heart;3ds;save;
StartupWMClass=io.github.mm3d_heart_tracker
EOF

command -v update-desktop-database >/dev/null && update-desktop-database "$apps" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "${icons%/scalable/apps}" 2>/dev/null || true
echo "Installed. Launch 'Heart Piece Tracker' from your app launcher, or run: mm3d-heart-tracker"
