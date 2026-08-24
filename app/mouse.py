import os
import subprocess
import sys
import time
import shutil

VALID_BUTTONS = {1, 2, 3}

# caminho fixo usado por instalações via .deb/.rpm (scripts/build-packages.sh)
_SYSTEM_VENDOR_DIR = "/usr/lib/jcl-clicker/vendor/ydotool"


def _resolve_vendor_dir():
    """Localiza o diretório com os binários vendorizados do ydotool.

    - PyInstaller (--onefile/--onedir): binários embutidos via --add-binary
      são extraídos para a raiz apontada por sys._MEIPASS
    - source (dev) e instalação .deb/.rpm: vendor/ fica na raiz do app,
      um nível acima do pacote Python (ex: /usr/lib/jcl-clicker/vendor/)
    - último recurso: caminho fixo da instalação de sistema
    """
    candidates = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "vendor", "ydotool"))

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(base, "vendor", "ydotool"))

    candidates.append(_SYSTEM_VENDOR_DIR)

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    return candidates[-1]


_VENDOR_DIR = _resolve_vendor_dir()

_VENDORED_YDOTOOL = os.path.join(_VENDOR_DIR, "ydotool")
_VENDORED_YDOTOOLD = os.path.join(_VENDOR_DIR, "ydotoold")

def _socket_path():
    """Socket próprio do app, por usuário.

    Um caminho compartilhado fixo (ex: /tmp/.ydotool_socket) colide com o
    daemon do sistema: se o socket existir mas não for acessível (dono
    root, grupo ydotool), o app falharia em vez de subir o daemon
    vendorizado. XDG_RUNTIME_DIR é tmpfs do próprio usuário (0700).
    """
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return os.path.join(runtime_dir, "jcl-clicker-ydotool.socket")
    return f"/tmp/jcl-clicker-{os.getuid()}-ydotool.socket"


# app usa 1=esquerdo, 2=meio, 3=direito
_YDOTOOL_BUTTON_MAP = {1: "0xC0", 2: "0xC2", 3: "0xC1"}

_x11_controller = None
_daemon_process = None
_ydotool_source_logged = False


class MouseError(Exception):
    """Erro ao tentar executar um clique de mouse."""


def _debug_log(message):
    # JCL_CLICKER_DEBUG=1 mostra no stderr qual binário/vendor está em uso
    if os.environ.get("JCL_CLICKER_DEBUG") == "1":
        print(f"[jcl-clicker] {message}", file=sys.stderr)


def _log_ydotool_source():
    global _ydotool_source_logged
    if _ydotool_source_logged:
        return
    _ydotool_source_logged = True
    _debug_log(f"vendor dir: {_VENDOR_DIR}")
    _debug_log(f"binário ydotool em uso: {_ydotool_binary()}")


def _ydotool_binary():
    if os.path.isfile(_VENDORED_YDOTOOL) and os.access(_VENDORED_YDOTOOL, os.X_OK):
        return _VENDORED_YDOTOOL
    return shutil.which("ydotool") or "ydotool"


def _socket_is_alive(path):
    import socket as socket_module

    if not os.path.exists(path):
        return False

    sock = socket_module.socket(socket_module.AF_UNIX, socket_module.SOCK_STREAM)
    sock.settimeout(0.3)
    try:
        sock.connect(path)
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _ensure_daemon_running():
    """Sobe o ydotoold vendorizado se necessário. True se o socket está acessível."""
    global _daemon_process

    socket_path = _socket_path()

    if _socket_is_alive(socket_path):
        return True

    # arquivo de socket órfão de uma execução anterior: remove antes de subir de novo
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
        except OSError:
            pass

    if not (os.path.isfile(_VENDORED_YDOTOOLD) and os.access(_VENDORED_YDOTOOLD, os.X_OK)):
        _debug_log("ydotoold vendorizado não encontrado, seguindo sem daemon próprio")
        return False  # sem daemon vendorizado, deixa o erro normal acontecer e avisar o usuário

    _debug_log(f"subindo daemon: {_VENDORED_YDOTOOLD}")
    _daemon_process = subprocess.Popen(
        [_VENDORED_YDOTOOLD, f"--socket-path={socket_path}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # espera até 5s o socket ficar de fato acessível (existir não basta:
    # o daemon pode ainda não estar aceitando conexões)
    for _ in range(50):
        if _socket_is_alive(socket_path):
            return True
        if _daemon_process.poll() is not None:
            break  # daemon morreu na inicialização
        time.sleep(0.1)

    _debug_log("daemon não ficou acessível a tempo")
    return False


def get_session():
    return os.environ.get("XDG_SESSION_TYPE", "")


def _get_x11_controller():
    global _x11_controller
    if _x11_controller is None:
        from pynput.mouse import Controller
        _x11_controller = Controller()
    return _x11_controller


def click(button=1):

    if button not in VALID_BUTTONS:
        raise MouseError(
            f"Botão inválido: {button}. Use 1 (esquerdo), 2 (meio) ou 3 (direito)."
        )

    session = get_session()

    # Wayland
    if session == "wayland":

        if not _ensure_daemon_running():
            raise MouseError(
                "Não foi possível iniciar o ydotoold vendorizado. "
                "No Wayland o daemon precisa de acesso a /dev/uinput — "
                "veja a seção 'Permissão de input (Wayland)' no README."
            )
        _log_ydotool_source()

        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = _socket_path()

        try:
            subprocess.run(
                [_ydotool_binary(), "click", _YDOTOOL_BUTTON_MAP[button]],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise MouseError(
                "ydotool não encontrado. Instale o pacote 'ydotool' para usar o clicker no Wayland."
            )
        except subprocess.CalledProcessError as error:
            raise MouseError(
                "Falha ao executar ydotool. Verifique se o daemon 'ydotoold' está rodando. "
                f"Detalhes: {error.stderr.strip() if error.stderr else error}"
            )

    # X11
    elif session == "x11":

        try:
            from pynput.mouse import Controller, Button

            mouse = _get_x11_controller()

            buttons = {
                1: Button.left,
                2: Button.middle,
                3: Button.right
            }

            mouse.click(buttons[button])
        except ImportError:
            raise MouseError(
                "pynput não está instalado. Rode 'pip install -r requirements.txt'."
            )
        except Exception as error:
            raise MouseError(
                f"Falha ao executar clique via pynput: {error}"
            )

    else:
        raise MouseError(
            f"Sessão não suportada: {session or 'desconhecida'}"
        )


def click_burst(button=1, count=1, interval=0.1, running_flag=None, on_click=None):
    """Clica repetidamente via ydotool, um processo por clique.
    Sem --repeat porque nem toda build do ydotool suporta essa flag."""

    if button not in VALID_BUTTONS:
        raise MouseError(
            f"Botão inválido: {button}. Use 1 (esquerdo), 2 (meio) ou 3 (direito)."
        )

    if not _ensure_daemon_running():
        raise MouseError(
            "Não foi possível iniciar o ydotoold vendorizado. "
            "No Wayland o daemon precisa de acesso a /dev/uinput — "
            "veja a seção 'Permissão de input (Wayland)' no README."
        )
    _log_ydotool_source()

    env = os.environ.copy()
    env["YDOTOOL_SOCKET"] = _socket_path()

    clicked = 0
    try:
        while running_flag is None or running_flag():
            subprocess.run(
                [_ydotool_binary(), "click", _YDOTOOL_BUTTON_MAP[button]],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            clicked += 1

            if on_click:
                on_click(clicked)

            if count and clicked >= count:
                break

            time.sleep(interval)
    except FileNotFoundError:
        raise MouseError(
            "ydotool não encontrado. Instale o pacote 'ydotool' para usar o clicker no Wayland."
        )
    except subprocess.CalledProcessError as error:
        raise MouseError(
            "Falha ao executar ydotool. Verifique se o daemon 'ydotoold' está rodando. "
            f"Detalhes: {error.stderr.strip() if error.stderr else error}"
        )
    return clicked