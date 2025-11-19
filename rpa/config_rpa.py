# -*- coding: utf-8 -*-
"""
Módulo de Configuração do RPA (Validado).

Baseado na Documentação Técnica ISSNET Goiânia e path.json.
Centraliza constantes, caminhos de diretórios e seletores CSS.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env na raiz
load_dotenv()

# --- Diretórios do Projeto ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RPA_DIR = Path(__file__).resolve().parent

# Estrutura de Logs (Apenas Textuais)
LOGS_DIR = PROJECT_ROOT / 'rpa_logs'
EXECUTION_LOGS_DIR = LOGS_DIR / 'execution_logs'

# Garante que os diretórios de log existam
LOGS_DIR.mkdir(exist_ok=True)
EXECUTION_LOGS_DIR.mkdir(exist_ok=True)

# Diretório de downloads/uploads (onde ficam os arquivos TXT gerados)
DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'

# --- Configurações do Portal ISS.net ---

# URL de Login (Padrão)
ISSNET_LOGIN_URL = os.getenv('ISSNET_URL', 'https://www.issnetonline.com.br/goiania/online/login/login.aspx')

# URLs Diretas (Para navegação rápida se necessário)
URLS = {
    'importacao': 'https://www.issnetonline.com.br/goiania/online/Servicos_Contratados/ImportacaoServicosContratados.aspx',
    'consulta_importacao': 'https://www.issnetonline.com.br/goiania/online/Servicos_Contratados/ConsultaImportacaoServicosContratados.aspx',
}

# Credenciais (Multi-empresa)
# O robô seleciona qual usar baseado na Inscrição Municipal passada pelo Frontend
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
# Remove chaves que possam estar vazias (caso o .env não tenha todas as empresas)
CREDENTIALS = {k: v for k, v in CREDENTIALS.items() if k is not None}

# --- Configurações do Playwright ---
RPA_MODE = os.getenv('RPA_MODE', 'development')

PLAYWRIGHT_CONFIG = {
    'development': {
        'headless': False, # Vê o navegador abrindo
        'slow_mo': 800,    # Lento para debug visual
        'devtools': False, 
        'args': ['--start-maximized']
    },
    'production': {
        'headless': True,  # Execução em background (mais rápido)
        'slow_mo': 100,
        'devtools': False,
        'args': [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080'
        ]
    }
}
BROWSER_CONFIG = PLAYWRIGHT_CONFIG.get(RPA_MODE, PLAYWRIGHT_CONFIG['development'])

# --- Timeouts (em milissegundos) ---
DEFAULT_TIMEOUT = int(os.getenv('RPA_TIMEOUT', '30')) * 1000
NAVIGATION_TIMEOUT = 60000 # Portal costuma ser lento no carregamento de grids
UPLOAD_TIMEOUT = 120000    # Processamento de arquivos grandes pode demorar

# --- SELETORES (Mapeamento do DOM) ---
SELECTORS = {
    'login': {
        'username_input': '#txtLogin',
        'password_input': '#txtSenha',      # Campo Readonly
        'submit_button': '#btnAcessar',
        'error_message': '.alert-danger',
        # Mapeamento dos botões do teclado virtual (IDs fixos no HTML)
        'virtual_keyboard': {
            'btn1': '#btn1',
            'btn2': '#btn2',
            'btn3': '#btn3',
            'btn4': '#btn4',
            'btn5': '#btn5',
            'limpar': '#btnLimpar'
        }
    },
    'selecao_empresa': {
        'input_inscricao': '#txtCae',      # Filtro por Inscrição Municipal
        'input_cnpj': '#TxtCPF',           # Filtro por CNPJ
        'btn_localizar': '#imbLocalizar',  # Botão Lupa
        'loading_overlay': '#loading',     # Overlay "Aguarde"
        # Nota: A seleção da linha é dinâmica e feita via código no portal_navigator.py
    },
    'importacao': {
        'input_arquivo': '#txtUpload',             # Input hidden onde injetamos o arquivo
        'btn_importar': '#btnImportarArquivo',     # Botão verde de envio
        'loading_overlay': '#loading',             # Overlay crítico para sincronização
        'chk_separador': '#radSeparadorPonto',     # Checkbox para definir ponto como decimal
        'chk_dv': '#radDVSim',                     # Checkbox de Dígito Verificador (se houver)
        'msg_resultado': '#divMensagemResultado',  # Container da resposta final
        'msg_erro_detalhe': '#lblErro'             # Label com stack trace ou detalhe do erro
    }
}

# --- Validação Básica ---
def validate_config():
    errors = []
    if not ISSNET_LOGIN_URL: errors.append("ISSNET_URL não definida.")
    if not CREDENTIALS: errors.append("Nenhuma credencial válida encontrada no .env.")
    
    if errors:
        # Loga o erro mas não quebra a importação imediatamente (deixa o controller tratar)
        print(f"⚠️  Aviso de Configuração: {', '.join(errors)}")

try:
    validate_config()
except Exception as e:
    print(f"⚠️ Configuração Inválida: {e}")