# -*- coding: utf-8 -*-
"""
Módulo de Navegação no Portal (rpa/portal_navigator.py).

Responsabilidade:
1. Navegar entre as telas (menus, grids) do portal ISS.net.
2. Selecionar a empresa correta (Contribuinte) no grid dinâmico após o login.
3. Fornecer feedback de progresso claro durante a navegação.
"""
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

    def select_contribuinte(self, inscricao_municipal: str) -> bool:
        """
        Realiza a seleção do contribuinte (empresa) no grid dinâmico.

        Args:
            inscricao_municipal (str): A Inscrição Municipal a ser selecionada.

        Returns:
            bool: True se a seleção for bem-sucedida.

        Raises:
            NavigationError: Se a empresa não for encontrada ou se ocorrer um erro na navegação.
        """
        logger.info(
            f"[{self.task_id}] 🏢 Iniciando seleção do Contribuinte: {inscricao_municipal}"
        )

        try:
            # 1. Aguarda a página carregar
            logger.debug(
                f"[{self.task_id}] Aguardando o campo de filtro de Inscrição Municipal."
            )
            input_inscricao_selector = SELECTORS["selecao_empresa"]["input_inscricao"]
            self.page.wait_for_selector(
                input_inscricao_selector, state="visible", timeout=NAVIGATION_TIMEOUT
            )

            # 2. Filtra pela Inscrição Municipal
            logger.debug(
                f"[{self.task_id}] Preenchendo filtro com '{inscricao_municipal}' e clicando em Localizar."
            )
            self.page.fill(input_inscricao_selector, inscricao_municipal)
            btn_localizar_selector = SELECTORS["selecao_empresa"]["btn_localizar"]
            self.page.click(btn_localizar_selector)

            # 3. Localiza e clica no botão 'Selecionar'
            logger.debug(
                f"[{self.task_id}] Procurando o botão 'Selecionar' na linha correspondente."
            )
            btn_selecionar_locator = self.page.locator(
                f"//tr[contains(., '{inscricao_municipal}')] //input[contains(@id, 'imbSelecionar') and contains(@type, 'image')]"
            )
            btn_selecionar_locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            btn_selecionar_locator.click()

            # 4. Valida a navegação para a próxima página
            logger.debug(
                f"[{self.task_id}] Aguardando redirecionamento para a página de importação."
            )
            self.page.wait_for_url(URLS["importacao"], timeout=NAVIGATION_TIMEOUT)

            logger.info(
                f"[{self.task_id}] ✅ Contribuinte {inscricao_municipal} selecionado com sucesso!"
            )
            return True

        except Exception as e:
            logger.error(
                f"[{self.task_id}] ❌ Falha ao selecionar o Contribuinte {inscricao_municipal}: {str(e)}"
            )
            raise NavigationError(
                f"Não foi possível selecionar o Contribuinte {inscricao_municipal} no grid. Verifique se a Inscrição está correta e disponível para o usuário."
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
