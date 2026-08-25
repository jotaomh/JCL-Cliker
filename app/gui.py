import os
import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk, Gdk

from .clicker import JCLClicker
from .config import load_config, save_config
from .hotkeys import GlobalHotkey, HotkeyError, KEY_MAP
from .mouse import get_session, run_setup_script
from .state import ClickerState


BUTTON_LABELS = ["Esquerdo", "Meio", "Direito"]
BUTTON_VALUES = [1, 2, 3]

# asset de UI exibido no cabeçalho da janela (não é o ícone do app)
LOGO_ASSET = "corinthians.png"


def resolve_asset_path(name):
    """Localiza um asset de UI em todos os modos de execução.

    Mesma estratégia do _resolve_vendor_dir (app/mouse.py):
    - PyInstaller (--onefile): datas viram arquivos em sys._MEIPASS
    - source (dev) e instalação .deb/.rpm: assets/ fica dentro do próprio
      pacote app (ex: /usr/lib/jcl-clicker/app/assets/)
    """
    candidates = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "app", "assets", name))

    package_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(package_dir, "assets", name))

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None

HOTKEY_NAMES = list(KEY_MAP.keys())
HOTKEY_LABELS = [name.upper().replace("_", " ") for name in HOTKEY_NAMES]

STATUS_TEXT = {
    ClickerState.IDLE: "Pronto",
    ClickerState.RUNNING: "Executando...",
    ClickerState.STOPPED: "Parado",
    ClickerState.FINISHED: "Concluído",
    ClickerState.ERROR: "Erro",
}

# Cores próprias de fundo/texto por tema: garante contraste legível mesmo
# em distros sem a variante escura do tema instalada (o prefer-dark sozinho
# não escurece nada nesses sistemas). Controles (spin/dropdown/botão)
# continuam com o tema do sistema; labels herdam a cor da janela.
THEME_CSS = {
    "dark": """
        window {
            background-color: #20202b;
            color: #f3f3f8;
        }
        label.error {
            color: #ff7373;
            font-weight: bold;
        }
        .logo {
            background-color: #f2f2f2;
            border-radius: 10px;
            padding: 4px;
        }
    """,
    "light": """
        window {
            background-color: #f6f6f9;
            color: #17171d;
        }
        label.error {
            color: #b80000;
            font-weight: bold;
        }
        .logo {
            background-color: transparent;
        }
    """,
}

# provider criado no do_startup (precisa de display) e recarregado a cada
# troca de tema — load_from_string substitui o conteúdo anterior
_CSS_PROVIDER = None


def apply_theme(dark):
    """Aplica o tema claro/escuro na aplicação inteira."""
    settings = Gtk.Settings.get_default()
    if settings:
        settings.set_property("gtk-application-prefer-dark-theme", bool(dark))
    if _CSS_PROVIDER is not None:
        _CSS_PROVIDER.load_from_string(THEME_CSS["dark" if dark else "light"])


class JCLClickerWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app, title="JCL Clicker")

        self.set_default_size(360, 260)
        self.set_resizable(False)

        self.bot = None
        self.hotkey = None
        self.config = load_config()

        self.connect("close-request", self._on_close_request)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)
        self.set_child(root)

        # Logo de destaque (cabeçalho)
        logo_path = resolve_asset_path(LOGO_ASSET)
        if logo_path:
            logo = Gtk.Picture.new_for_filename(logo_path)
            logo.set_content_fit(Gtk.ContentFit.CONTAIN)
            logo.set_can_shrink(True)
            logo.set_size_request(-1, 72)
            logo.set_halign(Gtk.Align.CENTER)
            # o escudo tem traços pretos: no tema escuro ganha um cartão
            # claro por trás (classe .logo no CSS de cada tema)
            logo.add_css_class("logo")
            root.append(logo)

        # Tema claro/escuro
        root.append(self._build_row(
            "Tema escuro:",
            self._build_theme_switch(),
        ))

        # Intervalo
        root.append(self._build_row(
            "Intervalo entre cliques (s):",
            self._build_interval_spin(),
        ))

        # Botão do mouse
        root.append(self._build_row(
            "Botão do mouse:",
            self._build_button_dropdown(),
        ))

        # Quantidade de cliques
        root.append(self._build_row(
            "Quantidade (0 = infinito):",
            self._build_amount_spin(),
        ))

        # Atalho global
        root.append(self._build_row(
            "Atalho global iniciar/parar:",
            self._build_hotkey_dropdown(),
        ))

        # Separador
        root.append(Gtk.Separator())

        # Status
        self.status_label = Gtk.Label(label=STATUS_TEXT[ClickerState.IDLE])
        self.status_label.set_xalign(0)
        root.append(self.status_label)

        # Contador de cliques
        self.counter_label = Gtk.Label(label="Cliques: 0")
        self.counter_label.set_xalign(0)
        root.append(self.counter_label)

        # Mensagem de erro (escondida por padrão)
        self.error_label = Gtk.Label(label="")
        self.error_label.set_xalign(0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        root.append(self.error_label)

        # Botão "Corrigir permissões" (escondido, aparece só no Wayland com erro)
        self.fix_perms_button = Gtk.Button(label="Corrigir permissões")
        self.fix_perms_button.connect("clicked", self._on_fix_perms_clicked)
        self.fix_perms_button.set_visible(False)
        root.append(self.fix_perms_button)

        # Botão iniciar/parar
        self.toggle_button = Gtk.Button(label="Iniciar")
        self.toggle_button.connect("clicked", self._on_toggle_clicked)
        root.append(self.toggle_button)

        self._apply_saved_theme()
        self._start_hotkey_listener()

    # ---------- construção dos campos ----------

    def _build_theme_switch(self):
        switch = Gtk.Switch()
        dark = self.config.get("theme", "dark") == "dark"
        switch.set_active(dark)
        switch.connect("notify::active", self._on_theme_toggled)
        self.theme_switch = switch
        return switch

    def _build_row(self, label_text, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        label.set_hexpand(True)
        row.append(label)
        row.append(widget)
        return row

    def _build_interval_spin(self):
        adjustment = Gtk.Adjustment(
            value=self.config["interval"],
            lower=0.01,
            upper=60.0,
            step_increment=0.01,
            page_increment=0.1,
        )
        spin = Gtk.SpinButton(adjustment=adjustment, digits=2)
        spin.set_value(self.config["interval"])
        spin.connect("value-changed", self._on_interval_changed)
        self.interval_spin = spin
        return spin

    def _build_button_dropdown(self):
        model = Gtk.StringList.new(BUTTON_LABELS)
        dropdown = Gtk.DropDown(model=model)

        try:
            index = BUTTON_VALUES.index(self.config["button"])
        except ValueError:
            index = 0

        dropdown.set_selected(index)
        dropdown.connect("notify::selected", self._on_button_changed)
        self.button_dropdown = dropdown
        return dropdown

    def _build_amount_spin(self):
        adjustment = Gtk.Adjustment(
            value=self.config["amount"],
            lower=0,
            upper=1_000_000,
            step_increment=1,
            page_increment=10,
        )
        spin = Gtk.SpinButton(adjustment=adjustment, digits=0)
        spin.set_value(self.config["amount"])
        spin.connect("value-changed", self._on_amount_changed)
        self.amount_spin = spin
        return spin

    def _build_hotkey_dropdown(self):
        model = Gtk.StringList.new(HOTKEY_LABELS)
        dropdown = Gtk.DropDown(model=model)

        try:
            index = HOTKEY_NAMES.index(self.config.get("hotkey", "f6"))
        except ValueError:
            index = HOTKEY_NAMES.index("f6")

        dropdown.set_selected(index)
        dropdown.connect("notify::selected", self._on_hotkey_changed)
        self.hotkey_dropdown = dropdown
        return dropdown

    # ---------- handlers de configuração ----------

    def _on_theme_toggled(self, switch, _param):
        dark = switch.get_active()
        self.config["theme"] = "dark" if dark else "light"
        save_config(self.config)
        apply_theme(dark)

    def _on_interval_changed(self, spin):
        self.config["interval"] = round(spin.get_value(), 2)
        save_config(self.config)

    def _on_button_changed(self, dropdown, _param):
        index = dropdown.get_selected()
        self.config["button"] = BUTTON_VALUES[index]
        save_config(self.config)

    def _on_amount_changed(self, spin):
        self.config["amount"] = int(spin.get_value())
        save_config(self.config)

    def _on_hotkey_changed(self, dropdown, _param):
        index = dropdown.get_selected()
        self.config["hotkey"] = HOTKEY_NAMES[index]
        save_config(self.config)
        self._start_hotkey_listener()

    # ---------- iniciar / parar ----------

    def _on_toggle_clicked(self, _button):
        if self.bot and self.bot.running:
            self.bot.stop()
            self.toggle_button.set_label("Iniciar")
            self.status_label.set_text(STATUS_TEXT[ClickerState.STOPPED])
            self._set_inputs_sensitive(True)
            return

        self.error_label.set_visible(False)
        self.error_label.set_text("")
        self.fix_perms_button.set_visible(False)

        self.bot = JCLClicker(
            interval=self.config["interval"],
            button=self.config["button"],
            amount=self.config["amount"],
            callback=self._on_clicker_event,
        )
        self.bot.start()

        self.toggle_button.set_label("Parar")
        self.status_label.set_text(STATUS_TEXT[ClickerState.RUNNING])
        self._set_inputs_sensitive(False)

    def _on_clicker_event(self, value):
        # Executa na thread do JCLClicker: repassa para a thread principal do GTK
        GLib.idle_add(self._handle_event_in_main_thread, value)

    def _handle_event_in_main_thread(self, value):
        if isinstance(value, int):
            self.counter_label.set_text(f"Cliques: {value}")

        elif isinstance(value, str) and value.startswith("error: "):
            message = value[len("error: "):]
            self.error_label.set_text(message)
            self.error_label.set_visible(True)
            # Mostra botão de correção apenas para erros de permissão Wayland
            is_wayland_permission_error = (
                get_session() == "wayland"
                and "/dev/uinput" in message
            )
            self.fix_perms_button.set_visible(is_wayland_permission_error)
            self._finish_run(ClickerState.ERROR)

        elif value == "finished":
            self._finish_run(self.bot.state if self.bot else ClickerState.FINISHED)

        return False  # não repetir (GLib.idle_add one-shot)

    def _finish_run(self, state):
        self.toggle_button.set_label("Iniciar")
        self.status_label.set_text(STATUS_TEXT.get(state, "Pronto"))
        self._set_inputs_sensitive(True)
        if state != ClickerState.ERROR:
            self.fix_perms_button.set_visible(False)

    def _on_fix_perms_clicked(self, _button):
        """Executa o script de configuração de permissões via pkexec/sudo."""
        self.fix_perms_button.set_sensitive(False)
        self.fix_perms_button.set_label("Configurando...")
        self.error_label.set_visible(False)

        import threading

        def _run():
            success, output = run_setup_script()
            GLib.idle_add(self._on_fix_perms_done, success, output)

        threading.Thread(target=_run, daemon=True).start()

    def _on_fix_perms_done(self, success, output):
        self.fix_perms_button.set_sensitive(True)
        self.fix_perms_button.set_label("Corrigir permissões")

        if success:
            self.error_label.set_text(
                "Permissões configuradas com sucesso!\n"
                "Se o grupo 'input' acabou de ser adicionado, faça logout/login para aplicar."
            )
            self.error_label.set_visible(True)
            self.fix_perms_button.set_visible(False)
        else:
            msg = output.strip() if output else "Erro desconhecido."
            self.error_label.set_text(f"Falha ao configurar permissões:\n{msg}")
            self.error_label.set_visible(True)

        return False

    def _set_inputs_sensitive(self, sensitive):
        self.interval_spin.set_sensitive(sensitive)
        self.button_dropdown.set_sensitive(sensitive)
        self.amount_spin.set_sensitive(sensitive)

    # ---------- tema ----------

    def _apply_saved_theme(self):
        apply_theme(self.config.get("theme", "dark") == "dark")

    # ---------- atalho global ----------

    def _start_hotkey_listener(self):
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None

        key = self.config.get("hotkey", "f6")

        self.hotkey = GlobalHotkey(key=key, on_trigger=self._on_hotkey_triggered)

        try:
            self.hotkey.start()
        except HotkeyError as error:
            self.hotkey = None
            self.error_label.set_text(f"Atalho global indisponível: {error}")
            self.error_label.set_visible(True)

    def _on_hotkey_triggered(self):
        # Executa numa thread de fundo (pynput/evdev): repassa pro GTK
        GLib.idle_add(self._on_toggle_clicked, None)

    def _on_close_request(self, _window):
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None

        if self.bot and self.bot.running:
            self.bot.stop()
            thread = self.bot.thread
            if thread and thread.is_alive():
                # evita que a thread do clicker enfileire callbacks GTK
                # (idle_add) depois da janela destruída
                thread.join(timeout=2.0)

        return False  # permite o fechamento normal da janela


class JCLClickerApp(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id="io.github.jotaomh.jclclicker",
            # Sem isso, uma instância anterior (mesmo apontando para um
            # display morto ou de outra sessão) mantém o nome no D-Bus e
            # toda nova execução sai silenciosamente sem abrir janela.
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_startup(self):
        Gtk.Application.do_startup(self)

        global _CSS_PROVIDER
        _CSS_PROVIDER = Gtk.CssProvider()
        _CSS_PROVIDER.load_from_string(THEME_CSS["light"])
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            _CSS_PROVIDER,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = JCLClickerWindow(self)
        window.present()
