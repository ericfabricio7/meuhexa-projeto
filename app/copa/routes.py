from flask import render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor

pacotes_disponiveis = 5

def registrar_rotas(app):

    # Álbum 

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pacotes_disponiveis=pacotes_disponiveis
        )

    @app.route("/abrir_pacote")
    def abrir_pacote():
        global pacotes_disponiveis
        if pacotes_disponiveis > 0:
            pacotes_disponiveis -= 1
        return redirect(url_for("index") + "#painel")

    # Minigame 

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

        data       = request.get_json()
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

        # Salva histórico quando jogo termina (acerto ou erro final)
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
        """
        Chamado quando o usuário diz quem era o jogador após o motor errar.
        Salva o histórico e verifica se o jogador existe na base.
        """
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data  = request.get_json()
        nome  = data.get("nome", "").strip()
        ano   = data.get("ano")
        palpite = data.get("palpite", {})

        if not nome or not ano:
            return jsonify({"erro": "Informe o nome e a Copa do jogador."}), 422

        # Verifica se o jogador existe na base
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
        """Recebe os dados de um jogador sugerido pelo usuário e salva em CSV."""
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Dados inválidos."}), 422

        ok, mensagem = motor.salvar_sugestao(dados)
        if not ok:
            return jsonify({"erro": mensagem}), 422

        return jsonify({"ok": True, "mensagem": mensagem})
