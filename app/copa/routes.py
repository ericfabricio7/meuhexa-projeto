from flask import app, render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor
from app.copa.utils import carregar_figurinhas
from functools import wraps
import random
import csv
import os

figurinhas = carregar_figurinhas()

CSV_PATH = "data/usuarios.csv"
CSV_HEADER = [
    "nome",
    "email",
    "usuario",
    "senha",
    "pacotes",
    "repetidas",
    "coladas",
    "sorteadas"
]

PACOTES_DISPONIVEIS = 2
NUMERO_FIGURINHAS = 7

def inicializar_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)

def verificar_login(usuario, senha):

    if not os.path.exists(CSV_PATH):
        return None

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:

            if len(row) < 8:
                continue

            nome_csv, email_csv, usuario_csv, senha_csv, pacotes, repetidas, coladas, sorteadas = row

            if usuario_csv == usuario and senha_csv == senha:
                return {
                    "nome": nome_csv,
                    "email": email_csv,
                    "usuario": usuario_csv,
                    "pacotes": int(pacotes),
                    "repetidas": int(repetidas),
                    "coladas": coladas,
                    "sorteadas": sorteadas
                }

    return None

def salvar_album(usuario, pacotes, repetidas, coladas, sorteadas):

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        linhas = list(csv.reader(f))

    for i in range(1, len(linhas)):

        if linhas[i][2] == usuario:

            linhas[i][4] = str(pacotes)
            linhas[i][5] = str(repetidas)
            linhas[i][6] = ";".join(map(str, coladas))
            linhas[i][7] = ";".join(map(str, sorteadas))

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(linhas)

def salvar_usuario(nome, email, usuario, senha):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            nome,
            email,
            usuario,
            senha,
            PACOTES_DISPONIVEIS,
            0,
            "",
            ""
        ])


def usuario_existe(email, usuario):

    if not os.path.exists(CSV_PATH):
        return False

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            print(row)

            e = row[1]
            u = row[2]

            if e == email or u == usuario:
                return True

    return False

# =========================
# Login
# =========================


# =========================
# 🔒 LOGIN REQUIRED
# =========================

def login_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        if not session.get("logado"):
            return redirect(url_for("cadastro"))

        return f(*args, **kwargs)

    return decorated

# =========================
# 🚀 ROTAS
# =========================

def registrar_rotas(app):

    inicializar_csv()
# =========================
# 🏠 LOGIN
# =========================

    @app.route("/login", methods=["POST"])
    def login():

        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        usuario_encontrado = verificar_login(usuario, senha)

        if usuario_encontrado:

            session["logado"] = True
            session["nome"] = usuario_encontrado["nome"]
            session["usuario"] = usuario_encontrado["usuario"]

            session["pacotes"] = usuario_encontrado["pacotes"]
            session["repetidas"] = usuario_encontrado["repetidas"]

            session["coladas"] = (
                [int(x) for x in usuario_encontrado["coladas"].split(";")]
                if usuario_encontrado["coladas"]
                else []
            )

            session["sorteadas"] = (
                [int(x) for x in usuario_encontrado["sorteadas"].split(";")]
                if usuario_encontrado["sorteadas"]
                else []
            )

            session["bonus"] = False

            return redirect(url_for("index"))

        return "Usuário ou senha inválidos!", 401
    @app.route("/logout")
    def logout():

        session.clear()

        return redirect(url_for("index"))
    # =========================
    # 🏠 ÁLBUM
    # =========================

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pacotes_disponiveis=session.get(
                "pacotes",
                PACOTES_DISPONIVEIS
            ),
            sorteadas=session.get("sorteadas", []),
            figurinhas=figurinhas,
            coladas=session.get("coladas", []),
            tem_bonus=session.get("bonus", False)
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
            nova_ids = [int(f["numero"]) for f in nova]

            sorteadas.extend(nova_ids)

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
                if int(f["numero"]) not in coladas
            ]

            if faltantes:
                coladas.append(random.choice(faltantes))

            repetidas_usadas += 20

        bonus = (repetidas - repetidas_usadas) >= 20

        session["coladas"] = coladas
        session["bonus"] = bonus
        session["repetidas"] = repetidas_usadas

        salvar_album(
            session["usuario"],
            session["pacotes"],
            repetidas_usadas,
            coladas,
            sorteadas
        )

        return redirect(url_for("index") + "#ponto-retorno")
    
    #FINAL - ERIC

    # Minigame 

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

            session["pacotes"] = PACOTES_DISPONIVEIS
            session["sorteadas"] = []
            session["coladas"] = []
            session["bonus"] = False
            session["repetidas"] = 0

            return redirect(url_for("index"))

        return render_template("cadastro.html",modo=modo)