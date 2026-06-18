from flask import render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor
from app.copa.utils import carregar_figurinhas
import random
import csv
import os

PACOTES_DISPONIVEIS = 7

pacotes_disponiveis = PACOTES_DISPONIVEIS
sorteadas = []
coladas = []

tem_bonus = False
repetidas_usadas = 0

figurinhas = carregar_figurinhas()

CSV_PATH = "usuarios.csv"
CSV_HEADER = ["nome", "email", "usuario", "senha"]


# =========================
# 🧠 CSV HELPERS
# =========================

def inicializar_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def salvar_usuario(nome, email, usuario, senha):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([nome, email, usuario, senha])


def usuario_existe(email, usuario):
    if not os.path.exists(CSV_PATH):
        return False

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # pula cabeçalho

        for row in reader:
            if len(row) < 4:
                continue

            _, e, u, _ = row

            if e == email or u == usuario:
                return True

    return False


# =========================
# 🚀 ROTAS
# =========================

def registrar_rotas(app):

    inicializar_csv()

    # =========================
    # 🏠 ÁLBUM
    # =========================

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
        global pacotes_disponiveis, sorteadas, tem_bonus, repetidas_usadas

        if pacotes_disponiveis > 0:
            pacotes_disponiveis -= 1
            nova = random.sample(figurinhas, k=50)
            sorteadas.extend([int(f["numero"]) for f in nova])

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/colar/<int:jogador>")
    def colar(jogador):
        global coladas, sorteadas, tem_bonus, repetidas_usadas

        if jogador in sorteadas:
            coladas.append(jogador)
            sorteadas.remove(jogador)

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + f"#fig-{jogador}")

    @app.route("/bonus")
    def bonus():
        global repetidas_usadas, tem_bonus

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        if repetidas - repetidas_usadas >= 20:
            faltantes = [
                int(f["numero"])
                for f in figurinhas
                if int(f["numero"]) not in coladas
            ]

            if faltantes:
                coladas.append(random.choice(faltantes))

            repetidas_usadas += 20

        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/reiniciar")
    def reiniciar():
        global pacotes_disponiveis, sorteadas, coladas, tem_bonus, repetidas_usadas

        pacotes_disponiveis = PACOTES_DISPONIVEIS
        sorteadas = []
        coladas = []
        tem_bonus = False
        repetidas_usadas = 0

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/colartudo")
    def colartudo():
        global coladas, sorteadas
        coladas = sorteadas.copy()
        return redirect(url_for("index") + "#ponto-retorno")

    # =========================
    # 🎮 MINIGAME
    # =========================

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
            str(data["resposta"])
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
            data.get("fase_palpite", "mid")
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
        dados = request.get_json()

        if not dados:
            return jsonify({"erro": "Dados inválidos"}), 422

        ok, mensagem = motor.salvar_sugestao(dados)

        if not ok:
            return jsonify({"erro": mensagem}), 422

        return jsonify({"ok": True, "mensagem": mensagem})

    # =========================
    # 👤 CADASTRO (CSV COM DUPLICIDADE)
    # =========================

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():

        if request.method == "POST":

            nome = request.form.get("nome")
            email = request.form.get("email")
            usuario = request.form.get("usuario")
            senha = request.form.get("senha")

            # 🔍 valida duplicidade
            if usuario_existe(email, usuario):
                return "Email ou usuário já cadastrado!", 400

            salvar_usuario(nome, email, usuario, senha)

            return redirect(url_for("index"))

        return render_template("cadastro.html")