from app.clicker import JCLClicker


clicks = 0


def status(valor):
    global clicks
    if isinstance(valor, int):
        clicks = valor
    print("Evento:", valor)


bot = JCLClicker(
    interval=0.1,
    amount=10,
    callback=status
)


print("Estado inicial:", bot.state)

bot.start()

bot.thread.join()

print("Estado final:", bot.state)
print(f"Total de cliques: {clicks}")