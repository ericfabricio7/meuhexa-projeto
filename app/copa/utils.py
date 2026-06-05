import csv
import os


BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.join(BASE,"data")

FIGURINHAS_CSV = os.path.join(BASE_DIR, "figurinhas.csv")

USUARIO_CSV = os.path.join(BASE_DIR, "usuario.csv")


def carregar_figurinhas():
    figurinhas = []

    with open(FIGURINHAS_CSV, encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)

        for jogador in leitor:
            jogador["numero"]=int(jogador["numero"])
            figurinhas.append(jogador)

    return figurinhas