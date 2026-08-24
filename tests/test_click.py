from app.mouse import click

import time


print("Iniciando teste...")


for i in range(5):

    click()

    print(f"Clique {i+1}")

    time.sleep(1)


print("Finalizado!")
