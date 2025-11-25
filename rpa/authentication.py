# -*- coding: utf-8 -*-
"""
Módulo de Autenticação (rpa/authentication.py).

Responsabilidade:
1. Realizar o login no portal ISS.net.
2. Resolver o desafio do Teclado Virtual Dinâmico.
3. Validar se o acesso foi concedido, com mecanismos de robustez e debug.
"""

import time
from pathlib import Path
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

# Módulos de configuração e utilitários
from rpa.config_rpa import SELECTORS, ISSNET_URL, NAVIGATION_TIMEOUT
from rpa.error_handler import AuthenticationError
from rpa.utils import setup_logger

# Configuração do Logger para este módulo
logger = setup_logger("rpa_authentication")


class ISSAuthenticator:
    """
    Encapsula toda a lógica de autenticação no portal ISS.net,
    incluindo a resolução do teclado virtual e tratamento de erros aprimorado.
    """

    def __init__(self, page: Page, task_id: str):
        """
        Inicializa o autenticador.

        Args:
            page (Page): Objeto Page do Playwright (sessão do navegador).
            task_id (str): ID da tarefa para rastreamento nos logs.
        """
        self.page = page
        self.task_id = task_id

    def login(
        self,
        user: str,
        password: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Executa o fluxo completo de login, com callbacks de status e robustez aprimorada.

        Args:
            user (str): Usuário (CPF/CNPJ/Inscrição).
            password (str): Senha numérica.
            status_callback (Callable, optional): Função para reportar progresso.

        Returns:
            bool: True se o login for bem-sucedido.

        Raises:
            AuthenticationError: Se houver erro de credencial, bloqueio, ou timeout.
        """
        logger.info(
            f"[{self.task_id}] 🔐 Iniciando autenticação para o usuário '{user[:4]}...'"
        )
        if status_callback:
            status_callback("Realizando login...")

        try:
            # 1. Navegação Inicial
            logger.debug(f"[{self.task_id}] Navegando para: {ISSNET_URL}")
            if status_callback:
                status_callback("Navegando para o portal...")
            self.page.goto(ISSNET_URL, timeout=NAVIGATION_TIMEOUT)

            # 2. Preenchimento do Usuário
            if status_callback:
                status_callback("Inserindo usuário...")
            user_selector = SELECTORS["login"]["username_input"]
            self.page.wait_for_selector(user_selector, state="visible")
            self.page.fill(user_selector, user)

            # 3. Resolução do Teclado Virtual
            if status_callback:
                status_callback("Resolvendo teclado virtual...")
            self._resolver_teclado_virtual(password)

            # 4. Simula comportamento humano e submete
            time.sleep(
                1
            )  # Delay estratégico para parecer menos robótico antes do clique
            logger.debug(f"[{self.task_id}] Clicando no botão de submissão.")
            if status_callback:
                status_callback("Enviando credenciais...")
            btn_submit = SELECTORS["login"]["submit_button"]
            self.page.click(btn_submit)

            # 5. Validação do Sucesso
            logger.debug(f"[{self.task_id}] Aguardando redirecionamento pós-login...")
            try:
                # Timeout aumentado para 30s para acomodar anti-bot checks
                self.page.wait_for_url(
                    "**/SelecionarContribuinte.aspx*", timeout=NAVIGATION_TIMEOUT
                )
                logger.info(
                    f"[{self.task_id}] ✅ Login para '{user[:4]}...' bem-sucedido!"
                )
                return True
            except PlaywrightTimeoutError:
                # Se o timeout ocorrer, tira um screenshot para diagnóstico
                screenshot_path = self._take_error_screenshot()
                logger.error(
                    f"[{self.task_id}] Timeout ao aguardar login. A página pode ter um CAPTCHA ou bloqueio. Screenshot salvo em: {screenshot_path}"
                )
                raise AuthenticationError(
                    f"Falha no login (Timeout). Verifique o screenshot de erro: {Path(screenshot_path).name}"
                )

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            logger.error(
                f"[{self.task_id}] Erro técnico inesperado durante a autenticação: {e}"
            )
            raise AuthenticationError(f"Erro técnico durante o login: {e}") from e

    def _resolver_teclado_virtual(self, password: str):
        """
        Lógica para lidar com o Teclado Virtual.
        """
        keyboard_map = SELECTORS["login"]["virtual_keyboard"]
        logger.debug(f"[{self.task_id}] Processando teclado virtual...")

        for digit in password:
            clicked = False
            for btn_key, btn_selector in keyboard_map.items():
                if btn_key == "limpar":
                    continue
                button = self.page.locator(btn_selector)
                if not button.is_visible():
                    continue
                btn_value = button.get_attribute("value") or button.inner_text()
                if digit in btn_value:
                    button.click()
                    time.sleep(0.3)
                    clicked = True
                    break
            if not clicked:
                screenshot_path = self._take_error_screenshot()
                logger.error(
                    f"[{self.task_id}] Dígito '{digit}' não encontrado no teclado virtual. Screenshot: {screenshot_path}"
                )
                raise AuthenticationError(
                    f"Dígito '{digit}' não encontrado no teclado. Verifique o screenshot."
                )
        logger.info(f"[{self.task_id}] Teclado virtual processado com sucesso.")

    def _take_error_screenshot(self) -> str:
        """
        Tira um screenshot da página atual e salva em um diretório de logs.
        """
        # Garante que o diretório de screenshots exista
        screenshots_dir = Path("rpa_logs/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Cria um nome de arquivo único
        screenshot_path = (
            screenshots_dir / f"auth_error_{self.task_id}_{int(time.time())}.png"
        )

        # Tira e salva o screenshot
        self.page.screenshot(path=str(screenshot_path))
        return str(screenshot_path)
