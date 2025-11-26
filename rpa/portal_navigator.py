# -*- coding: utf-8 -*-
"""
Módulo de Navegação no Portal (rpa/portal_navigator.py).

Responsabilidade:
1. Navegar entre as telas (menus, grids) do portal ISS.net.
2. Selecionar a empresa correta (Contribuinte) no grid dinâmico após o login.
3. Fornecer feedback de progresso claro durante a navegação.
"""
from playwright.sync_api import Page
import time

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
        Filtra e seleciona a empresa (contribuinte) na tela de seleção.

        Raises:
            NavigationError: Se a empresa não for encontrada ou se ocorrer um erro na navegação.
        """
        logger.info(f"[{self.task_id}] 🏢 Selecionando empresa: {cnpj_alvo}")

        try:
            # 1. Limpa e Preenche Filtro
            input_selector = SELECTORS["selecao_empresa"]["input_filtro_cnpj"]
            self.page.wait_for_selector(input_selector)
            self.page.fill(input_selector, "")
            self.page.type(input_selector, cnpj_alvo, delay=100)

            # 2. Clica em Localizar
            logger.debug(f"[{self.task_id}] Filtrando...")
            self.page.click(SELECTORS["selecao_empresa"]["btn_localizar"])

            # 3. Espera Inteligente pelo PostBack
            # O sistema usa __doPostBack, que recarrega partes da página.
            # Esperamos 1.5s fixos para o servidor processar + wait_for_selector do botão
            logger.debug(f"[{self.task_id}] Aguardando PostBack do servidor...")
            time.sleep(1.5)

            btn_selector = SELECTORS["selecao_empresa"]["btn_selecionar_primeira_linha"]

            # Aguarda o botão da primeira linha aparecer
            self.page.wait_for_selector(btn_selector, state="visible", timeout=10000)

            # 4. Clica na Primeira Linha (agora garantida ser a correta)
            logger.info(f"[{self.task_id}] Clicando no botão de seleção...")
            self.page.click(btn_selector)

            # 5. Validação de Saída
            # Aguarda sair da tela de seleção (URL muda ou elemento de filtro some)
            logger.debug(f"[{self.task_id}] Validando redirecionamento após seleção...")
            try:
                self.page.wait_for_selector(
                    SELECTORS["selecao_empresa"]["input_filtro_cnpj"],
                    state="hidden",
                    timeout=5000,
                )
            except Exception:
                pass  # Se der timeout, a validação principal será a URL no controller

            logger.info(f"[{self.task_id}] ✅ Contribuinte selecionado com sucesso!")

        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Falha na seleção de empresa: {str(e)}")
            raise NavigationError(
                f"Falha ao tentar selecionar a empresa com CNPJ {cnpj_alvo}."
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
