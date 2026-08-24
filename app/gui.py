import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GLib, Gdk

from .clicker import AutoClicker
from .config import load_config, save_config
from .hotkeys import GlobalHotkey, HotkeyError, KEY_MAP
from .state import ClickerState


BUTTON_LABELS = ["Esquerdo", "Meio", "Direito"]
BUTTON_VALUES = [1, 2, 3]

HOTKEY_NAMES = list(KEY_MAP.keys())
HOTKEY_LABELS = [name.upper().replace("_", " ") for name in HOTKEY_NAMES]

STATUS_TEXT = {
    ClickerState.IDLE: "Pronto",
    ClickerState.RUNNING: "Executando...",
    ClickerState.STOPPED: "Parado",
    ClickerState.FINISHED: "Concluído",
    ClickerState.ERROR: "Erro",
}


class AutoClickerWindow(Gtk.ApplicationWindow):

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

        # Botão iniciar/parar
        self.toggle_button = Gtk.Button(label="Iniciar")
        self.toggle_button.connect("clicked", self._on_toggle_clicked)
        root.append(self.toggle_button)

        self._start_hotkey_listener()

    # ---------- construção dos campos ----------

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

        self.bot = AutoClicker(
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
        # Executa na thread do AutoClicker: repassa para a thread principal do GTK
        GLib.idle_add(self._handle_event_in_main_thread, value)

    def _handle_event_in_main_thread(self, value):
        if isinstance(value, int):
            self.counter_label.set_text(f"Cliques: {value}")

        elif isinstance(value, str) and value.startswith("error: "):
            message = value[len("error: "):]
            self.error_label.set_text(message)
            self.error_label.set_visible(True)
            self._finish_run(ClickerState.ERROR)

        elif value == "finished":
            self._finish_run(self.bot.state if self.bot else ClickerState.FINISHED)

        return False  # não repetir (GLib.idle_add one-shot)

    def _finish_run(self, state):
        self.toggle_button.set_label("Iniciar")
        self.status_label.set_text(STATUS_TEXT.get(state, "Pronto"))
        self._set_inputs_sensitive(True)

    def _set_inputs_sensitive(self, sensitive):
        self.interval_spin.set_sensitive(sensitive)
        self.button_dropdown.set_sensitive(sensitive)
        self.amount_spin.set_sensitive(sensitive)

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

        return False  # permite o fechamento normal da janela


CSS = """
label.error {
    color: #cc0000;
    font-weight: bold;
}
"""


class AutoClickerApp(Gtk.Application):

    def __init__(self):
        super().__init__(application_id="io.github.jotaomh.jclclicker")

    def do_startup(self):
        Gtk.Application.do_startup(self)

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = AutoClickerWindow(self)
        window.present()
