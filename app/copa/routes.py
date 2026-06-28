from flask import render_template, redirect, url_for, request, session, jsonify
from . import akinator_motor as motor
from app.copa.utils import carregar_figurinhas
from functools import wraps
import random
import csv
import os

PACOTES_DISPONIVEIS = 2
NUMERO_FIGURINHAS = 7

pacotes_disponiveis = PACOTES_DISPONIVEIS
sorteadas = []
coladas = []
tem_bonus = False
repetidas_usadas = 0

figurinhas = carregar_figurinhas()

CSV_PATH = "data/usuarios.csv"
CSV_HEADER = ["nome", "email", "usuario", "senha", "foto_perfil", "selecao_favorita", "data_cadastro"]

UPLOAD_FOLDER = os.path.join("static", "img", "perfil")
EXTENSOES_PERMITIDAS = {"jpg", "jpeg", "png", "gif", "webp"}

SELECOES = [
    "Brasil", "Argentina", "França", "Alemanha", "Espanha", "Inglaterra",
    "Portugal", "Itália", "Holanda", "Bélgica", "Croácia", "Marrocos",
    "Japão", "Coreia do Sul", "Austrália", "Estados Unidos", "México",
    "Colômbia", "Uruguai", "Equador", "Senegal", "Nigéria", "Costa Rica",
    "Polônia", "Suíça", "Dinamarca", "Turquia", "Canadá", "Peru", "Chile",
]


# CSV HELPERS

def _ler_usuarios():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{campo: row.get(campo, "") for campo in CSV_HEADER} for row in reader]


def _salvar_usuarios(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def inicializar_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()
    else:
        # migra CSV antigo adicionando colunas novas com valor vazio
        _salvar_usuarios(_ler_usuarios())


def salvar_usuario(nome, email, usuario, senha):
    rows = _ler_usuarios()
    rows.append({
        "nome": nome, "email": email, "usuario": usuario,
        "senha": senha, "foto_perfil": "", "selecao_favorita": "", "data_cadastro": "",
    })
    _salvar_usuarios(rows)


def usuario_existe(email, usuario):
    return any(r["email"] == email or r["usuario"] == usuario for r in _ler_usuarios())


def verificar_login(usuario, senha):
    for row in _ler_usuarios():
        if row["usuario"] == usuario and row["senha"] == senha:
            return row
    return None


def obter_usuario(usuario):
    return next((r for r in _ler_usuarios() if r["usuario"] == usuario), None)


def atualizar_usuario(usuario_alvo, **campos):
    rows = _ler_usuarios()
    for row in rows:
        if row["usuario"] == usuario_alvo:
            row.update(campos)
            break
    _salvar_usuarios(rows)


def excluir_usuario(usuario_alvo):
    _salvar_usuarios([r for r in _ler_usuarios() if r["usuario"] != usuario_alvo])


def extensao_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


# LOGIN REQUIRED

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("cadastro"))
        return f(*args, **kwargs)
    return decorated


# ROTAS

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
            return redirect(url_for("index"))

        return "Usuário ou senha inválidos!", 401

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pacotes_disponiveis=pacotes_disponiveis,
            sorteadas=sorteadas,
            figurinhas=figurinhas,
            coladas=coladas,
            tem_bonus=tem_bonus,
        )

    @app.route("/abrir_pacote")
    @login_required
    def abrir_pacote():
        global pacotes_disponiveis, sorteadas, tem_bonus, repetidas_usadas

        if pacotes_disponiveis > 0:
            pacotes_disponiveis -= 1
            nova = random.sample(figurinhas, k=NUMERO_FIGURINHAS)
            sorteadas.extend([int(f["numero"]) for f in nova])

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))
        tem_bonus = (repetidas - repetidas_usadas) >= 20

        return redirect(url_for("index") + "#ponto-retorno")

    @app.route("/colar/<int:jogador>")
    @login_required
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
    @login_required
    def bonus():
        global repetidas_usadas, tem_bonus

        tudo = sorteadas + coladas
        repetidas = len(tudo) - len(set(tudo))

        if repetidas - repetidas_usadas >= 20:
            faltantes = [
                int(f["numero"]) for f in figurinhas if int(f["numero"]) not in coladas
            ]
            if faltantes:
                coladas.append(random.choice(faltantes))
            repetidas_usadas += 20

        tem_bonus = (repetidas - repetidas_usadas) >= 20
        return redirect(url_for("index") + "#ponto-retorno")

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
        dados = request.get_json()

        if not dados:
            return jsonify({"erro": "Dados inválidos"}), 422

        ok, mensagem = motor.salvar_sugestao(dados)

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
