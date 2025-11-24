import os


class Config:
    """
    Centraliza as configurações da aplicação Flask.
    """

    # Define o diretório base da aplicação (a pasta 'app')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Define a raiz do projeto (um nível acima da pasta 'app')
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

    # Caminhos para os diretórios de upload e download
    UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")
    DOWNLOADS_DIR = os.path.join(PROJECT_ROOT, "downloads")

    # Configurações de arquivo baseadas no workflow
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    # Chave secreta para segurança de sessões
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-padrao-issnet"
