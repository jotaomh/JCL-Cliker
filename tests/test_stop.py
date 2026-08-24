import time

from app.clicker import JCLClicker


def status(valor):
    print("Evento:", valor)


bot = JCLClicker(
    interval=0.5,
    callback=status
)


print("Estado inicial:", bot.state)

bot.start()

time.sleep(3)

print("Parando...")

bot.stop()

bot.thread.join()

print("Estado depois do stop:", bot.state)