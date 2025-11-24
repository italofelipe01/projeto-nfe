from flask import Flask
from .config import Config


def create_app(config_class=Config):
    """
    Application Factory (Fábrica de Aplicação):
    Cria e configura uma instância do Flask.

    Vantagens:
    1. Evita Ciclos de Importação (Circular Imports).
    2. Permite instâncias diferentes para Testes e Produção.
    3. Centraliza o registro de Blueprints.
    """

    # Inicializa a aplicação Flask
    app = Flask(__name__)

    # Carrega as configurações do arquivo config.py
    app.config.from_object(config_class)

    # Registro de Blueprints (Rotas)
    from .main import bp as main_bp

    app.register_blueprint(main_bp)

    return app
