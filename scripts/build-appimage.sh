#!/usr/bin/env bash
set -euo pipefail

# Gera o AppImage do JCL Clicker.
#
# Reaproveita o binário standalone (PyInstaller --onefile, self-contained),
# monta a AppDir com o .desktop e o ícone e empacota com o appimagetool.
# Se o binário standalone ainda não existir, o build-standalone.sh é
# executado primeiro automaticamente.

VERSION="${1:?Uso: $0 <versão>}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$REPO_DIR/dist"
APPDIR="$DIST_DIR/appimage/AppDir"
BIN_NAME="jcl-clicker"
ICON_NAME="jcl-clicker.png"
OUTPUT="$DIST_DIR/jcl-clicker-${VERSION}-x86_64.AppImage"

STAGE_BIN="$DIST_DIR/standalone/jcl-clicker/$BIN_NAME"
if [ ! -f "$STAGE_BIN" ]; then
    echo "Binário standalone não encontrado — gerando antes..."
    "$REPO_DIR/scripts/build-standalone.sh" "$VERSION"
fi

ICON_SRC="$REPO_DIR/packaging/icons/$ICON_NAME"
if [ ! -f "$ICON_SRC" ]; then
    echo "ERRO: ícone obrigatório não encontrado em $ICON_SRC" >&2
    exit 1
fi

# --- appimagetool: usa o do PATH ou baixa uma cópia para o cache de build ---
TOOL_DIR="$DIST_DIR/appimage/tools"
mkdir -p "$TOOL_DIR"
TOOL_IS_APPIMAGE=0
if command -v appimagetool >/dev/null 2>&1; then
    APPIMAGETOOL="$(command -v appimagetool)"
else
    APPIMAGETOOL="$TOOL_DIR/appimagetool-x86_64.AppImage"
    if [ ! -f "$APPIMAGETOOL" ]; then
        echo "Baixando appimagetool..."
        curl -fL --retry 3 -o "$APPIMAGETOOL" \
            "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x "$APPIMAGETOOL"
    fi
    TOOL_IS_APPIMAGE=1
fi

run_appimagetool() {
    if [ "$TOOL_IS_APPIMAGE" = "1" ]; then
        # --appimage-extract-and-run: funciona mesmo sem FUSE instalado
        "$APPIMAGETOOL" --appimage-extract-and-run "$@"
    else
        "$APPIMAGETOOL" "$@"
    fi
}

# --- monta a AppDir ---
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"

cp "$STAGE_BIN" "$APPDIR/usr/bin/$BIN_NAME"
chmod 755 "$APPDIR/usr/bin/$BIN_NAME"

cp "$ICON_SRC" "$APPDIR/$BIN_NAME.png"   # Icon=jcl-clicker do .desktop
cp "$ICON_SRC" "$APPDIR/.DirIcon"
cp "$REPO_DIR/packaging/autoclicker.desktop" "$APPDIR/"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/jcl-clicker" "$@"
EOF
chmod 755 "$APPDIR/AppRun"

# --- empacota ---
cd "$DIST_DIR/appimage"
ARCH=x86_64 run_appimagetool --comp gzip "AppDir" "$OUTPUT"

echo
echo "AppImage gerado:"
ls -lh "$OUTPUT"