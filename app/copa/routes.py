from flask import render_template, redirect, url_for

pacotes_disponiveis = 5

def registrar_rotas(app):

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