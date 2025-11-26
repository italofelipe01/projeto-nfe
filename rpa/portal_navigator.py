# -*- coding: utf-8 -*-
"""
Módulo de Navegação no Portal (rpa/portal_navigator.py).

Responsabilidade:
1. Navegar entre as telas (menus, grids) do portal ISS.net.
2. Selecionar a empresa correta (Contribuinte) no grid dinâmico após o login.
3. Fornecer feedback de progresso claro durante a navegação.
"""
import time
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

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

    def select_contribuinte(self, inscricao: str, cnpj: str):
        """
        Preenche a Inscrição Municipal e o CNPJ, localiza a empresa e lida com
        o desafio Cloudflare que pode ocorrer após a busca.

        Args:
            inscricao (str): A Inscrição Municipal da empresa.
            cnpj (str): O CNPJ da empresa.

        Raises:
            NavigationError: Se a empresa não for encontrada ou se ocorrer um erro de navegação.
        """
        logger.info(f"[{self.task_id}] 🏢 Iniciando seleção com Inscrição '{inscricao}' e CNPJ '{cnpj}'.")

        try:
            # 1. Aguarda e preenche os campos de filtro
            inscricao_selector = SELECTORS["selecao_empresa"]["input_inscricao"]
            cnpj_selector = SELECTORS["selecao_empresa"]["input_filtro_cnpj"]

            self.page.wait_for_selector(inscricao_selector, state="visible", timeout=15000)
            logger.debug(f"[{self.task_id}] Formulário de seleção visível. Preenchendo dados...")

            # Simula comportamento humano para acionar eventos JS
            self.page.click(inscricao_selector)
            self.page.fill(inscricao_selector, inscricao)

            self.page.click(cnpj_selector)
            self.page.fill(cnpj_selector, cnpj)
            self.page.press(cnpj_selector, "Tab")  # Dispara on-blur

            # 2. Executa a busca
            logger.debug(f"[{self.task_id}] Filtro preenchido. Clicando em 'Localizar'...")
            self.page.click(SELECTORS["selecao_empresa"]["btn_localizar"])
            time.sleep(1) # Pausa para a requisição iniciar

            # 3. Validação de Sucesso com Tratamento de Cloudflare
            logger.debug(f"[{self.task_id}] Validando entrada no painel da empresa...")
            try:
                # A melhor validação é esperar o elemento do filtro desaparecer.
                self.page.wait_for_selector(
                    inscricao_selector, state="hidden", timeout=15000
                )
            except PlaywrightTimeoutError:
                # Se o seletor não desaparecer, verifica se é por causa do Cloudflare
                page_title = self.page.title().lower()
                if "just a moment" in page_title or "challenge" in page_title:
                    logger.warning(
                        f"[{self.task_id}] ⚠️ Desafio Cloudflare detectado após a seleção de empresa. Aguardando resolução..."
                    )
                    # Aumenta o timeout para dar tempo ao Stealth de resolver
                    self.page.wait_for_selector(
                        inscricao_selector, state="hidden", timeout=120000
                    )
                    logger.info(f"[{self.task_id}] Desafio Cloudflare resolvido. Acesso ao painel liberado.")
                else:
                    # Se não for Cloudflare, é um erro de navegação
                    raise NavigationError(
                        f"Timeout ao entrar no painel da empresa para o CNPJ {cnpj}. O portal pode estar lento ou a empresa não foi encontrada."
                    )

            logger.info(f"[{self.task_id}] ✅ Acesso ao painel da empresa com CNPJ {cnpj} bem-sucedido!")

        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Falha crítica na seleção de empresa: {str(e)}")
            # Encapsula a exceção original
            raise NavigationError(
                f"Não foi possível selecionar a empresa com CNPJ {cnpj}. Verifique se os dados estão corretos."
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
