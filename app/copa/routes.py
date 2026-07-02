from flask import render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor
from app.copa.utils import (
    carregar_figurinhas,
    atualizar_pacotes,
    inicializar_csv,
    salvar_usuario,
    usuario_existe,
    salvar_album,
    verificar_login,
    obter_usuario,
    atualizar_usuario,
    excluir_usuario,
    salvar_pendente,
    extensao_permitida,
    login_required,
    SELECOES,
    UPLOAD_FOLDER,
)
from datetime import datetime, timedelta
import random
import os
from app.copa.config import PACOTES_DISPONIVEIS, NUMERO_FIGURINHAS

figurinhas = carregar_figurinhas()

from datetime import datetime, timedelta

def atualizar_pacotes(usuario):
    dados = obter_usuario(usuario)

    if not dados:
        return

    ultimo = dados.get("ultimo_bonus", "")

    if ultimo:
        ultimo = datetime.fromisoformat(ultimo)
    else:
        ultimo = datetime.min

    if datetime.now() - ultimo >= timedelta(seconds=7):

        novos_pacotes = int(dados["pacotes"]) + 2

        atualizar_usuario(
            usuario,
            pacotes=novos_pacotes,
            ultimo_bonus=datetime.now().isoformat()
        )

        session["pacotes"] = novos_pacotes
        session["ultimo_bonus"] = datetime.now().isoformat()


def registrar_rotas(app):

    inicializar_csv()

    @app.route("/login", methods=["POST"])
    def login():
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        encontrado = verificar_login(usuario, senha)

        if encontrado:
            session["logado"] = True
            session["nome"] = encontrado["nome"]
            session["usuario"] = encontrado["usuario"]
            session["foto"] = encontrado["foto_perfil"]
            session["selecao"] = encontrado["selecao_favorita"]
            session["pacotes"] = int(encontrado["pacotes"])
            session["repetidas"] = int(encontrado["repetidas"])

            session["coladas"] = (
                [int(x) for x in encontrado["coladas"].split(";")]
                if encontrado["coladas"]
                else []
            )

            session["sorteadas"] = (
                [int(x) for x in encontrado["sorteadas"].split(";")]
                if encontrado["sorteadas"]
                else []
            )

            session["bonus"] = False

            session["ultimo_bonus"] = encontrado["ultimo_bonus"]
            return redirect(url_for("index"))
        
            

        return "Usuário ou senha inválidos!", 401

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/")
    def index():
        if session.get("logado"):
            atualizar_pacotes(session["usuario"])

        return render_template(
            "index.html",
            pacotes_disponiveis=session.get("pacotes", PACOTES_DISPONIVEIS),
            sorteadas=session.get("sorteadas", []),
            figurinhas=figurinhas,
            coladas=session.get("coladas", []),
            tem_bonus=session.get("bonus", False),
        )

    @app.route("/abrir_pacote")
    @login_required
    def abrir_pacote():

        pacotes = session.get("pacotes", PACOTES_DISPONIVEIS)
        sorteadas = session.get("sorteadas", [])
        coladas = session.get("coladas", [])
        repetidas_usadas = session.get("repetidas", 0)

        if pacotes > 0:
            pacotes -= 1
            nova = random.sample(figurinhas, k=NUMERO_FIGURINHAS)
            sorteadas.extend([int(f["numero"]) for f in nova])

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        bonus = (repetidas - repetidas_usadas) >= 20

        session["pacotes"] = pacotes
        session["sorteadas"] = sorteadas
        session["bonus"] = bonus

        salvar_album(
            session["usuario"],
            pacotes,
            repetidas_usadas,
            coladas,
            sorteadas
        )

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/colar/<int:jogador>")
    @login_required
    def colar(jogador):

        coladas = session.get("coladas", [])
        sorteadas = session.get("sorteadas", [])
        repetidas_usadas = session.get("repetidas", 0)

        if jogador in sorteadas:
            coladas.append(jogador)
            sorteadas.remove(jogador)

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        bonus = (repetidas - repetidas_usadas) >= 20

        session["coladas"] = coladas
        session["sorteadas"] = sorteadas
        session["bonus"] = bonus

        salvar_album(
            session["usuario"],
            session["pacotes"],
            repetidas_usadas,
            coladas,
            sorteadas
        )

        return redirect(url_for("index") + f"#fig-{jogador}")

    @app.route("/bonus")
    @login_required
    def bonus():

        coladas = session.get("coladas", [])
        sorteadas = session.get("sorteadas", [])
        repetidas_usadas = session.get("repetidas", 0)

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        if repetidas - repetidas_usadas >= 20:

            faltantes = [
                int(f["numero"])
                for f in figurinhas
                if int(f["numero"]) not in sorteadas and int(f["numero"]) not in coladas
            ]

            if faltantes:
                sorteadas.append(random.choice(faltantes))

            repetidas_usadas += 20

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        bonus = (repetidas - repetidas_usadas) >= 20

        session["coladas"] = coladas
        session["repetidas"] = repetidas_usadas
        session["bonus"] = bonus

        salvar_album(
            session["usuario"],
            session["pacotes"],
            repetidas_usadas,
            coladas,
            sorteadas
        )
        return redirect(url_for("index") + "#ponto-retorno")
    
    #FINAL - ERIC

    @app.route("/minigame")
    def minigame():
        return render_template("minigame.html")

    @app.route("/minigame/novo", methods=["POST"])
    def minigame_novo():
        session["ak"] = motor.novo_jogo()
        return jsonify(motor.calcular_estado(session["ak"]))

    @app.route("/minigame/responder", methods=["POST"])
    def minigame_responder():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data = request.get_json()
        novo_ak, estado = motor.processar_resposta(
            session["ak"],
            int(data["pergunta_id"]),
            str(data["resposta"]),
        )
        session["ak"] = novo_ak
        return jsonify(estado)

    @app.route("/minigame/confirmar", methods=["POST"])
    def minigame_confirmar():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data = request.get_json()
        novo_ak, estado = motor.confirmar_palpite(
            session["ak"],
            data.get("confirmado"),
            data.get("palpite_id"),
            data.get("fase_palpite", "mid"),
        )
        session["ak"] = novo_ak

        if estado.get("fase") == "fim":
            motor.salvar_historico(
                acertou=bool(estado.get("acertou")),
                palpite=estado.get("palpite", {}),
                n_rodadas=estado.get("rodada", 0),
            )

        return jsonify(estado)

    @app.route("/minigame/registrar_erro", methods=["POST"])
    def minigame_registrar_erro():
        if "ak" not in session:
            return jsonify({"erro": "sem jogo ativo"}), 400

        data = request.get_json()
        nome = data.get("nome", "").strip()
        ano = data.get("ano")

        if not nome or not ano:
            return jsonify({"erro": "Informe nome e Copa"}), 422

        resultado = motor.verificar_jogador(nome, ano)
        return jsonify({
            "encontrado": resultado["encontrado"],
            "apelido": resultado.get("apelido"),
            "mensagem": (
                f"{resultado['apelido']} já está na base!"
                if resultado["encontrado"]
                else f"{nome} não encontrado na base para {ano}"
            ),
        })

    @app.route("/minigame/sugerir", methods=["POST"])
    def minigame_sugerir():
        if not session.get("logado"):
            return jsonify({"login_required": True}), 401

        dados = request.get_json()

        if not dados:
            return jsonify({"erro": "Dados inválidos"}), 422

        ok, mensagem = salvar_pendente(dados, session["usuario"])

        if not ok:
            return jsonify({"erro": mensagem}), 422

        return jsonify({"ok": True, "mensagem": mensagem})

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        modo = request.args.get("modo", "cadastro")

        if request.method == "POST":
            nome = request.form.get("nome")
            email = request.form.get("email")
            usuario = request.form.get("usuario")
            senha = request.form.get("senha")

            if usuario_existe(email, usuario):
                return "Email ou usuário já cadastrado!", 400

            salvar_usuario(nome, email, usuario, senha)

            session["logado"] = True
            session["nome"] = nome
            session["usuario"] = usuario
            session["foto"] = ""
            session["selecao"] = ""
            session["pacotes"] = PACOTES_DISPONIVEIS
            session["repetidas"] = 0
            session["coladas"] = []
            session["sorteadas"] = []
            session["bonus"] = False

            return redirect(url_for("index"))

        return render_template("cadastro.html", modo=modo)

    # PERFIL

    @app.route("/perfil")
    @login_required
    def perfil():
        usuario = obter_usuario(session["usuario"])
        return render_template("perfil.html", usuario=usuario, selecoes=SELECOES)

    @app.route("/perfil/atualizar", methods=["POST"])
    @login_required
    def perfil_atualizar():
        usuario_atual = session["usuario"]
        campos = {}

        nome = request.form.get("nome", "").strip()
        selecao = request.form.get("selecao_favorita", "").strip()
        foto = request.files.get("foto")

        if nome:
            campos["nome"] = nome
            session["nome"] = nome

        if selecao:
            campos["selecao_favorita"] = selecao
            session["selecao"] = selecao

        if foto and foto.filename:
            if not extensao_permitida(foto.filename):
                return redirect(url_for("perfil") + "?erro=foto_invalida")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = foto.filename.rsplit(".", 1)[1].lower()
            filename = f"{usuario_atual}.{ext}"
            foto.save(os.path.join(UPLOAD_FOLDER, filename))
            campos["foto_perfil"] = f"img/perfil/{filename}"
            session["foto"] = campos["foto_perfil"]

        if campos:
            atualizar_usuario(usuario_atual, **campos)

        return redirect(url_for("perfil") + "?sucesso=perfil")

    @app.route("/perfil/senha", methods=["POST"])
    @login_required
    def perfil_senha():
        usuario_atual = session["usuario"]
        dados = obter_usuario(usuario_atual)

        if not dados or dados["senha"] != request.form.get("senha_atual", ""):
            return redirect(url_for("perfil") + "?erro=senha_incorreta")

        nova = request.form.get("nova_senha", "")
        if nova != request.form.get("confirmar_senha", ""):
            return redirect(url_for("perfil") + "?erro=senhas_diferentes")
        if len(nova) < 4:
            return redirect(url_for("perfil") + "?erro=senha_curta")

        atualizar_usuario(usuario_atual, senha=nova)
        return redirect(url_for("perfil") + "?sucesso=senha")

    @app.route("/perfil/excluir", methods=["POST"])
    @login_required
    def perfil_excluir():
        usuario_atual = session["usuario"]

        if request.form.get("confirmacao", "") != usuario_atual:
            return redirect(url_for("perfil") + "?erro=confirmacao_invalida")

        dados = obter_usuario(usuario_atual)
        if dados and dados.get("foto_perfil"):
            foto_path = os.path.join("static", dados["foto_perfil"])
            if os.path.exists(foto_path):
                os.remove(foto_path)

        excluir_usuario(usuario_atual)
        session.clear()
        return redirect(url_for("index"))
