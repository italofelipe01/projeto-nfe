# -*- coding: utf-8 -*-
"""
Módulo de Autenticação (rpa/authentication.py).

Responsabilidade:
1. Realizar o login no portal ISS.net.
2. Resolver o desafio do Teclado Virtual Dinâmico.
3. Validar se o acesso foi concedido, reportando progresso detalhado.
"""

import time
from playwright.sync_api import Page
from typing import Callable, Optional

# Módulos de configuração e utilitários
from rpa.config_rpa import SELECTORS, ISSNET_URL, DEFAULT_TIMEOUT
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
        logger.info(f"[{self.task_id}] 🔐 Iniciando processo de autenticação para o usuário '{user[:4]}...'.")
        if status_callback:
            status_callback("Realizando login...")

        try:
            # 1. Navegação Inicial
            logger.debug(f"[{self.task_id}] Navegando para a página de login: {ISSNET_URL}")
            if status_callback:
                status_callback("Navegando para o portal...")
            self.page.goto(ISSNET_URL, timeout=DEFAULT_TIMEOUT)

            # 2. Preenchimento do Usuário
            logger.debug(f"[{self.task_id}] Preenchendo campo de usuário.")
            if status_callback:
                status_callback("Inserindo usuário...")
            user_selector = SELECTORS["login"]["username_input"]
            self.page.wait_for_selector(user_selector, state="visible")
            self.page.fill(user_selector, user)

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

            # 5. Validação do Sucesso
            logger.debug(f"[{self.task_id}] Aguardando redirecionamento pós-login...")
            try:
                self.page.wait_for_url("**/SelecionarContribuinte.aspx*", timeout=10000)
                logger.info(f"[{self.task_id}] ✅ Login para o usuário '{user[:4]}...' realizado com sucesso!")
                return True
            except Exception:
                # Se o redirecionamento falhar, verifica se há uma mensagem de erro explícita.
                error_sel = SELECTORS["login"]["error_message"]
                if self.page.locator(error_sel).is_visible():
                    erro_msg = self.page.inner_text(error_sel).strip()
                    logger.error(f"[{self.task_id}] Login recusado pelo portal: {erro_msg}")
                    raise AuthenticationError(f"Falha no login: {erro_msg}")

                # Se não houver mensagem de erro, pode ser um timeout ou CAPTCHA.
                logger.error(f"[{self.task_id}] Login falhou sem mensagem de erro clara (possível timeout ou CAPTCHA).")
                raise AuthenticationError("Falha desconhecida no login (Timeout ou comportamento inesperado do portal).")

        except Exception as e:
            # Garante que qualquer exceção seja registrada e relançada como AuthenticationError
            # para ser tratada pelo bot_controller.
            if isinstance(e, AuthenticationError):
                raise  # Relança a exceção já tipada

            logger.error(f"[{self.task_id}] Erro técnico inesperado durante a autenticação: {str(e)}")
            raise AuthenticationError(f"Erro técnico durante o login: {str(e)}") from e

    def _resolver_teclado_virtual(self, password: str):
        """
        Lógica para lidar com o Teclado Virtual, que possui valores dinâmicos.
        A automação lê os valores dos botões na tela e os clica na sequência correta.
        """
        keyboard_map = SELECTORS["login"]["virtual_keyboard"]
        logger.debug(f"[{self.task_id}] Processando teclado virtual para senha de {len(password)} dígitos.")

        for i, digit in enumerate(password):
            clicked = False
            # Itera sobre os botões do teclado virtual (ex: 'btn1', 'btn2', ...)
            for btn_key, btn_selector in keyboard_map.items():
                if btn_key == "limpar":
                    continue

                button = self.page.locator(btn_selector)
                if not button.is_visible():
                    continue

                # Extrai o valor do botão (ex: "5 ou 3")
                btn_value = button.get_attribute("value") or button.inner_text()

                # Se o dígito da senha estiver contido no valor do botão, clica nele.
                if digit in btn_value:
                    button.click()
                    time.sleep(0.3)  # Simula um clique humano para evitar detecção
                    clicked = True
                    break

            if not clicked:
                logger.error(f"[{self.task_id}] Teclado Virtual: Não foi possível encontrar um botão para o dígito '{digit}'.")
                raise AuthenticationError(f"Erro no teclado virtual: Dígito '{digit}' não encontrado na tela.")

        logger.info(f"[{self.task_id}] Teclado virtual processado com sucesso.")
