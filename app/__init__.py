from flask import Flask
from flask_session import Session

def create_app():
    app = Flask(__name__)
    
    from app.api import api_bp
    from app.web import web_bp

    # Configura la sesión para usar filesystem (en lugar de cookies firmadas)
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    app.json.sort_keys = False
    Session(app)

    # Registro de las blueprints de la API REST y web app
    app.register_blueprint(api_bp, url_prefix='/api/')
    app.register_blueprint(web_bp, url_prefix='/')

    return app