#!/usr/bin/env bash
set -euo pipefail

# Gera os pacotes .deb e .rpm do JCL Clicker.
#
# Estratégia: aplicativo Python NATIVO, sem PyInstaller. Os pacotes declaram
# python3/GTK4/PyGObject como dependências do sistema — embutir tudo num
# binário via PyInstaller era duplicação e deixava os pacotes com ~100MB.
# Apenas as bibliotecas puras de pip (pynput, python-xlib, six, evdev) são
# vendorizadas em /usr/lib/jcl-clicker/lib/, junto do código em
# /usr/lib/jcl-clicker/app/ e dos binários vendorizados do ydotool em
# /usr/lib/jcl-clicker/vendor/. Resultado esperado: pacotes de poucos MB.

VERSION="${1:?Uso: $0 <versão>}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_DIR/dist"
APP_DIR="$BUILD_DIR/jcl-clicker"

APP_ROOT="/usr/lib/jcl-clicker"
BIN_NAME="jcl-clicker"
ICON_NAME="jcl-clicker.png"

if [ -x "$REPO_DIR/venv/bin/python" ]; then
    PY="$REPO_DIR/venv/bin/python"
else
    PY="$(command -v python3)"
fi

rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/usr/bin" \
         "$APP_DIR$APP_ROOT/app" \
         "$APP_DIR$APP_ROOT/lib" \
         "$APP_DIR$APP_ROOT/vendor/ydotool" \
         "$APP_DIR$APP_ROOT/scripts" \
         "$APP_DIR/usr/share/applications" \
         "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

# --- código da aplicação ---
cp -a "$REPO_DIR/app/." "$APP_DIR$APP_ROOT/app/"
find "$APP_DIR$APP_ROOT/app" -type d -name "__pycache__" -prune -exec rm -rf {} +

# --- ydotool vendorizado (obrigatório: corrige clique lento no Wayland) ---
for binary in ydotool ydotoold; do
    if [ ! -f "$REPO_DIR/vendor/ydotool/$binary" ]; then
        echo "ERRO: $REPO_DIR/vendor/ydotool/$binary não encontrado." >&2
        exit 1
    fi
done
cp -a "$REPO_DIR/vendor/ydotool/." "$APP_DIR$APP_ROOT/vendor/ydotool/"

# --- script de setup de permissões Wayland ---
cp "$REPO_DIR/scripts/setup-uinput.sh" "$APP_DIR$APP_ROOT/scripts/setup-uinput.sh"
chmod 755 "$APP_DIR$APP_ROOT/scripts/setup-uinput.sh"

# --- libs puras de pip vendorizadas (leves); GTK4 e evdev ficam por conta do
# sistema. --no-deps é essencial: o pynput declara evdev>=1.3 como dependência
# transitiva no Linux, mas o evdev tem extensão C presa à versão do Python e
# por isso vem do pacote nativo da distro (python3-evdev), não daqui.
grep -iE '^(pynput|python-xlib|six)==' "$REPO_DIR/requirements.txt" \
    > "$BUILD_DIR/requirements-vendored.txt"
"$PY" -m pip install --quiet --no-compile --no-deps \
    --target "$APP_DIR$APP_ROOT/lib" \
    -r "$BUILD_DIR/requirements-vendored.txt"

# --- launcher fino em /usr/bin ---
cat > "$APP_DIR/usr/bin/$BIN_NAME" << LAUNCHER
#!/bin/sh
# JCL Clicker: usa o GTK4/PyGObject do sistema; código e libs em $APP_ROOT
export PYTHONPATH="$APP_ROOT:$APP_ROOT/lib\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m app.main "\$@"
LAUNCHER
chmod 755 "$APP_DIR/usr/bin/$BIN_NAME"

# --- desktop e ícone (ícone é obrigatório, sem pular silenciosamente) ---
cp "$REPO_DIR/packaging/autoclicker.desktop" \
   "$APP_DIR/usr/share/applications/autoclicker.desktop"

ICON_SRC="$REPO_DIR/packaging/icons/$ICON_NAME"
if [ ! -f "$ICON_SRC" ]; then
    echo "ERRO: ícone obrigatório não encontrado em $ICON_SRC" >&2
    exit 1
fi
cp "$ICON_SRC" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/$ICON_NAME"

# --- .deb via dpkg-deb ---
DEB_ROOT="$BUILD_DIR/deb/jcl-clicker_${VERSION}_amd64"
mkdir -p "$DEB_ROOT/DEBIAN"
cp -a "$APP_DIR"/* "$DEB_ROOT/"

cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: jcl-clicker
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: python3, python3-gi, gir1.2-gtk-4.0, python3-evdev
Recommends: ydotool
Maintainer: jotaomh <https://github.com/jotaomh>
Description: JCL Clicker - automação de cliques de mouse para Linux
 JCL Clicker é um auto clicker para Linux com suporte a X11 e Wayland.
 Interface gráfica em GTK4 com atalho global de teclado.
 Usa o GTK4/PyGObject do sistema e traz o ydotool vendorizado para o
 Wayland (o Recommends: ydotool é apenas fallback).
EOF

cp "$REPO_DIR/packaging/postinst.sh" "$DEB_ROOT/DEBIAN/postinst"
chmod 755 "$DEB_ROOT/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "$DEB_ROOT" \
    "$BUILD_DIR/jcl-clicker_${VERSION}_amd64.deb"

# --- .rpm via rpmbuild ---
RPMBUILD="$BUILD_DIR/rpmbuild"
mkdir -p "$RPMBUILD"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

RPM_SRC_BASE="$(mktemp -d)"
RPM_SRC="$RPM_SRC_BASE/jcl-clicker-${VERSION}"
mkdir -p "$RPM_SRC"
cp -a "$APP_DIR/usr" "$RPM_SRC/"
tar -czf "$RPMBUILD/SOURCES/jcl-clicker-${VERSION}.tar.gz" \
    -C "$RPM_SRC_BASE" "jcl-clicker-${VERSION}"
rm -rf "$RPM_SRC_BASE"

cat > "$RPMBUILD/SPECS/jcl-clicker.spec" << EOF
%define _enable_debug_packages 0
%define debug_package %{nil}
%define _missing_build_ids_terminate_build 0
%define _build_id_links none

Name:           jcl-clicker
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        JCL Clicker - automação de cliques de mouse para Linux
License:        MIT
URL:            https://github.com/jotaomh/JCL-Cliker
Source0:        jcl-clicker-%{version}.tar.gz
BuildArch:      x86_64
AutoReqProv:    no
Requires:       python3, python3-gobject, gtk4, python3-evdev
Recommends:     ydotool

%description
JCL Clicker é um auto clicker para Linux com suporte a X11 e Wayland.
Interface gráfica em GTK4 com atalho global de teclado. Usa o GTK4 do
sistema e traz o ydotool vendorizado para o Wayland.

%prep
%setup -q

%install
cp -a usr %{buildroot}

%post
update-desktop-database -q /usr/share/applications || true
gtk-update-icon-cache /usr/share/icons/hicolor || true

%files
/usr/bin/jcl-clicker
/usr/share/applications/autoclicker.desktop
/usr/share/icons/hicolor/256x256/apps/${ICON_NAME}
${APP_ROOT}
EOF

rpmbuild -bb "$RPMBUILD/SPECS/jcl-clicker.spec" \
    --define "_topdir $RPMBUILD" \
    --define "_sourcedir $RPMBUILD/SOURCES"

cp "$RPMBUILD"/RPMS/*/*.rpm "$BUILD_DIR/" 2>/dev/null || true

echo
echo "Pacotes gerados em $BUILD_DIR:"
ls -lh "$BUILD_DIR"/*.deb "$BUILD_DIR"/*.rpm 2>/dev/null