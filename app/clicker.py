import threading
import time

from .mouse import click, click_burst, get_session, MouseError
from .state import ClickerState


class JCLClicker:

    def __init__(self, interval=0.1, button=1, amount=0, callback=None):

        self.interval = interval
        self.button = button
        self.amount = amount
        self.callback = callback

        self.clicks = 0
        self.error = None

        self.running = False
        self.thread = None
        self.state = ClickerState.IDLE

    def start(self):

        if self.running:
            return

        self.running = True
        self.error = None
        self.state = ClickerState.RUNNING

        # daemon: o fechamento da janela não pode ficar preso num clique
        # de subprocesso em andamento (join com timeout é feito na GUI)
        self.thread = threading.Thread(target=self._run, daemon=True)

        self.thread.start()

    def stop(self):

        self.running = False
        self.state = ClickerState.STOPPED


    def _run(self):

        self.clicks = 0

        if get_session() == "wayland":
            self._run_wayland_burst()
        else:
            self._run_single_clicks()

        self.running = False

        if self.state == ClickerState.RUNNING:
            self.state = ClickerState.FINISHED

        if self.callback and self.state != ClickerState.ERROR:
            self.callback("finished")


    def _run_wayland_burst(self):

            count = self.amount if self.amount > 0 else 0  # 0 = ilimitado dentro do click_burst

            def on_click(n):
                self.clicks = n
                if self.callback:
                    self.callback(self.clicks)
                else:
                    print(f"Clique {self.clicks}")

            try:
                click_burst(
                    self.button,
                    count=count,
                    interval=self.interval,
                    running_flag=lambda: self.running,
                    on_click=on_click,
                )
            except MouseError as error:
                self.error = str(error)
                self.state = ClickerState.ERROR

                if self.callback:
                    self.callback(f"error: {self.error}")
                else:
                    print(f"Erro: {self.error}")


    def _run_single_clicks(self):

        # Loop original, usado no X11 (onde o Controller() do pynput já
        # é reaproveitado entre chamadas, então o overhead por clique é
        # baixo o suficiente para clicar dentro do próprio loop Python).
        while self.running:

            start = time.monotonic()

            try:
                click(self.button)
            except MouseError as error:
                self.error = str(error)
                self.running = False
                self.state = ClickerState.ERROR

                if self.callback:
                    self.callback(f"error: {self.error}")
                else:
                    print(f"Erro: {self.error}")

                break

            self.clicks += 1

            if self.callback:
                self.callback(self.clicks)
            else:
                print(f"Clique {self.clicks}")

            if (
                self.amount > 0
                and self.clicks >= self.amount
            ):
                break

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, self.interval - elapsed)
            time.sleep(sleep_time)