#!/bin/bash
# setup-uinput.sh — Configura permissões necessárias para o ydotoold no Wayland.
#
# Precisa ser executado como root (sudo ou pkexec).
#
# O que faz:
#   1. Carrega o módulo uinput e garante persistência
#   2. Cria regra udev para /dev/uinput (grupo "input", modo 0660)
#   3. Adiciona o usuário ao grupo "input"
#   4. Recarrega regras udev
#
# Exit codes:
#   0 — tudo ok
#   1 — erro ao carregar módulo
#   2 — erro ao configurar udev
#   3 — erro ao adicionar usuário ao grupo

set -euo pipefail

# ── pré-requisitos ──────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo "ERRO: este script precisa ser executado como root." >&2
    exit 1
fi

if [ -z "${SUDO_USER:-}" ] && [ -z "${PKEXEC_UID:-}" ]; then
    echo "ERRO: execute via sudo ou pkexec para que o usuário original seja identificado." >&2
    exit 1
fi

# Usuário alvo (quem chamou sudo/pkexec)
if [ -n "${SUDO_USER:-}" ]; then
    TARGET_USER="$SUDO_USER"
else
    TARGET_USER="$(getent passwd "${PKEXEC_UID}" | cut -d: -f1)"
fi

echo "Configurando permissões de input para o usuário: ${TARGET_USER}"

# ── 1. Módulo uinput ───────────────────────────────────────────────────────
echo "[1/4] Verificando módulo uinput..."

if ! lsmod | grep -q "^uinput "; then
    modprobe uinput
    echo "  → Módulo uinput carregado."
else
    echo "  → Módulo uinput já carregado."
fi

# Persistência: garante que o módulo carrega no boot
UINPUT_MODULES_CONF="/etc/modules-load.d/uinput.conf"
if [ ! -f "$UINPUT_MODULES_CONF" ] || ! grep -q "^uinput" "$UINPUT_MODULES_CONF" 2>/dev/null; then
    mkdir -p /etc/modules-load.d
    echo "uinput" > "$UINPUT_MODULES_CONF"
    echo "  → Persistência configurada em ${UINPUT_MODULES_CONF}"
else
    echo "  → Persistência já configurada."
fi

# ── 2. Regra udev ──────────────────────────────────────────────────────────
echo "[2/4] Configurando regra udev..."

UDEV_RULE="/etc/udev/rules.d/99-jcl-clicker.rules"
UDEV_CONTENT='KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"'

if [ -f "$UDEV_RULE" ] && grep -q 'KERNEL=="uinput"' "$UDEV_RULE" 2>/dev/null; then
    echo "  → Regra udev já existe em ${UDEV_RULE}"
else
    echo "$UDEV_CONTENT" > "$UDEV_RULE"
    echo "  → Regra udev criada em ${UDEV_RULE}"
fi

# Recarrega regras e aplica
if command -v udevadm &>/dev/null; then
    udevadm control --reload-rules
    udevadm trigger --name-match=uinput
    echo "  → Regras udev recarregadas."
else
    echo "  AVISO: udevadm não encontrado, regras serão aplicadas no próximo boot." >&2
fi

# ── 3. Grupo do usuário ────────────────────────────────────────────────────
echo "[3/4] Adicionando ${TARGET_USER} ao grupo input..."

if id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx "input"; then
    echo "  → Usuário ${TARGET_USER} já pertence ao grupo input."
else
    usermod -aG input "$TARGET_USER"
    echo "  → Usuário ${TARGET_USER} adicionado ao grupo input."
    echo ""
    echo "  ⚠  IMPORTANTE: Faça logout/login (ou reinicie) para o grupo ter efeito."
    echo ""
fi

# ── 4. Verificação final ───────────────────────────────────────────────────
echo "[4/4] Verificação..."

if [ -c /dev/uinput ]; then
    echo "  → /dev/uinput existe."
else
    echo "  AVISO: /dev/uinput não encontrado. Verifique se o módulo uinput está disponível no kernel." >&2
fi

echo ""
echo "Configuração concluída com sucesso!"
echo "Se acabou de ser adicionado ao grupo 'input', faça logout/login para aplicar."
