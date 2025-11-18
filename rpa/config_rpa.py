# -*- coding: utf-8 -*-
"""
Módulo de Configuração do RPA.

Este arquivo centraliza todas as configurações relacionadas
à automação RPA do portal ISS.net.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Diretórios do Projeto ---

# Diretório raiz do projeto (3 níveis acima deste arquivo)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório base do módulo RPA
RPA_DIR = Path(__file__).resolve().parent

# Diretórios de logs
LOGS_DIR = PROJECT_ROOT / 'rpa_logs'
EXECUTION_LOGS_DIR = LOGS_DIR / 'execution_logs'
SCREENSHOTS_DIR = LOGS_DIR / 'screenshots'

# Garante que os diretórios existam
LOGS_DIR.mkdir(exist_ok=True)
EXECUTION_LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Diretório de downloads (onde os arquivos .txt estão)
DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'

# --- Configurações do Portal ISS.net ---

# URL do portal
ISSNET_URL = os.getenv('ISSNET_URL', 'https://www.issnetonline.com.br/goiania/online/login/login.aspx')

# Credenciais (estruturadas por Inscrição Municipal)
# Formato: {inscricao_municipal: {'user': '...', 'pass': '...'}}
CREDENTIALS = {
    os.getenv('ISSNET_INSCRICAO_1'): {
        'user': os.getenv('ISSNET_USER_1'),
        'pass': os.getenv('ISSNET_PASS_1'),
        'inscricao': os.getenv('ISSNET_INSCRICAO_1')
    },
    os.getenv('ISSNET_INSCRICAO_2'): {
        'user': os.getenv('ISSNET_USER_2'),
        'pass': os.getenv('ISSNET_PASS_2'),
        'inscricao': os.getenv('ISSNET_INSCRICAO_2')
    }
}

# Remove entradas None (caso alguma variável não esteja definida)
CREDENTIALS = {k: v for k, v in CREDENTIALS.items() if k is not None}

# --- Configurações de Execução do RPA ---

# Modo de execução: 'development' (headful) ou 'production' (headless)
RPA_MODE = os.getenv('RPA_MODE', 'development')

# Configurações do Playwright baseadas no modo
PLAYWRIGHT_CONFIG = {
    'development': {
        'headless': False,
        'slow_mo': 500,  # Desacelera ações em 500ms (para visualização)
        'devtools': False,  # Abre DevTools automaticamente
        'args': []
    },
    'production': {
        'headless': True,
        'slow_mo': 0,
        'devtools': False,
        'args': [
            '--disable-blink-features=AutomationControlled',  # Evita detecção de bot
            '--no-sandbox',  # Necessário em alguns ambientes de produção
            '--disable-dev-shm-usage'  # Evita problemas de memória compartilhada
        ]
    }
}

# Pega a configuração atual baseada no modo
BROWSER_CONFIG = PLAYWRIGHT_CONFIG.get(RPA_MODE, PLAYWRIGHT_CONFIG['development'])

# --- Timeouts (em milissegundos para Playwright) ---

# Timeout padrão para operações (30 segundos)
DEFAULT_TIMEOUT = int(os.getenv('RPA_TIMEOUT', '30')) * 1000

# Timeout para navegação de páginas (30 segundos)
NAVIGATION_TIMEOUT = 30000

# Timeout para upload de arquivos (60 segundos)
UPLOAD_TIMEOUT = int(os.getenv('RPA_UPLOAD_TIMEOUT', '60')) * 1000

# Timeout para elementos críticos (aguardar aparecer/desaparecer)
ELEMENT_TIMEOUT = 10000

# --- Configurações de Retry ---

# Número máximo de tentativas em caso de falha
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Tempo de espera entre tentativas (em segundos)
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))

# --- Configurações de Logging ---

# Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

# Salvar logs em arquivo?
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'True').lower() == 'true'

# --- Configurações de Screenshot ---

# Capturar screenshot em caso de erro?
SCREENSHOT_ON_ERROR = os.getenv('SCREENSHOT_ON_ERROR', 'True').lower() == 'true'

# Capturar screenshot em caso de sucesso?
SCREENSHOT_ON_SUCCESS = os.getenv('SCREENSHOT_ON_SUCCESS', 'True').lower() == 'true'

# --- Seletores do Portal (serão preenchidos após mapeamento) ---

# IMPORTANTE: Estes seletores serão atualizados após análise do portal
# Por enquanto, deixamos placeholders
SELECTORS = {
    'login': {
        'username_input': '#txtLogin',  # Placeholder
        'password_input': '#txtSenha',  # Placeholder
        'submit_button': '#btnEntrar',  # Placeholder
        'error_message': '.mensagem-erro',  # Placeholder
    },
    'menu': {
        'declaracoes': '#menuDeclaracoes',  # Placeholder
        'servicos_contratados': '#menuServicosContratados',  # Placeholder
        'importar_declaracao': '#btnImportar',  # Placeholder
    },
    'upload': {
        'file_input': '#fileUpload',  # Placeholder
        'separador_decimal_virgula': '#radSeparadorVirgula',  # Placeholder
        'separador_decimal_ponto': '#radSeparadorPonto',  # Placeholder
        'digito_verificador_sim': '#radDVSim',  # Placeholder
        'digito_verificador_nao': '#radDVNao',  # Placeholder
        'submit_button': '#btnImportar',  # Placeholder
        'loading_indicator': '#divLoading',  # Placeholder
    },
    'result': {
        'message_container': '#divMensagem',  # Placeholder
        'success_class': '.mensagem-sucesso',  # Placeholder
        'error_class': '.mensagem-erro',  # Placeholder
        'details_container': '#divDetalhes',  # Placeholder
    }
}

# --- Funções Auxiliares ---

def get_credentials_by_inscricao(inscricao_municipal):
    """
    Retorna as credenciais para uma determinada Inscrição Municipal.
    
    Args:
        inscricao_municipal (str): Número da inscrição municipal
        
    Returns:
        dict: Dicionário com 'user', 'pass' e 'inscricao' ou None se não encontrado
    """
    return CREDENTIALS.get(str(inscricao_municipal))

def is_development_mode():
    """Retorna True se estiver em modo de desenvolvimento."""
    return RPA_MODE.lower() == 'development'

def is_production_mode():
    """Retorna True se estiver em modo de produção."""
    return RPA_MODE.lower() == 'production'

# --- Validação de Configuração ---

def validate_config():
    """
    Valida se as configurações essenciais estão presentes.
    Lança exceção se algo crítico estiver faltando.
    """
    errors = []
    
    if not ISSNET_URL:
        errors.append("ISSNET_URL não está definida no .env")
    
    if not CREDENTIALS:
        errors.append("Nenhuma credencial válida encontrada no .env (ISSNET_USER_X, ISSNET_PASS_X, ISSNET_INSCRICAO_X)")
    
    if errors:
        raise ValueError(f"Erros de configuração detectados:\n" + "\n".join(f"- {e}" for e in errors))
    
    return True

# Executa validação ao importar o módulo
try:
    validate_config()
except ValueError as e:
    print(f"⚠️ AVISO: {e}")
    print("O RPA não poderá ser executado até que as configurações sejam corrigidas.")