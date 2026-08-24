#!/usr/bin/env bash
set -euo pipefail

# Gera o binário standalone do JCL Clicker (tarball com PyInstaller --onefile).
#
# Este é o ÚNICO alvo que usa PyInstaller: precisa embutir Python + GTK4 para
# rodar em máquinas sem dependências pré-instaladas — é naturalmente o
# artefato mais pesado (veja README, seção de instalação).
#
# Redução de tamanho (de ~92MB para poucos dezenas de MB):
#   - hooksconfig do gi: NÃO coleta temas de ícones (~135MB!), temas GTK3
#     e traduções além de pt_BR — o hook coleta TUDO do sistema por padrão
#   - filtro pós-Análise no spec: remove GTK3 (o app usa só GTK4)
#   - --exclude-module para módulos não usados
#
# UPX: o PyInstaller desativa UPX fora do Windows por padrão (causa
# segfaults conhecidos em shared libraries dlopen'd no Linux) e forçar via
# PYINSTALLER_FORCE_UPX é arriscado — por isso não é usado aqui. O arquivo
# interno do --onefile já sai comprimido com zlib.
#
# O ydotool vendorizado é embutido via o spec e resolvido em runtime por
# app/mouse.py através de sys._MEIPASS.

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

# --- spec gerado sob medida (hooksconfig não é exposto na CLI do PyInstaller) ---
cat > "$BUILD_DIR/jcl-clicker.spec" << 'SPEC'
# -*- mode: python ; coding: utf-8 -*-
import os

REPO = os.environ["JCL_REPO_DIR"]

a = Analysis(
    [os.path.join(REPO, "app", "main.py")],
    pathex=[REPO],
    binaries=[
        (os.path.join(REPO, "vendor", "ydotool", "ydotool"), "vendor/ydotool"),
        (os.path.join(REPO, "vendor", "ydotool", "ydotoold"), "vendor/ydotool"),
    ],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={
        "gi": {
            # padrão do hook coleta TODOS os temas de ícones do sistema
            # (135MB+): o app não carrega ícones por nome, então nenhum
            "icons": [],
            # temas GTK do sistema: GTK4 já traz Adwaita embutido
            "themes": [],
            # traduções só do idioma do app
            "languages": ["pt_BR"],
        },
    },
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc",
        "pydoc_data",
        "curses",
        "lib2to3",
        "pytest",
    ],
    noarchive=False,
)


def _keep(entry):
    # remove GTK3 inteiro (o app usa somente GTK4) e sobras de temas
    dest = entry[0]
    forbidden = ("gtk-3", "gdk-3", "Gtk-3", "Gdk-3", "share/themes", "share/icons")
    return not any(token in dest for token in forbidden)


a.binaries = [entry for entry in a.binaries if _keep(entry)]
a.datas = [entry for entry in a.datas if _keep(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="jcl-clicker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
SPEC

cd "$REPO_DIR"
JCL_REPO_DIR="$REPO_DIR" "$PY" -m PyInstaller \
    --noconfirm \
    --distpath "$STAGE_DIR" \
    --workpath "$BUILD_DIR/build" \
    "$BUILD_DIR/jcl-clicker.spec"

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