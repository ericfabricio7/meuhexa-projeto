from flask import redirect, url_for, session
from functools import wraps
from datetime import datetime, timedelta
import csv
import uuid
import os
from app.copa.config import PACOTES_DISPONIVEIS

BASE = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

BASE_DIR = os.path.join(BASE, "data")

FIGURINHAS_CSV = os.path.join(BASE_DIR, "figurinhas.csv")

CSV_PATH = "data/usuarios.csv"
CSV_HEADER = [
    "nome",
    "email",
    "usuario",
    "senha",
    "pacotes",
    "repetidas",
    "coladas",
    "sorteadas",
    "foto_perfil",
    "selecao_favorita",
    "ultimo_bonus"
]

UPLOAD_FOLDER = os.path.join("static", "img", "perfil")
EXTENSOES_PERMITIDAS = {"jpg", "jpeg", "png", "gif", "webp"}

SELECOES = [
    "Brasil", "Argentina", "França", "Alemanha", "Espanha", "Inglaterra",
    "Portugal", "Itália", "Holanda", "Bélgica", "Croácia", "Marrocos",
    "Japão", "Coreia do Sul", "Austrália", "Estados Unidos", "México",
    "Colômbia", "Uruguai", "Equador", "Senegal", "Nigéria", "Costa Rica",
    "Polônia", "Suíça", "Dinamarca", "Turquia", "Canadá", "Peru", "Chile",
]

CSV_PENDING_PATH = "data/pending.csv"
CSV_PENDING_HEADER = [
    "id_contribuicao", "data_hora", "usuario_contribuinte",
    "nome", "apelido", "ano_copa", "posicao",
    "clube", "titular", "gols", "observacoes",
    "curiosidade_1", "curiosidade_2",
    "status",
]



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

def atualizar_pacotes(usuario):
    dados = obter_usuario(usuario)

    if not dados:
        return

    ultimo = dados.get("ultimo_bonus", "")

    if ultimo:
        ultimo = datetime.fromisoformat(ultimo)
    else:
        ultimo = datetime.min

    if datetime.now() - ultimo >= timedelta(minutes=1):

        novos_pacotes = int(dados["pacotes"]) + 2

        atualizar_usuario(
            usuario,
            pacotes=novos_pacotes,
            ultimo_bonus=datetime.now().isoformat()
        )

        session["pacotes"] = novos_pacotes
        session["ultimo_bonus"] = datetime.now().isoformat()

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
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
    else:
        # migra CSV antigo adicionando colunas novas com valor vazio
        _salvar_usuarios(_ler_usuarios())


def salvar_usuario(nome, email, usuario, senha):
    rows = _ler_usuarios()

    rows.append({
        "nome": nome,
        "email": email,
        "usuario": usuario,
        "senha": senha,
        "pacotes": PACOTES_DISPONIVEIS,
        "repetidas": 0,
        "coladas": "",
        "sorteadas": "",
        "foto_perfil": "",
        "selecao_favorita": "",
        "ultimo_bonus": datetime.now().isoformat()
    })

    _salvar_usuarios(rows)


def usuario_existe(email, usuario):
    return any(r["email"] == email or r["usuario"] == usuario for r in _ler_usuarios())

def salvar_album(usuario, pacotes, repetidas, coladas, sorteadas):

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        linhas = list(csv.reader(f))

    for i in range(1, len(linhas)):

        if linhas[i][2] == usuario:

            linhas[i][4] = str(pacotes)
            linhas[i][5] = str(repetidas)
            linhas[i][6] = ";".join(map(str, coladas))
            linhas[i][7] = ";".join(map(str, sorteadas))

            break

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(linhas)

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


def salvar_pendente(dados: dict, usuario: str) -> tuple[bool, str]:
    existe = os.path.exists(CSV_PENDING_PATH) and os.path.getsize(CSV_PENDING_PATH) > 0
    try:
        with open(CSV_PENDING_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_PENDING_HEADER)
            if not existe:
                writer.writeheader()
            writer.writerow({
                "id_contribuicao":     str(uuid.uuid4())[:8],
                "data_hora":           datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "usuario_contribuinte": usuario,
                "nome":        dados.get("nome", "").strip(),
                "apelido":     dados.get("apelido", "").strip(),
                "ano_copa":    dados.get("ano_copa", ""),
                "posicao":     dados.get("posicao", "").strip(),
                "clube":       dados.get("clube", "").strip(),
                "titular":     dados.get("titular", "").strip(),
                "gols":        dados.get("gols", "0"),
                "observacoes": dados.get("observacoes", "").strip(),
                "curiosidade_1": dados.get("curiosidade_1", "").strip(),
                "curiosidade_2": dados.get("curiosidade_2", "").strip(),
                "status":      "pendente",
            })
        return True, "Contribuição registrada! Avaliaremos para incluir na base."
    except OSError as e:
        return False, f"Não foi possível salvar a contribuição: {e}"


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