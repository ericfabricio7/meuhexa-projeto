from flask import render_template, redirect, url_for
from app.copa.utils import carregar_figurinhas
import random

PACOTES_DISPONIVEIS = 7

pacotes_disponiveis = PACOTES_DISPONIVEIS

sorteadas = []
coladas = []

tem_bonus = False
repetidas_usadas = 0

figurinhas = carregar_figurinhas()


def registrar_rotas(app):

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pacotes_disponiveis=pacotes_disponiveis,
            sorteadas=sorteadas,
            figurinhas=figurinhas,
            coladas=coladas,
            tem_bonus=tem_bonus
        )

    @app.route("/abrir_pacote")
    def abrir_pacote():
        global pacotes_disponiveis
        global sorteadas
        global tem_bonus
        global repetidas_usadas

        if pacotes_disponiveis > 0:
            pacotes_disponiveis -= 1

            nova = random.sample(figurinhas, k=10)
            nova_ids = [int(f["numero"]) for f in nova]

            sorteadas.extend(nova_ids)

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/colar/<int:jogador>")
    def colar(jogador):
        global coladas
        global sorteadas
        global tem_bonus
        global repetidas_usadas

        if jogador in sorteadas:
            coladas.append(jogador)
            sorteadas.remove(jogador)

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + f"#fig-{jogador}")

    @app.route("/bonus")
    def bonus():
        global pacotes_disponiveis
        global repetidas_usadas
        global tem_bonus

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        if repetidas - repetidas_usadas >= 20:
            pacotes_disponiveis += 1
            repetidas_usadas += 20

        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/reiniciar")
    def reiniciar():
        global pacotes_disponiveis
        global sorteadas
        global coladas
        global tem_bonus
        global repetidas_usadas

        pacotes_disponiveis = PACOTES_DISPONIVEIS
        sorteadas = []
        coladas = []

        tem_bonus = False
        repetidas_usadas = 0

        return redirect(url_for("index") + "#ponto-retorno")
    
    @app.route("/colartudo")
    def colartudo():
        global coladas, sorteadas
        s = sorteadas.copy()
        coladas=s
        return redirect(url_for("index")+"#ponto-retorno")