from flask import render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor
from app.copa.utils import carregar_figurinhas
import random

PACOTES_DISPONIVEIS = 2
NUMERO_FIGURINHAS = 7

pacotes_disponiveis = PACOTES_DISPONIVEIS

sorteadas = []
coladas = []

tem_bonus = False
repetidas_usadas = 0

figurinhas = carregar_figurinhas()


def registrar_rotas(app):

    # Álbum

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

            nova = random.sample(figurinhas, k=NUMERO_FIGURINHAS)
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
        global repetidas_usadas
        global tem_bonus

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        if repetidas - repetidas_usadas >= 20:

            faltantes = [
                int(f["numero"])
                for f in figurinhas
                if int(f["numero"]) not in coladas
            ]

            if faltantes:
                figurinha_bonus = random.choice(faltantes)
                coladas.append(figurinha_bonus)

            repetidas_usadas += 20

        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/minigame")
    def minigame():
        return render_template("minigame.html")

    @app.route("/minigame/novo", methods=["POST"])
    def minigame_novo():
        session["ak"] = motor.novo_jogo()
        estado = motor.calcular_estado(session["ak"])
        return jsonify(estado)

    @app.route("/minigame/responder", methods=["POST"])
    def minigame_responder():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data        = request.get_json()
        id_pergunta = int(data["pergunta_id"])
        resposta    = str(data["resposta"])

        novo_ak, estado = motor.processar_resposta(session["ak"], id_pergunta, resposta)
        session["ak"]   = novo_ak
        return jsonify(estado)

    @app.route("/minigame/confirmar", methods=["POST"])
    def minigame_confirmar():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data         = request.get_json()
        confirmado   = data.get("confirmado")
        palpite_id   = data.get("palpite_id")
        fase_palpite = data.get("fase_palpite", "mid")

        novo_ak, estado = motor.confirmar_palpite(
            session["ak"], confirmado, palpite_id, fase_palpite
        )
        session["ak"] = novo_ak

        fase = estado.get("fase")
        print(f'[confirmar] fase={fase} confirmado={confirmado} fase_palpite={fase_palpite}')
        if fase == "fim":
            motor.salvar_historico(
                acertou   = bool(estado.get("acertou")),
                palpite   = estado.get("palpite", {}),
                n_rodadas = estado.get("rodada", 0),
            )
            print(f'[confirmar] histórico salvo: acertou={estado.get("acertou")}')

        return jsonify(estado)

    @app.route("/minigame/registrar_erro", methods=["POST"])
    def minigame_registrar_erro():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data = request.get_json()
        nome = data.get("nome", "").strip()
        ano  = data.get("ano")

        if not nome or not ano:
            return jsonify({"erro": "Informe o nome e a Copa do jogador."}), 422

        resultado = motor.verificar_jogador(nome, ano)
        return jsonify({
            "encontrado": resultado["encontrado"],
            "apelido":    resultado.get("apelido"),
            "mensagem":   (
                f"{resultado['apelido']} está na nossa base! O motor aprenderá com esse erro."
                if resultado["encontrado"]
                else f"'{nome}' ainda não está na nossa base para a Copa de {ano}. Que tal nos ajudar a incluir?"
            ),
        })

    @app.route("/minigame/sugerir", methods=["POST"])
    def minigame_sugerir():
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados inválidos."}), 422

        ok, mensagem = motor.salvar_sugestao(dados)
        if not ok:
            return jsonify({"erro": mensagem}), 422

        return jsonify({"ok": True, "mensagem": mensagem})
