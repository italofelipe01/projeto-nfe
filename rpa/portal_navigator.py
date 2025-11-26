# -*- coding: utf-8 -*-
"""
Módulo de Navegação no Portal (rpa/portal_navigator.py).

Responsabilidade:
1. Navegar entre as telas (menus, grids) do portal ISS.net.
2. Selecionar a empresa correta (Contribuinte) no grid dinâmico após o login.
3. Fornecer feedback de progresso claro durante a navegação.
"""
import time
from playwright.sync_api import Page

# Módulos de configuração e utilitários
from rpa.config_rpa import SELECTORS, DEFAULT_TIMEOUT, NAVIGATION_TIMEOUT, URLS
from rpa.error_handler import NavigationError
from rpa.utils import setup_logger

# Configuração do Logger para este módulo
logger = setup_logger("rpa_portal_navigator")


class ISSNavigator:
    """
    Encapsula a lógica de navegação no portal ISS.net, como a seleção de
    contribuintes e o acesso a páginas específicas.
    """

    def __init__(self, page: Page, task_id: str):
        """
        Inicializa o navegador do portal.

        Args:
            page (Page): Objeto Page do Playwright.
            task_id (str): ID da tarefa para rastreamento nos logs.
        """
        self.page = page
        self.task_id = task_id

    def select_contribuinte(self, cnpj_alvo: str):
        """
        Filtra e seleciona a empresa (contribuinte) de forma robusta e dinâmica.

        Raises:
            NavigationError: Se a empresa não for encontrada ou se ocorrer um erro de navegação.
        """
        logger.info(f"[{self.task_id}] 🏢 Iniciando seleção de empresa para o CNPJ: {cnpj_alvo}")

        try:
            # 1. Filtro Robusto
            input_selector = SELECTORS["selecao_empresa"]["input_filtro_cnpj"]
            self.page.wait_for_selector(input_selector, state="visible", timeout=15000)

            # Ações que simulam comportamento humano para JS
            self.page.click(input_selector)
            self.page.fill(input_selector, "")  # Garante que o campo esteja limpo
            self.page.type(input_selector, cnpj_alvo, delay=100)
            self.page.press(input_selector, "Tab")  # Dispara eventos onblur

            logger.debug(f"[{self.task_id}] Filtro preenchido. Clicando em 'Localizar'...")
            self.page.click(SELECTORS["selecao_empresa"]["btn_localizar"])

            # 2. Tratamento de PostBack ASP.NET
            logger.debug(f"[{self.task_id}] Aguardando PostBack do servidor após filtro...")
            time.sleep(2)  # Pausa para o início do request
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # 3. Seleção Dinâmica de Linha
            # Em vez de um seletor fixo, busca qualquer botão "Selecionar" visível
            grid_selector = SELECTORS["selecao_empresa"]["grid_tabela"]
            select_button_selector = f"{grid_selector} a[id*='imbSelecione']"

            logger.debug(
                f"[{self.task_id}] Procurando por um botão de seleção com o seletor: '{select_button_selector}'"
            )

            select_buttons = self.page.locator(select_button_selector)

            # Valida se algum resultado foi encontrado
            if select_buttons.count() == 0:
                raise NavigationError(f"Nenhuma empresa encontrada para o CNPJ '{cnpj_alvo}' após o filtro.")

            logger.info(f"[{self.task_id}] Empresa encontrada. Clicando no primeiro botão de seleção disponível.")
            select_buttons.first.click()

            # 4. Validação de Sucesso
            logger.debug(
                f"[{self.task_id}] Validando redirecionamento para o painel principal..."
            )
            # A melhor validação é esperar o elemento da tela anterior (filtro) desaparecer.
            self.page.wait_for_selector(
                input_selector, state="hidden", timeout=15000
            )

            logger.info(f"[{self.task_id}] ✅ Contribuinte com CNPJ {cnpj_alvo} selecionado com sucesso!")

        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Falha crítica na seleção de empresa: {str(e)}")
            # Encapsula a exceção original para manter o rastreamento
            raise NavigationError(
                f"Não foi possível selecionar a empresa com CNPJ {cnpj_alvo}. Verifique se o CNPJ está correto e associado ao login."
            ) from e

    def navigate_to_import_page(self) -> None:
        """
        Navega diretamente para a página de importação de serviços contratados.
        """
        logger.info(
            f"[{self.task_id}] 🧭 Navegando para a tela de Importação de Serviços..."
        )
        try:
            self.page.goto(URLS["importacao"], timeout=NAVIGATION_TIMEOUT)
            # Confirma que a página carregou verificando um elemento chave
            self.page.wait_for_selector(
                SELECTORS["importacao"]["input_arquivo"],
                state="visible",
                timeout=DEFAULT_TIMEOUT,
            )
            logger.info(
                f"[{self.task_id}] ✅ Navegação para a página de Importação concluída com sucesso."
            )
        except Exception as e:
            logger.error(
                f"[{self.task_id}] ❌ Falha ao navegar para a página de Importação: {str(e)}"
            )
            raise NavigationError(
                f"Erro ao tentar acessar a URL de Importação: {URLS['importacao']}. O portal pode estar instável."
            ) from e
