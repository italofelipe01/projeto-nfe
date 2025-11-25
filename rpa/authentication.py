# -*- coding: utf-8 -*-
"""
Módulo de Autenticação (rpa/authentication.py).

Responsabilidade:
1. Realizar o login no portal ISS.net.
2. Resolver o desafio do Teclado Virtual Dinâmico.
3. Validar se o acesso foi concedido, reportando progresso detalhado.
"""
import time
from datetime import datetime
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from typing import Callable, Optional

# Módulos de configuração e utilitários
from rpa.config_rpa import (
    SELECTORS,
    ISSNET_URL,
    LOGIN_TIMEOUT,
    DEBUG_SCREENSHOTS_DIR,
)
from rpa.error_handler import AuthenticationError
from rpa.utils import setup_logger

# Configuração do Logger para este módulo
logger = setup_logger("rpa_authentication")


class ISSAuthenticator:
    """
    Encapsula toda a lógica de autenticação no portal ISS.net,
    incluindo a resolução do teclado virtual.
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

    def _take_debug_screenshot(self):
        """Salva uma screenshot da tela atual para depuração."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = (
            DEBUG_SCREENSHOTS_DIR / f"login_failed_{self.task_id}_{timestamp}.png"
        )
        try:
            self.page.screenshot(path=screenshot_path)
            logger.info(f"[{self.task_id}] Screenshot de depuração salva em: {screenshot_path}")
        except Exception as e:
            logger.error(
                f"[{self.task_id}] Falha ao salvar screenshot de depuração: {e}"
            )

    def login(
        self,
        user: str,
        password: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Executa o fluxo completo de login, com callbacks de status para feedback em tempo real.

        Args:
            user (str): Usuário (CPF/CNPJ/Inscrição).
            password (str): Senha numérica.
            status_callback (Callable, optional): Função para reportar progresso.

        Returns:
            bool: True se o login for bem-sucedido.

        Raises:
            AuthenticationError: Se houver erro de credencial, bloqueio ou falha no processo.
        """
        logger.info(
            f"[{self.task_id}] 🔐 Iniciando processo de autenticação para o usuário '{user[:4]}...'."
        )
        if status_callback:
            status_callback("Realizando login...")

        try:
            # 1. Navegação Inicial
            logger.debug(
                f"[{self.task_id}] Navegando para a página de login: {ISSNET_URL}"
            )
            if status_callback:
                status_callback("Navegando para o portal...")
            self.page.goto(ISSNET_URL, timeout=LOGIN_TIMEOUT)

            # --- Detecção de Cloudflare ---
            page_title = self.page.title().lower()
            page_content = self.page.content().lower()
            if "challenge" in page_title or "just a moment" in page_content:
                logger.warning(
                    f"[{self.task_id}] Detecado desafio Cloudflare. Aguardando resolução automática..."
                )
                if status_callback:
                    status_callback("Aguardando verificação de segurança...")
                # Aumenta o tempo de espera para o Stealth lidar com o desafio
                self.page.wait_for_timeout(15000)

            # 2. Preenchimento do Usuário
            logger.debug(f"[{self.task_id}] Preenchendo campo de usuário.")
            if status_callback:
                status_callback("Inserindo usuário...")
            user_selector = SELECTORS["login"]["username_input"]
            self.page.wait_for_selector(user_selector, state="visible")
            self.page.fill(user_selector, user)
            time.sleep(0.5)  # Pequena pausa para simular comportamento humano

            # 3. Resolução do Teclado Virtual (Senha)
            if status_callback:
                status_callback("Resolvendo teclado virtual...")
            self._resolver_teclado_virtual(password)

            # 4. Submissão
            logger.debug(f"[{self.task_id}] Clicando no botão de submissão.")
            if status_callback:
                status_callback("Enviando credenciais...")
            btn_submit = SELECTORS["login"]["submit_button"]
            self.page.click(btn_submit)
            time.sleep(1) # Aguarda um momento para a página começar a reagir

            # 5. Validação do Sucesso
            logger.debug(f"[{self.task_id}] Aguardando redirecionamento pós-login...")
            self.page.wait_for_url("**/SelecionarContribuinte.aspx*", timeout=30000)
            logger.info(
                f"[{self.task_id}] ✅ Login para o usuário '{user[:4]}...' realizado com sucesso!"
            )
            return True

        except PlaywrightTimeoutError:
            logger.error(f"[{self.task_id}] Timeout ao aguardar redirecionamento pós-login.")
            self._take_debug_screenshot()

            # Verifica se há uma mensagem de erro explícita.
            error_sel = SELECTORS["login"]["error_message"]
            if self.page.locator(error_sel).is_visible():
                erro_msg = self.page.inner_text(error_sel).strip()
                logger.error(f"[{self.task_id}] Login recusado pelo portal: {erro_msg}")
                raise AuthenticationError(f"Falha no login: {erro_msg}")

            logger.error(
                f"[{self.task_id}] Login falhou sem mensagem clara (possível timeout, CAPTCHA ou bloqueio)."
            )
            raise AuthenticationError(
                "Falha no login (Timeout). O portal pode estar lento ou bloqueando o acesso."
            )

        except Exception as e:
            logger.error(
                f"[{self.task_id}] Erro técnico inesperado durante a autenticação: {str(e)}"
            )
            self._take_debug_screenshot()
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Erro técnico durante o login: {str(e)}") from e

    def _resolver_teclado_virtual(self, password: str):
        """
        Lógica para lidar com o Teclado Virtual, que possui valores dinâmicos.
        """
        keyboard_map = SELECTORS["login"]["virtual_keyboard"]
        logger.debug(
            f"[{self.task_id}] Processando teclado virtual para senha de {len(password)} dígitos."
        )

        for i, digit in enumerate(password):
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
                logger.error(
                    f"[{self.task_id}] Teclado Virtual: Não foi possível encontrar um botão para o dígito '{digit}'."
                )
                raise AuthenticationError(
                    f"Erro no teclado virtual: Dígito '{digit}' não encontrado."
                )

        logger.info(f"[{self.task_id}] Teclado virtual processado com sucesso.")
