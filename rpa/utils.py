# -*- coding: utf-8 -*-
"""
Módulo de Utilitários do RPA (rpa/utils.py).

Responsabilidade:
1. Configurar o sistema de logging centralizado (Console + Arquivo com rotação).
2. Fornecer funções auxiliares para geração de IDs únicos.
3. Validar arquivos antes de envio ao portal.

Arquitetura:
- Logging estruturado com níveis distintos para Console (INFO+) e Arquivo (DEBUG+).
- Rotação automática de logs por tamanho (evita arquivos gigantes).
- Funções helper thread-safe para uso em ambiente multi-threading (Flask).
"""

import uuid
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- Configuração de Diretórios ---

# Define a raiz do projeto subindo dois níveis a partir deste arquivo
# Estrutura: projeto-nfe/rpa/utils.py -> PROJECT_ROOT = projeto-nfe/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório centralizado de logs do RPA
LOGS_DIR = PROJECT_ROOT / "rpa_logs"
EXECUTION_LOGS_DIR = LOGS_DIR / "execution_logs"

# Garante que os diretórios de log existam antes de qualquer operação
# exist_ok=True evita exceção se o diretório já existir (idempotência)
EXECUTION_LOGS_DIR.mkdir(parents=True, exist_ok=True)


# --- Funções de Logging ---


def setup_logger(name="rpa_logger", log_level=logging.DEBUG):
    """
    Configura um logger centralizado para o módulo RPA.

    Estratégia de Logging:
    - Console (StreamHandler): Exibe apenas INFO, WARNING e ERROR (feedback visual limpo).
    - Arquivo (RotatingFileHandler): Registra TUDO (DEBUG+) com rotação automática.

    Rotação de Arquivos:
    - Tamanho máximo: 5 MB por arquivo.
    - Backup: Mantém os últimos 10 arquivos (total ~50 MB de histórico).
    - Nomenclatura: execution_YYYYMMDD.log (um arquivo por dia).

    Args:
        name (str): Nome do logger (permite múltiplos loggers isolados).
        log_level (int): Nível mínimo de log para o arquivo (padrão: DEBUG).

    Returns:
        logging.Logger: Instância configurada e pronta para uso.

    Exemplo de Uso:
        >>> logger = setup_logger('rpa_authentication')
        >>> logger.info("Login iniciado")
        >>> logger.debug("Resolvendo teclado virtual...")
    """
    logger = logging.getLogger(name)

    # Evita duplicação de handlers se o logger já estiver configurado.
    # Isso previne que a mesma mensagem apareça repetida no terminal/arquivo.
    # Importante em ambientes onde setup_logger() pode ser chamado múltiplas vezes.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    # Desabilita propagação para o logger root (evita logs duplicados no Flask)
    logger.propagate = False

    # --- Formato Enriquecido do Log ---
    # Inclui: Data/Hora | Nível | Nome do Módulo | Linha | Thread | Mensagem
    # O campo %(threadName)s é crítico para debug de operações assíncronas (Flask threads).
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] [%(name)s:%(lineno)d] [%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Handler 1: Arquivo Rotativo (Histórico Completo) ---
    # Nome do arquivo inclui a data para facilitar auditoria diária.
    log_filename = f"execution_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = EXECUTION_LOGS_DIR / log_filename

    # RotatingFileHandler: Rotaciona quando o arquivo atinge maxBytes.
    # maxBytes=5*1024*1024 = 5 MB por arquivo.
    # backupCount=10 = Mantém os últimos 10 arquivos antes de sobrescrever.
    file_handler = RotatingFileHandler(
        log_filepath, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"  # 5 MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # Arquivo registra TUDO (incluindo DEBUG)

    # --- Handler 2: Console (Feedback Visual Limpo) ---
    # Exibe apenas INFO+ no terminal para não poluir a saída com mensagens de debug.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(
        logging.INFO
    )  # Console mostra INFO, WARNING, ERROR, CRITICAL

    # Anexa os handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_module_logger(module_name):
    """
    Cria um logger específico para um módulo RPA.

    Benefício: Permite rastrear qual módulo gerou cada log (ex: rpa.authentication, rpa.uploader).
    Isso facilita o debug de fluxos complexos onde múltiplos módulos interagem.

    Args:
        module_name (str): Nome do módulo (ex: 'authentication', 'file_uploader').

    Returns:
        logging.Logger: Logger configurado e isolado para o módulo.

    Exemplo:
        >>> # Em rpa/authentication.py
        >>> from rpa.utils import get_module_logger
        >>> logger = get_module_logger('authentication')
        >>> logger.info("Resolvendo teclado virtual...")

        # Log resultante:
        # 2025-11-19 14:32:10 [INFO    ] [rpa.authentication:45] [Thread-1] Resolvendo teclado virtual...
    """
    # Cria hierarquia de loggers: 'rpa.authentication', 'rpa.uploader', etc.
    # Isso permite filtragem por namespace se necessário.
    full_name = f"rpa.{module_name}"
    return setup_logger(full_name)


# --- Funções Auxiliares ---


def generate_task_id():
    """
    Gera um identificador único para uma tarefa de RPA.

    Estratégia:
    - Usa UUID4 (aleatório, seguro para ambientes distribuídos).
    - Trunca para 8 caracteres hexadecimais (suficiente para unicidade em contexto local).
    - Prefixo 'rpa_' facilita identificação visual nos logs.

    Returns:
        str: ID único no formato 'rpa_a3f8b2e1'.

    Exemplo:
        >>> task_id = generate_task_id()
        >>> print(task_id)
        'rpa_7d4c91a2'

    Uso Típico:
        - Nomear diretórios temporários (ex: rpa_logs/videos/rpa_7d4c91a2/).
        - Rastrear execuções no banco de dados ou fila de tarefas.
        - Correlacionar logs de múltiplas funções na mesma execução.
    """
    return f"rpa_{uuid.uuid4().hex[:8]}"


def validate_file_exists(file_path):
    """
    Valida a existência e integridade de um arquivo antes do upload.

    Validações Realizadas:
    1. Verifica se o caminho existe no sistema de arquivos.
    2. Confirma que é um arquivo (não um diretório).
    3. Verifica se o arquivo não está vazio (tamanho > 0 bytes).

    Args:
        file_path (str | Path): Caminho absoluto ou relativo do arquivo.

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            - (True, "") se o arquivo é válido.
            - (False, "motivo") se houver problema.

    Exemplo:
        >>> is_valid, error = validate_file_exists('/path/to/arquivo.txt')
        >>> if not is_valid:
        ...     logger.error(f"Arquivo inválido: {error}")
        ...     return False

    Casos de Uso:
    - Chamado pelo bot_controller.py antes de iniciar o navegador.
    - Evita abrir sessão Playwright para descobrir que o arquivo não existe.
    - Melhora feedback ao usuário (erro rápido vs timeout de 30s).
    """
    # Converte para Path object (suporta tanto string quanto Path)
    path = Path(file_path)

    # Validação 1: O caminho existe no filesystem?
    if not path.exists():
        return False, f"Arquivo não encontrado: {file_path}"

    # Validação 2: É um arquivo regular (não um diretório ou link simbólico)?
    if not path.is_file():
        return False, f"Caminho não aponta para um arquivo válido: {file_path}"

    # Validação 3: O arquivo tem conteúdo (não está vazio)?
    # stat().st_size retorna o tamanho em bytes.
    file_size = path.stat().st_size
    if file_size == 0:
        return False, f"Arquivo vazio (0 bytes): {file_path}"

    # Opcional: Log de sucesso para auditoria (comentado para não poluir)
    # logger.debug(f"Arquivo válido: {file_path} ({file_size} bytes)")

    return True, ""


# --- Exemplo de Uso (Executado apenas se o script for chamado diretamente) ---

if __name__ == "__main__":
    # Teste de Logging
    test_logger = setup_logger("test_module")
    test_logger.debug("Mensagem de DEBUG (só aparece no arquivo)")
    test_logger.info("Mensagem de INFO (console + arquivo)")
    test_logger.warning("Mensagem de WARNING")
    test_logger.error("Mensagem de ERROR")

    # Teste de Task ID
    print(f"Task ID Gerado: {generate_task_id()}")

    # Teste de Validação de Arquivo
    is_valid, error = validate_file_exists(__file__)  # Valida o próprio arquivo
    print(f"Validação do próprio arquivo: {is_valid} | Erro: {error}")

    is_valid, error = validate_file_exists("/caminho/inexistente.txt")
    print(f"Validação de arquivo inexistente: {is_valid} | Erro: {error}")
