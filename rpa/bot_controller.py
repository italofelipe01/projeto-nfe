# -*- coding: utf-8 -*-
"""
Módulo Orquestrador do Robô (rpa/bot_controller.py).

Responsabilidade:
1. Orquestrar o fluxo completo de automação (Login -> Navegação -> Upload -> Extração).
2. Gerenciar a inicialização e o encerramento do Playwright (navegador).
3. Implementar uma política de retentativas (retry) para falhas de infraestrutura.
4. Coordenar os módulos especializados (Authenticator, Navigator, Uploader, Parser).
"""

import time
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from playwright_stealth import Stealth

# Módulos de configuração e utilitários
from rpa.config_rpa import BROWSER_CONFIG, CREDENTIALS, LOGIN_TIMEOUT, USER_AGENT
from rpa.error_handler import AuthenticationError, PortalOfflineError
from rpa.utils import setup_logger

# Módulos de Ação Especializados
from rpa.authentication import ISSAuthenticator
from rpa.file_uploader import ISSUploader
from rpa.portal_navigator import ISSNavigator
from rpa.result_parser import ISSResultParser

# Configuração do Logger para este módulo
logger = setup_logger("rpa_bot_controller")


class ISSBot:
    """
    Classe principal do Robô, encapsulando a lógica de automação do portal ISS.net.
    """

    def __init__(self, task_id: str, is_dev_mode: bool = False):
        """
        Inicializa o robô.

        Args:
            task_id (str): ID único para rastrear a execução nos logs.
            is_dev_mode (bool): Se True, executa em modo 'headful' (visível).
        """
        self.task_id = task_id
        self.is_dev_mode = is_dev_mode
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def execute(
        self,
        file_path: str,
        inscricao_municipal: str,
        status_callback=None,
    ) -> dict:
        """
        Executa o fluxo RPA completo com política de retry para falhas de infraestrutura.
        Utiliza um loop de retentativas com backoff exponencial para lidar com instabilidades do portal.

        Args:
            file_path (str): Caminho do arquivo .txt a ser enviado.
            inscricao_municipal (str): Inscrição Municipal para login e seleção.
            status_callback (function, optional): Função para reportar progresso em tempo real.

        Returns:
            dict: Dicionário com o resultado da operação ('success', 'message', 'details').
        """
        logger.info(f"[{self.task_id}] Iniciando Robô. IM: {inscricao_municipal}")
        if status_callback:
            status_callback("Iniciando Robô...")

        # Validação de Credenciais
        creds = CREDENTIALS.get(str(inscricao_municipal))
        if not creds:
            msg = f"Credenciais não encontradas para a Inscrição Municipal '{inscricao_municipal}'."
            logger.error(f"[{self.task_id}] {msg}")
            return {"success": False, "message": msg}

        # --- Lógica de Retentativas ---
        max_retries = 3
        attempt = 0
        backoff_base = 2  # Segundos

        while attempt < max_retries:
            attempt += 1
            playwright = None
            try:
                # --- FASE 0: INICIALIZAÇÃO DO NAVEGADORES ---
                logger.debug(
                    f"[{self.task_id}] [Tentativa {attempt}] Iniciando Playwright..."
                )
                if status_callback:
                    status_callback(f"Conectando ao portal (Tentativa {attempt})...")

                playwright = sync_playwright().start()

                launch_config = BROWSER_CONFIG.copy()
                if self.is_dev_mode:
                    launch_config["headless"] = False

                self.browser = playwright.chromium.launch(**launch_config)

                # --- Stealth Configuration ---
                stealth = Stealth(
                    navigator_languages_override=["pt-BR", "pt"],
                    vendor_override="Google Inc.",
                    webgl_vendor_override="Intel Inc.",
                    renderer_override="Intel Iris OpenGL Engine",
                    fix_hairline=True
                )

                record_dir = f"rpa_logs/videos/{self.task_id}" if self.is_dev_mode else None

                self.context = self.browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    locale="pt-BR",
                    record_video_dir=record_dir,
                )

                stealth.apply_stealth_sync(self.context)

                # Remove WebDriver fingerprint
                self.context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                self.page = self.context.new_page()
                self.page.set_default_timeout(LOGIN_TIMEOUT)


                # --- FASE 1: LOGIN ---
                user, password, inscricao = (
                    creds.get("user"),
                    creds.get("pass"),
                    creds.get("inscricao"),
                )
                if not all([user, password, inscricao]):
                    raise ValueError(
                        f"Credenciais incompletas para {inscricao_municipal} (Usuário, Senha ou Inscrição vazios)."
                    )

                auth = ISSAuthenticator(self.page, self.task_id)
                # O callback é passado para o método de login para granularidade
                auth.login(user, password, status_callback)

                # --- FASE 2: SELEÇÃO DE EMPRESA ---
                if status_callback:
                    status_callback("Selecionando empresa...")

                nav = ISSNavigator(self.page, self.task_id)
                nav.select_contribuinte(inscricao)

                # --- FASE 3: UPLOAD ---
                if status_callback:
                    status_callback("Enviando arquivo...")

                uploader = ISSUploader(self.page, self.task_id)
                uploader.upload_file(file_path)

                # --- FASE 4: LEITURA DE RESULTADOS ---
                if status_callback:
                    status_callback("Analisando resultados...")

                parser = ISSResultParser(self.page, self.task_id)
                resultado = parser.parse()

                if status_callback:
                    status_callback("Processo concluído com sucesso!")

                return resultado  # Sucesso, sai do loop

            except PortalOfflineError as e:
                logger.warning(
                    f"[{self.task_id}] Portal offline ou instável (Tentativa {attempt}/{max_retries}): {e}"
                )
                if attempt >= max_retries:
                    logger.error(
                        f"[{self.task_id}] Esgotadas as tentativas de conexão."
                    )
                    return {
                        "success": False,
                        "message": "Erro de Infraestrutura: O portal parece estar indisponível.",
                        "details": str(e),
                    }
                # Backoff Exponencial
                wait_time = backoff_base**attempt
                if status_callback:
                    status_callback(
                        f"Portal instável. Nova tentativa em {wait_time}s..."
                    )
                time.sleep(wait_time)
                # Continue para a próxima iteração do `while`

            except AuthenticationError as e:
                # Erro de autenticação é fatal e não deve ser retentado.
                logger.error(f"[{self.task_id}] Falha de autenticação: {e}")
                # A mensagem de erro já é amigável, vinda da exceção.
                # A screenshot é tirada dentro do módulo de autenticação.
                return {
                    "success": False,
                    "message": str(e),
                    "details": "Verifique as credenciais ou procure por uma screenshot de depuração na pasta 'rpa_logs/debug_screenshots'.",
                }

            except Exception as e:
                # Erro fatal (negócio, código, etc.) -> Aborta
                logger.exception(f"[{self.task_id}] Erro fatal durante a execução do robô.")
                return {
                    "success": False,
                    "message": f"Erro inesperado: {str(e)}",
                    "details": "Um erro técnico impediu a conclusão do processo. Verifique os logs para mais detalhes.",
                }

            finally:
                # --- LIMPEZA (CLEANUP) ---
                logger.info(
                    f"[{self.task_id}] [Tentativa {attempt}] Encerrando sessão do navegador."
                )
                if self.context:
                    self.context.close()
                if self.browser:
                    self.browser.close()
                if playwright:
                    playwright.stop()

        # Este retorno só é alcançado se o loop terminar sem sucesso
        return {
            "success": False,
            "message": "Ocorreu um erro inesperado no controle de tentativas.",
            "details": "O robô não conseguiu concluir a tarefa após todas as tentativas.",
        }

def run_rpa_process(
    task_id: str,
    file_path: str,
    inscricao_municipal: str,
    is_dev_mode: bool = False,
    status_callback=None,
) -> dict:
    """
    Função de ponto de entrada para iniciar o processo de RPA.
    Cria uma instância do ISSBot e executa o fluxo.
    """
    bot = ISSBot(task_id, is_dev_mode)
    return bot.execute(file_path, inscricao_municipal, status_callback)
