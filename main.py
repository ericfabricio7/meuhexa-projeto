from flask import Flask
from app.copa.routes import copa_bp

app = Flask(__name__)

app.register_blueprint(copa_bp)

if __name__ == "__main__":
    app.run(debug=True)