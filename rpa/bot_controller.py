# -*- coding: utf-8 -*-
"""
Controlador Principal do Robô (rpa/bot_controller.py).

Responsabilidade:
1. Orquestrar o ciclo de vida do navegador (Launch/Close).
2. Instanciar e coordenar os módulos especialistas (Login, Navegação, Upload).
3. Gerir sessões, contextos e tratamento de erros de alto nível.

Arquitetura: Padrão Facade/Controller.
"""

import os
from playwright.sync_api import sync_playwright
from rpa.config_rpa import CREDENTIALS, BROWSER_CONFIG, DEFAULT_TIMEOUT
from rpa.utils import setup_logger

# Importação dos módulos especialistas
from rpa.authentication import ISSAuthenticator
from rpa.portal_navigator import ISSNavigator
from rpa.file_uploader import ISSUploader
from rpa.result_parser import ISSResultParser

logger = setup_logger()

class ISSBot:
    def __init__(self, task_id: str, is_dev_mode: bool = False):
        self.task_id = task_id
        self.is_dev_mode = is_dev_mode
        self.browser = None
        self.context = None
        self.page = None

    def execute(self, file_path: str, inscricao_municipal: str) -> dict:
        """
        Executa o fluxo completo de automação.
        
        Args:
            file_path (str): Caminho absoluto do arquivo TXT a ser enviado.
            inscricao_municipal (str): Inscrição da empresa para login/seleção.
            
        Returns:
            dict: Resultado padronizado {'success': bool, 'message': str, ...}
        """
        logger.info(f"[{self.task_id}] 🚀 Iniciando execução do Robô para IM: {inscricao_municipal}")

        # 1. Recuperação de Credenciais
        # Busca no dicionário carregado do .env em config_rpa.py
        creds = CREDENTIALS.get(str(inscricao_municipal))
        if not creds:
            msg = f"Credenciais não encontradas para a inscrição {inscricao_municipal}. Verifique o .env."
            logger.error(f"[{self.task_id}] {msg}")
            return {'success': False, 'message': msg}

        playwright = None
        try:
            playwright = sync_playwright().start()
            
            # 2. Configuração do Browser
            # Ajusta headless dinamicamente se estiver em modo dev ou produção
            launch_config = BROWSER_CONFIG.copy()
            if self.is_dev_mode:
                launch_config['headless'] = False
            
            self.browser = playwright.chromium.launch(**launch_config)
            
            # Cria contexto com vídeo se necessário (opcional para debug)
            self.context = self.browser.new_context(
                record_video_dir=f"rpa_logs/videos/{self.task_id}" if self.is_dev_mode else None,
                viewport={'width': 1280, 'height': 720}
            )
            self.page = self.context.new_page()
            self.page.set_default_timeout(DEFAULT_TIMEOUT)

            # --- FASE 1: LOGIN ---
            auth = ISSAuthenticator(self.page, self.task_id)
            if not auth.login(creds['user'], creds['pass']):
                raise Exception("Falha na etapa de autenticação.")

            # --- FASE 2: SELEÇÃO DE CONTEXTO ---
            nav = ISSNavigator(self.page, self.task_id)
            nav.selecionar_empresa(creds['inscricao'])

            # --- FASE 3: UPLOAD ---
            uploader = ISSUploader(self.page, self.task_id)
            uploader.upload_file(file_path)

            # --- FASE 4: RESULTADOS ---
            parser = ISSResultParser(self.page, self.task_id)
            resultado = parser.parse()

            return resultado

        except Exception as e:
            logger.exception(f"[{self.task_id}] 💥 Erro fatal durante execução")
            
            return {
                'success': False, 
                'message': f"Erro técnico no processamento: {str(e)}",
                'details': "Consulte os logs técnicos para mais informações."
            }
            
        finally:
            # Garante limpeza de recursos
            logger.info(f"[{self.task_id}] Encerrando sessão do navegador.")
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if playwright: playwright.stop()

# --- Interface Pública (Entry Point) ---

def run_rpa_process(task_id: str, file_path: str, inscricao_municipal: str, is_dev_mode: bool = False):
    """
    Wrapper simples para ser chamado pelo Flask (app/main.py).
    """
    bot = ISSBot(task_id, is_dev_mode)
    return bot.execute(file_path, inscricao_municipal)