from flask import render_template, redirect, url_for
from app.copa.utils import carregar_figurinhas
import random

pacotes_disponiveis = 5

sorteadas = []
coladas = []

figurinhas = carregar_figurinhas()


def registrar_rotas(app):

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pacotes_disponiveis=pacotes_disponiveis,
            sorteadas=sorteadas,
            figurinhas=figurinhas,
            coladas=coladas
        )

    @app.route("/abrir_pacote")
    def abrir_pacote():
        global pacotes_disponiveis, sorteadas

        if pacotes_disponiveis > 0:
            pacotes_disponiveis -= 1

            nova = random.sample(figurinhas, k=2)
            nova_ids = [int(f["numero"]) for f in nova]

            sorteadas.extend(nova_ids)

        return redirect(url_for("index") + "#painel")

    @app.route("/colar/<int:jogador>")
    def colar(jogador):
        global coladas, sorteadas

        jogador = int(jogador)

        if jogador in sorteadas:
            coladas.append(jogador)
            sorteadas.remove(jogador)

        return redirect(url_for("index")+f"#fig-{jogador}")