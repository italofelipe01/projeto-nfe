from flask import Flask
from .config import Config

def create_app(config_class=Config):
    """
    Application Factory (Fábrica de Aplicação):
    Cria e configura uma instância do Flask.
    
    Vantagens:
    1. Evita Ciclos de Importação (Circular Imports) entre Main e RPA.
    2. Permite criar instâncias diferentes para Testes e Produção.
    3. Centraliza o registro de Blueprints (Rotas).
    """
    
    # Inicializa a aplicação Flask
    app = Flask(__name__)
    
    # Carrega as configurações do arquivo config.py (ex: SECRET_KEY, UPLOAD_FOLDER)
    app.config.from_object(config_class)
    
    # Registro de Blueprints (Rotas)
    # Importamos dentro da função para evitar que o main.py tente importar o 'app'
    # antes dele ser criado totalmente.
    
    # Observação: O arquivo app/main.py precisará ser refatorado para usar 'Blueprint'
    # em vez de criar 'app = Flask()'.
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    # Aqui você também pode inicializar extensões, como Banco de Dados ou Login Manager
    # db.init_app(app)
    
    return app