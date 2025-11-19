# -*- coding: utf-8 -*-
"""
Módulo de Autenticação (rpa/authentication.py).

Responsabilidade:
1. Realizar o login no portal ISS.net.
2. Resolver o desafio do Teclado Virtual Dinâmico.
3. Validar se o acesso foi concedido.
"""

import time
from playwright.sync_api import Page
from rpa.config_rpa import SELECTORS, ISSNET_LOGIN_URL, DEFAULT_TIMEOUT
from rpa.utils import setup_logger
from rpa.error_handler import AuthenticationError

logger = setup_logger()

class ISSAuthenticator:
    def __init__(self, page: Page, task_id: str):
        """
        Inicializa o autenticador com a página do navegador controlada pelo Playwright.
        
        :param page: Objeto Page do Playwright (sessão do navegador).
        :param task_id: ID da tarefa para rastreamento nos logs.
        """
        self.page = page
        self.task_id = task_id

    def login(self, user: str, password: str) -> bool:
        """
        Executa o fluxo completo de login.
        
        :param user: Usuário (CPF/CNPJ/Inscrição).
        :param password: Senha numérica.
        :return: True se o login for bem-sucedido.
        :raises: AuthenticationError se houver erro de credencial ou bloqueio.
        """
        logger.info(f"[{self.task_id}] 🔐 Iniciando processo de autenticação...")

        try:
            # 1. Navegação Inicial
            logger.debug(f"[{self.task_id}] Navegando para: {ISSNET_LOGIN_URL}")
            self.page.goto(ISSNET_LOGIN_URL, timeout=DEFAULT_TIMEOUT)

            # 2. Preenchimento do Usuário
            user_selector = SELECTORS['login']['username_input']
            self.page.wait_for_selector(user_selector, state='visible')
            self.page.fill(user_selector, user)

            # 3. Resolução do Teclado Virtual (Senha)
            self._resolver_teclado_virtual(password)

            # 4. Submissão
            btn_submit = SELECTORS['login']['submit_button']
            self.page.click(btn_submit)

            # 5. Validação do Sucesso
            try:
                # Aguarda redirecionamento para uma URL interna logada
                self.page.wait_for_url("**/SelecionarContribuinte.aspx*", timeout=10000)
                logger.info(f"[{self.task_id}] ✅ Login realizado com sucesso!")
                return True
            except:
                # Se não redirecionou, verifica mensagem de erro na tela
                error_sel = SELECTORS['login']['error_message']
                if self.page.locator(error_sel).is_visible():
                    erro_msg = self.page.inner_text(error_sel).strip()
                    logger.error(f"[{self.task_id}] Login recusado pelo portal: {erro_msg}")
                    # Lança exceção específica de negócio (não tenta novamente)
                    raise AuthenticationError(f"Falha no login: {erro_msg}")
                
                logger.error(f"[{self.task_id}] Login falhou sem mensagem de erro clara (possível timeout ou captcha).")
                raise AuthenticationError("Falha desconhecida no login (Timeout ou comportamento inesperado).")

        except Exception as e:
            # Se já for AuthenticationError, apenas repassa
            if isinstance(e, AuthenticationError):
                raise e
            
            # Se for outro erro (técnico), loga e repassa
            logger.error(f"[{self.task_id}] Erro técnico na rotina de login: {str(e)}")
            raise e

    def _resolver_teclado_virtual(self, password: str):
        """
        Lógica para lidar com Teclado Virtual Randômico.
        """
        keyboard_map = SELECTORS['login']['virtual_keyboard']
        logger.debug(f"[{self.task_id}] Processando teclado virtual...")

        for i, digit in enumerate(password):
            clicked = False
            
            # Percorre botões #btn1 a #btn5
            for btn_key, btn_selector in keyboard_map.items():
                if btn_key == 'limpar': continue

                button = self.page.locator(btn_selector)
                if not button.is_visible(): continue

                # Extrai valor "1 ou 5" do botão
                btn_value = button.get_attribute('value') or button.inner_text()
                
                if digit in btn_value:
                    button.click()
                    clicked = True
                    time.sleep(0.3) # Pequeno delay para o JS do site processar o clique
                    break 
            
            if not clicked:
                logger.error(f"[{self.task_id}] Teclado Virtual: Não encontrei botão para o dígito '{digit}'.")
                raise AuthenticationError(f"Erro no teclado virtual: Dígito '{digit}' não encontrado na tela.")