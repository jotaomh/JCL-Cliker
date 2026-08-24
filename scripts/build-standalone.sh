#!/usr/bin/env bash
set -euo pipefail

# Gera o binário standalone do JCL Clicker (tarball com PyInstaller).
#
# Este é o ÚNICO alvo que usa PyInstaller --onefile: precisa embutir
# Python + GTK4 + tudo mais para rodar em máquinas sem dependências
# pré-instaladas, então é naturalmente o artefato mais pesado.
#
# O ydotool vendorizado é embutido via --add-binary e resolvido em runtime
# por app/mouse.py através de sys._MEIPASS.

VERSION="${1:?Uso: $0 <versão>}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_DIR/dist/standalone"
STAGE_DIR="$BUILD_DIR/jcl-clicker"
BIN_NAME="jcl-clicker"
ICON_NAME="jcl-clicker.png"

if [ -x "$REPO_DIR/venv/bin/python" ]; then
    PY="$REPO_DIR/venv/bin/python"
else
    PY="$(command -v python3)"
fi

for binary in ydotool ydotoold; do
    if [ ! -f "$REPO_DIR/vendor/ydotool/$binary" ]; then
        echo "ERRO: $REPO_DIR/vendor/ydotool/$binary não encontrado." >&2
        exit 1
    fi
done

ICON_SRC="$REPO_DIR/packaging/icons/$ICON_NAME"
if [ ! -f "$ICON_SRC" ]; then
    echo "ERRO: ícone obrigatório não encontrado em $ICON_SRC" >&2
    exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$STAGE_DIR"

if command -v upx >/dev/null 2>&1; then
    echo "UPX disponível ($(upx --version | head -1)) — comprimindo binário."
else
    echo "AVISO: UPX não encontrado no PATH — binário sai sem compressão extra." >&2
fi

cd "$REPO_DIR"
"$PY" -m PyInstaller \
    --onefile \
    --name "$BIN_NAME" \
    --add-binary "$REPO_DIR/vendor/ydotool/ydotool:vendor/ydotool" \
    --add-binary "$REPO_DIR/vendor/ydotool/ydotoold:vendor/ydotool" \
    --exclude-module tkinter \
    --exclude-module unittest \
    --exclude-module pydoc \
    --exclude-module pydoc_data \
    --exclude-module curses \
    --exclude-module lib2to3 \
    --exclude-module pytest \
    --distpath "$STAGE_DIR" \
    --workpath "$BUILD_DIR/build" \
    --specpath "$BUILD_DIR" \
    app/main.py

cp "$REPO_DIR/packaging/standalone/autoclicker.desktop" "$STAGE_DIR/"
cp "$REPO_DIR/packaging/standalone/install.sh" "$STAGE_DIR/"
cp "$REPO_DIR/packaging/standalone/README.txt" "$STAGE_DIR/"
cp "$ICON_SRC" "$STAGE_DIR/$ICON_NAME"
chmod +x "$STAGE_DIR/install.sh"

cd "$BUILD_DIR"
TARBALL="$REPO_DIR/dist/jcl-clicker-linux-${VERSION}-standalone.tar.gz"
tar -czf "$TARBALL" jcl-clicker

echo
echo "Arquivo standalone gerado:"
ls -lh "$TARBALL"