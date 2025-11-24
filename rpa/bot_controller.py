# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from rpa.config_rpa import CREDENTIALS, BROWSER_CONFIG, DEFAULT_TIMEOUT
from rpa.utils import setup_logger
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
        logger.info(f"[{self.task_id}] Iniciando Robô. IM: {inscricao_municipal}")

        creds = CREDENTIALS.get(str(inscricao_municipal))
        if not creds:
            msg = f"Credenciais não achadas p/ {inscricao_municipal}"
            logger.error(f"[{self.task_id}] {msg}")
            return {"success": False, "message": msg}

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
            user = creds.get("user")
            password = creds.get("pass")

            if not user or not password:
                raise ValueError(
                    f"Credenciais incompletas para {inscricao_municipal} (Usuário ou Senha vazios)."
                )

            auth = ISSAuthenticator(self.page, self.task_id)
            if not auth.login(user, password):
                raise Exception("Falha na etapa de autenticação.")

            # FASE 2: SELEÇÃO DE EMPRESA
            nav = ISSNavigator(self.page, self.task_id)
            nav.select_contribuinte(creds["inscricao"])

            # FASE 3: UPLOAD
            uploader = ISSUploader(self.page, self.task_id)
            uploader.upload_file(file_path)

            # FASE 4: RESULTADOS
            parser = ISSResultParser(self.page, self.task_id)
            resultado = parser.parse()

            return resultado

        except Exception as e:
            logger.exception(f"[{self.task_id}] Erro fatal durante execução")
            return {
                "success": False,
                "message": f"Erro técnico: {str(e)}",
                "details": "Consulte os logs técnicos.",
            }

        finally:
            logger.info(f"[{self.task_id}] Encerrando sessão.")
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if playwright:
                playwright.stop()


def run_rpa_process(
    task_id: str, file_path: str, inscricao_municipal: str, is_dev_mode: bool = False
):
    bot = ISSBot(task_id, is_dev_mode)
    return bot.execute(file_path, inscricao_municipal)
