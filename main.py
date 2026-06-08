from flask import Flask
from app.copa.routes import registrar_rotas


app = Flask(__name__)
app.secret_key = "akinacopa-dev-key-2024"

registrar_rotas(app)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False)
