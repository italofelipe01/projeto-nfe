# -*- coding: utf-8 -*-
"""
Módulo de Configuração do RPA.

Centraliza constantes, URLs, caminhos de diretórios e seletores CSS.
Define a arquitetura de acesso a credenciais multi-empresa.
"""
# Importações de tipagem para código limpo e type-checking robusto (PEP 484)
from typing import Dict, Any, Optional

import os
import csv
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env na raiz
load_dotenv()

# --- Diretórios do Projeto ---
# Define a raiz do projeto voltando dois níveis a partir deste arquivo
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RPA_DIR = Path(__file__).resolve().parent

# Estrutura de Logs (Apenas Textuais)
LOGS_DIR = PROJECT_ROOT / "rpa_logs"
EXECUTION_LOGS_DIR = LOGS_DIR / "execution_logs"
DEBUG_SCREENSHOTS_DIR = LOGS_DIR / "debug_screenshots"
# Garante que os diretórios de log existam
LOGS_DIR.mkdir(exist_ok=True)
EXECUTION_LOGS_DIR.mkdir(exist_ok=True)
DEBUG_SCREENSHOTS_DIR.mkdir(exist_ok=True)


# Diretório de downloads/uploads (onde ficam os arquivos TXT gerados)
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
# É crucial garantir a existência do diretório de downloads/uploads para evitar erros de I/O.
DOWNLOADS_DIR.mkdir(exist_ok=True)


# --- Configurações do Portal ISS.net ---

# Renomeado de ISSNET_LOGIN_URL para ISSNET_URL para compatibilidade com __init__.py
ISSNET_URL = os.getenv(
    "ISSNET_URL", "https://www.issnetonline.com.br/goiania/online/login/login.aspx"
)

# URLs Diretas (Para navegação rápida se necessário)
URLS: Dict[str, str] = {
    "importacao": "https://www.issnetonline.com.br/goiania/online/Servicos_Contratados/ImportacaoServicosContratados.aspx",
    "consulta_importacao": "https://www.issnetonline.com.br/goiania/online/Servicos_Contratados/ConsultaImportacaoServicosContratados.aspx",
}

# Define um tipo auxiliar para as credenciais de uma única empresa
CredentialData = Dict[str, Optional[str]]

# --- Carregamento de Credenciais (Híbrido: .env + CSV) ---

# 1. Carrega Credenciais Globais (Master Login) do .env
GLOBAL_USER = os.getenv("ISSNET_USER")
GLOBAL_PASS = os.getenv("ISSNET_PASS")


def load_companies_from_csv() -> Dict[str, CredentialData]:
    """
    Lê o arquivo configuracoes.csv e constrói o dicionário de credenciais.
    Combina o login global (.env) com os dados específicos da empresa (CSV).
    """
    csv_path = PROJECT_ROOT / "configuracoes.csv"
    credentials_map: Dict[str, CredentialData] = {}

    if not csv_path.exists():
        print(f"⚠️ Aviso: Arquivo {csv_path} não encontrado.")
        return {}

    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            # Assume que o CSV usa ponto e vírgula como separador
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:
                inscricao = row.get("inscricao_municipal")
                cnpj = row.get("cnpj")

                if inscricao:
                    # Remove formatação se houver (apenas números)
                    inscricao_clean = "".join(filter(str.isdigit, inscricao))

                    # Popula o dicionário usando a Inscrição como chave
                    credentials_map[inscricao_clean] = {
                        "user": GLOBAL_USER,
                        "pass": GLOBAL_PASS,
                        "inscricao": inscricao_clean,
                        "cnpj": cnpj, # Mantém formatação do CNPJ se vier do CSV ou limpa se necessário
                    }

                    # Também mapeia pela inscrição original (com formatação) caso venha assim do frontend
                    if inscricao != inscricao_clean:
                        credentials_map[inscricao] = credentials_map[inscricao_clean]

    except Exception as e:
        print(f"⚠️ Erro ao ler configuracoes.csv: {e}")

    return credentials_map


# Carrega as credenciais dinamicamente
CREDENTIALS: Dict[Optional[str], CredentialData] = load_companies_from_csv()

# Remove chaves que possam estar vazias
CREDENTIALS = {k: v for k, v in CREDENTIALS.items() if k is not None}

# Garante que as chaves do dicionário final são strings (para lookup)
FINAL_CREDENTIALS: Dict[str, CredentialData] = {
    str(k): v for k, v in CREDENTIALS.items()
}


# --- Configurações do Playwright ---
RPA_MODE = os.getenv("RPA_MODE", "development")

# Modern and realistic desktop Chrome user-agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Anti-detection browser arguments
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-dev-shm-usage",
]


PLAYWRIGHT_CONFIG: Dict[str, Any] = {
    "development": {
        "headless": False,  # Vê o navegador abrindo
        "slow_mo": 50,
        "devtools": False,
        "args": BROWSER_ARGS,
    },
    "production": {
        "headless": False,  # Alterado para False para depurar desafios Cloudflare
        "slow_mo": 0,
        "devtools": False,
        "args": BROWSER_ARGS,
    },
}
# O Python acessa o item 'RPA_MODE' para carregar a configuração, mas usamos Any para evitar tipagem complexa para BROWSER_CONFIG.
BROWSER_CONFIG: Dict[str, Any] = PLAYWRIGHT_CONFIG.get(
    RPA_MODE, PLAYWRIGHT_CONFIG["development"]
)

# --- Timeouts (em milissegundos) ---
DEFAULT_TIMEOUT = int(os.getenv("RPA_DEFAULT_TIMEOUT", "30000"))
LOGIN_TIMEOUT = int(os.getenv("RPA_LOGIN_TIMEOUT", "60000"))
NAVIGATION_TIMEOUT = 60000
UPLOAD_TIMEOUT = 120000

# --- SELETORES (Mapeamento do DOM) ---
SELECTORS: Dict[str, Any] = {
    "login": {
        "username_input": "#txtLogin",
        # O campo é readonly e a interação deve ser via teclado virtual (authentication.py)
        "password_input": "#txtSenha",
        "submit_button": "#btnAcessar",
        "error_message": ".alert-danger",
        "virtual_keyboard": {
            "btn1": "#btn1",
            "btn2": "#btn2",
            "btn3": "#btn3",
            "btn4": "#btn4",
            "btn5": "#btn5",
            "limpar": "#btnLimpar",
        },
    },
    "selecao_empresa": {
        "input_inscricao": "#txtCae",
        "input_filtro_cnpj": "#TxtCPF",
        "btn_localizar": "#imbLocalizar",

        # O seletor da linha específica foi removido.
        # A nova lógica em portal_navigator.py constrói o seletor dinamicamente.

        # Validadores de carregamento
        "loading_overlay": "#divCarregando", # Padrão NotaControl, mesmo que oculto no HTML estático
    },
    "importacao": {
        # O input para injeção de arquivo (file_uploader.py)
        "input_arquivo": "#txtUpload",
        "btn_importar": "#btnImportarArquivo",
        # O overlay que dita o fim do processamento do servidor (sincronização crítica)
        "loading_overlay": "#loading",
        "chk_separador": "#radSeparadorPonto",
        "chk_dv": "#radDVSim",
        "msg_resultado": "#divMensagemResultado",
        "msg_erro_detalhe": "#lblErro",
        "btn_atualizar_status": "#imbLocalizar",
        "grid_status_row": "#dgImportacao tr:nth-child(2)",
    },
}

# ----------------------------------------------------------------------
# FUNÇÕES AUXILIARES (Requeridas pelo rpa/__init__.py para expor a lógica)
# ----------------------------------------------------------------------


def is_development_mode() -> bool:
    """
    Verifica se o robô está rodando em modo de desenvolvimento (com interface gráfica visível).
    Retorno: Booleano indicando o modo de execução.
    """
    return RPA_MODE == "development"


def is_production_mode() -> bool:
    """
    Verifica se o robô está rodando em modo de produção (headless - sem interface gráfica).
    Retorno: Booleano indicando o modo de execução.
    """
    return RPA_MODE == "production"


def get_credentials_by_inscricao(inscricao: str) -> Optional[CredentialData]:
    """
    Busca e retorna as credenciais (user/pass) de uma empresa pela Inscrição Municipal.
    A tipagem explícita (Optional[CredentialData]) resolve o warning do Pylance
    ao indicar claramente que a função pode retornar um dicionário ou None.

    Args:
        inscricao: A Inscrição Municipal da empresa a ser procurada.

    Retorno: Um dicionário com 'user', 'pass' e 'inscricao', ou None se a inscrição não for encontrada.
    """
    # Usamos .get() que retorna None se a chave não existir, o que é mapeado pela tipagem Optional.
    return FINAL_CREDENTIALS.get(inscricao)


# --- Validação Básica ---
def validate_config():
    errors = []

    if not ISSNET_URL:
        errors.append("ISSNET_URL não definida.")

    if not GLOBAL_USER or not GLOBAL_PASS:
        errors.append("ISSNET_USER ou ISSNET_PASS não definidos no .env.")

    # Usamos FINAL_CREDENTIALS para garantir que a checagem é feita após a filtragem de chaves None
    if not FINAL_CREDENTIALS:
        # Apenas um aviso, pois o CSV pode estar vazio inicialmente
        print("⚠️ Aviso: Nenhuma empresa carregada de configuracoes.csv.")

    if errors:
        # A impressão de aviso é mantida para visibilidade no console
        print(f"⚠️  Aviso de Configuração RPA: {', '.join(errors)}")


try:
    validate_config()
except Exception as e:
    # Captura de erro para debug em ambiente de CLI
    print(f"⚠️ Configuração RPA Inválida: {e}")
