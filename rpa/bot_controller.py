# -*- coding: utf-8 -*-
from typing import Optional
import time
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from rpa.config_rpa import CREDENTIALS, BROWSER_CONFIG, DEFAULT_TIMEOUT
from rpa.utils import setup_logger
from rpa.authentication import ISSAuthenticator
from rpa.portal_navigator import ISSNavigator
from rpa.file_uploader import ISSUploader
from rpa.result_parser import ISSResultParser
from rpa.error_handler import PortalOfflineError

logger = setup_logger()


class ISSBot:
    def __init__(self, task_id: str, is_dev_mode: bool = False):
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
        :param status_callback: Função opcional (fn(msg)) para reportar progresso.
        """
        logger.info(f"[{self.task_id}] Iniciando Robô. IM: {inscricao_municipal}")
        if status_callback:
            status_callback("Iniciando Robô...")

        creds = CREDENTIALS.get(str(inscricao_municipal))
        if not creds:
            msg = f"Credenciais não achadas p/ {inscricao_municipal}"
            logger.error(f"[{self.task_id}] {msg}")
            return {"success": False, "message": msg}

        max_retries = 3
        attempt = 0
        backoff_base = 2  # Segundos

        while attempt < max_retries:
            attempt += 1
            playwright = None
            try:
                playwright = sync_playwright().start()

                launch_config = BROWSER_CONFIG.copy()
                if self.is_dev_mode:
                    launch_config["headless"] = False

                self.browser = playwright.chromium.launch(**launch_config)

                record_dir = None
                if self.is_dev_mode:
                    record_dir = f"rpa_logs/videos/{self.task_id}"

                self.context = self.browser.new_context(
                    record_video_dir=record_dir, viewport={"width": 1280, "height": 720}
                )
                self.page = self.context.new_page()
                self.page.set_default_timeout(DEFAULT_TIMEOUT)

                # FASE 1: LOGIN
                if status_callback:
                    status_callback(f"Realizando Login (Tentativa {attempt})...")

                user = creds.get("user")
                password = creds.get("pass")
                inscricao = creds.get("inscricao")

                if not user or not password or not inscricao:
                    raise ValueError(
                        f"Credenciais incompletas para {inscricao_municipal} (Usuário, Senha ou Inscrição vazios)."
                    )

                auth = ISSAuthenticator(self.page, self.task_id)
                if not auth.login(user, password):
                    # Login falhou, mas não lançou exceção (retornou False).
                    # Consideramos erro de negócio (senha errada), então não retry.
                    raise Exception("Falha na etapa de autenticação (Login recusado).")

                # FASE 2: SELEÇÃO DE EMPRESA
                if status_callback:
                    status_callback("Selecionando Empresa...")

                # Recupera o CNPJ para a seleção de empresa
                cnpj = creds.get("cnpj")
                if not cnpj:
                    raise ValueError(
                        f"CNPJ não encontrado nas credenciais para a Inscrição Municipal {inscricao_municipal}."
                    )

                nav = ISSNavigator(self.page, self.task_id)
                nav.select_contribuinte(inscricao_municipal, cnpj)

                # FASE 3: UPLOAD
                if status_callback:
                    status_callback("Enviando Arquivo...")

                uploader = ISSUploader(self.page, self.task_id)
                uploader.upload_file(file_path)

                # FASE 4: RESULTADOS
                if status_callback:
                    status_callback("Lendo Resultados...")

                parser = ISSResultParser(self.page, self.task_id)
                resultado = parser.parse()

                if status_callback:
                    status_callback("Concluído.")

                return resultado

            except PortalOfflineError as e:
                # ERRO DE INFRAESTRUTURA -> RETRY
                logger.warning(
                    f"[{self.task_id}] Portal offline ou instável (Tentativa {attempt}/{max_retries}): {e}"
                )
                if attempt >= max_retries:
                    logger.error(f"[{self.task_id}] Esgotadas tentativas de conexão.")
                    return {
                        "success": False,
                        "message": "Erro de Infraestrutura: Portal indisponível após múltiplas tentativas.",
                        "details": str(e),
                    }

                # Backoff Exponencial
                wait_time = backoff_base ** attempt
                if status_callback:
                    status_callback(f"Portal instável. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue  # Tenta novamente

            except Exception as e:
                # ERRO GERAL (Negócio, Código, Autenticação) -> ABORTA
                logger.exception(f"[{self.task_id}] Erro fatal durante execução")
                return {
                    "success": False,
                    "message": f"Erro técnico: {str(e)}",
                    "details": "Consulte os logs técnicos.",
                }

            finally:
                logger.info(f"[{self.task_id}] Encerrando sessão (Cleanup da tentativa).")
                if self.context:
                    self.context.close()
                if self.browser:
                    self.browser.close()
                if playwright:
                    playwright.stop()


def run_rpa_process(
    task_id: str,
    file_path: str,
    inscricao_municipal: str,
    is_dev_mode: bool = False,
    status_callback=None,
):
    bot = ISSBot(task_id, is_dev_mode)
    return bot.execute(file_path, inscricao_municipal, status_callback)
