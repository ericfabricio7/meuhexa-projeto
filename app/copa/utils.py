import os

BASE = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

BASE_DIR = os.path.join(BASE, "data")

FIGURINHAS_CSV = os.path.join(BASE_DIR, "figurinhas.csv")
USUARIO_CSV = os.path.join(BASE_DIR, "usuario.csv")


def carregar_figurinhas():
    figurinhas = []

    with open(FIGURINHAS_CSV, "r", encoding="utf-8") as arq:
        linhas = arq.read().splitlines()

    cabecalho = linhas[0].split(",")

    for linha in linhas[1:]:
        colunas = linha.split(",")

        jogador = {}

        for i in range(len(cabecalho)):
            jogador[cabecalho[i]] = colunas[i]

        jogador["numero"] = int(jogador["numero"])

        figurinhas.append(jogador)

    return figurinhas