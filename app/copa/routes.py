from flask import Blueprint, render_template
import requests

copa_bp = Blueprint("copa", __name__)

@copa_bp.route("/")
def home():

    url = "https://api.football-data.org/v4/competitions/WC/matches"

    headers = {
        "X-Auth-Token": ""
    }

    response = requests.get(url, headers=headers)

    dados = response.json()

    jogos = []

    for jogo in dados["matches"]:

        jogos.append({
            "casa": jogo["homeTeam"]["name"],
            "fora": jogo["awayTeam"]["name"],
            "gols_casa": jogo["score"]["fullTime"]["home"],
            "gols_fora": jogo["score"]["fullTime"]["away"]
        })

    return render_template(
        "index.html",
        jogos=jogos
    )