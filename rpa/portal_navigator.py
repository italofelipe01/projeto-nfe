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

    def select_contribuinte(
        self,
        inscricao_municipal: str,
        cnpj: str,
        mes_competencia: str,
        ano_competencia: str,
    ) -> bool:
        """
        Realiza a seleção do contribuinte (empresa) no grid dinâmico.

        A ordem de execução é estrita:
        1. Define o Ano e Mês de competência.
        2. Aguarda o Postback (recarregamento da página).
        3. Filtra pelo CNPJ e Inscrição Municipal.
        4. Clica no botão 'Selecionar' do grid.

        Args:
            inscricao_municipal (str): A Inscrição Municipal para filtro e seleção.
            cnpj (str): O CNPJ para filtro.
            mes_competencia (str): O mês de competência (e.g., "5" para Maio).
            ano_competencia (str): O ano de competência (e.g., "2023").

        Returns:
            bool: True se a seleção for bem-sucedida.

        Raises:
            NavigationError: Se a empresa não for encontrada ou se ocorrer um erro na navegação.
        """
        logger.info(
            f"[{self.task_id}] 🏢 Iniciando seleção do Contribuinte: {inscricao_municipal} | Competência: {mes_competencia}/{ano_competencia}"
        )
        try:
            # --- Etapa A: Aguardar Carregamento Inicial ---
            logger.debug(
                f"[{self.task_id}] Aguardando a página de seleção de contribuinte carregar."
            )
            # Usamos o seletor do ano como ponto de referência para o carregamento inicial.
            select_ano_selector = SELECTORS["selecao_empresa"]["select_ano"]
            self.page.wait_for_selector(
                select_ano_selector, state="visible", timeout=NAVIGATION_TIMEOUT
            )

            # --- Etapa B: Configurar Competência e Aguardar Postback ---
            logger.debug(
                f"[{self.task_id}] Definindo competência para {mes_competencia}/{ano_competencia}."
            )
            # 1. Seleciona o Ano
            self.page.select_option(select_ano_selector, label=ano_competencia)

            # 2. Seleciona o Mês
            # A dropdown espera um valor numérico sem zero à esquerda (e.g., '5' e não '05').
            mes_valor = str(int(mes_competencia))
            select_mes_selector = SELECTORS["selecao_empresa"]["select_mes"]
            self.page.select_option(select_mes_selector, value=mes_valor)

            # 3. Aguardar Postback do ASP.NET
            # O portal recarrega a página (Postback) após a seleção dos dropdowns.
            # 'networkidle' aguarda até que não haja mais tráfego de rede, garantindo
            # que o recarregamento esteja completo antes de prosseguirmos.
            logger.debug(
                f"[{self.task_id}] Aguardando Postback do servidor após definir competência..."
            )
            self.page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT)

            # --- Etapa C: Filtragem Dupla (Inscrição + CNPJ) ---
            logger.debug(
                f"[{self.task_id}] Aplicando filtro duplo: Inscrição '{inscricao_municipal}' e CNPJ."
            )
            # 1. Preenche a Inscrição Municipal
            input_inscricao_selector = SELECTORS["selecao_empresa"]["input_inscricao"]
            self.page.fill(input_inscricao_selector, inscricao_municipal)

            # 2. Preenche o CNPJ
            input_cnpj_selector = SELECTORS["selecao_empresa"]["input_cnpj"]
            self.page.fill(input_cnpj_selector, cnpj)

            # 3. Clica em Localizar
            btn_localizar_selector = SELECTORS["selecao_empresa"]["btn_localizar"]
            self.page.click(btn_localizar_selector)

            # --- Etapa D: Seleção no Grid ---
            # 1. Aguarda o desaparecimento do overlay de carregamento do grid
            loading_overlay_selector = SELECTORS["selecao_empresa"]["loading_overlay"]
            self.page.wait_for_selector(
                loading_overlay_selector, state="hidden", timeout=DEFAULT_TIMEOUT
            )

            # 2. Localiza e clica no botão 'Selecionar'
            logger.debug(
                f"[{self.task_id}] Procurando o botão 'Selecionar' na linha correspondente."
            )
            btn_selecionar_locator = self.page.locator(
                f"//tr[contains(., '{inscricao_municipal}')] //input[contains(@id, 'imbSelecionar') and contains(@type, 'image')]"
            )
            btn_selecionar_locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
            btn_selecionar_locator.click()

            # 3. Valida a navegação para a próxima página
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
                f"Não foi possível selecionar o Contribuinte {inscricao_municipal}. Verifique se a Inscrição, CNPJ e Competência estão corretos e disponíveis."
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
