# -*- coding: utf-8 -*-
"""
Módulo de Navegação no Portal (rpa/portal_navigator.py).

Responsabilidade:
1. Navegar entre as telas (menus, grids) do portal ISS.net.
2. Selecionar a empresa correta (Contribuinte) no grid dinâmico após o login.
"""
from playwright.sync_api import Page
from typing import Optional

# CORREÇÃO CRÍTICA DO ERRO: Substituí 'ISSNET_LOGIN_URL' por 'ISSNET_URL'.
# Importamos também o 'URLS' para as navegações diretas e 'NAVIGATION_TIMEOUT'.
from rpa.config_rpa import SELECTORS, DEFAULT_TIMEOUT, NAVIGATION_TIMEOUT, URLS 
from rpa.utils import setup_logger
from rpa.error_handler import NavigationError

logger = setup_logger()

class ISSNavigator:
    def __init__(self, page: Page, task_id: str):
        """
        Inicializa o navegador do portal com a página do Playwright.
        
        :param page: Objeto Page do Playwright.
        :param task_id: ID da tarefa para rastreamento nos logs.
        """
        self.page = page
        self.task_id = task_id

    def select_contribuinte(self, inscricao_municipal: str) -> bool:
        """
        Realiza a seleção do contribuinte (empresa) no grid dinâmico.

        **Design Pattern: Localização Resiliente**
        Como os IDs do grid são dinâmicos, usamos o valor do filtro e a
        combinação de seletores (XPath ou text-based) para garantir que
        o botão "Selecionar" seja encontrado na linha correta.
        
        :param inscricao_municipal: A Inscrição Municipal a ser selecionada.
        :return: True se a seleção for bem-sucedida.
        :raises: NavigationError se a empresa não for encontrada.
        """
        logger.info(f"[{self.task_id}] 🏢 Tentando selecionar o Contribuinte: {inscricao_municipal}")
        
        try:
            # 1. Aguarda a página de seleção de contribuinte carregar totalmente
            input_inscricao_selector = SELECTORS['selecao_empresa']['input_inscricao']
            self.page.wait_for_selector(input_inscricao_selector, state='visible', timeout=NAVIGATION_TIMEOUT)
            
            # 2. Preenche o filtro com a Inscrição Municipal e aciona o filtro
            self.page.fill(input_inscricao_selector, inscricao_municipal)
            btn_localizar_selector = SELECTORS['selecao_empresa']['btn_localizar']
            self.page.click(btn_localizar_selector)

            # 3. Localiza o botão 'Selecionar' na linha filtrada
            # Usando XPath para encontrar o botão 'Selecionar' (com ID dinâmico) dentro da linha que contém a Inscrição.
            # O Playwright também permite combinações de seletores mais limpas:
            # ex: `tr:has-text("12345") >> input[type=image][id*=Selecionar]`
            
            # Optamos por um XPath mais genérico, que busca a linha pelo texto e o botão pela parte de seu ID e tipo.
            btn_selecionar_locator = self.page.locator(
                f"//tr[contains(., '{inscricao_municipal}')] //input[contains(@id, 'imbSelecionar') and contains(@type, 'image')]"
            )

            # Aguarda a visibilidade do botão para confirmar que a filtragem terminou e o elemento foi encontrado.
            btn_selecionar_locator.wait_for(state='visible', timeout=DEFAULT_TIMEOUT)
            btn_selecionar_locator.click()

            # 4. Validação da Navegação
            # Após a seleção, o sistema deve ir para a página principal (ou tela de importação)
            # Usamos a URL de importação como ponto de verificação final para o próximo passo.
            self.page.wait_for_url(URLS['importacao'], timeout=NAVIGATION_TIMEOUT)

            logger.info(f"[{self.task_id}] ✅ Contribuinte {inscricao_municipal} selecionado com sucesso!")
            return True

        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Falha na seleção do Contribuinte {inscricao_municipal}: {str(e)}")
            raise NavigationError(f"Não foi possível selecionar o Contribuinte {inscricao_municipal} no grid. Detalhes: {e}")

    def navigate_to_import_page(self) -> None:
        """
        Navega diretamente para a página de importação de serviços contratados.
        
        **Design Pattern: Navegação Direta (Deep Link)**
        É sempre mais seguro usar URLs diretas quando disponíveis do que simular 
        cliques complexos em menus laterais, reduzindo a chance de falhas.
        """
        logger.info(f"[{self.task_id}] 🧭 Navegando para a tela de Importação de Serviços...")
        try:
            self.page.goto(URLS['importacao'], timeout=NAVIGATION_TIMEOUT)
            # Verifica a visibilidade do input de arquivo para garantir que a página carregou corretamente.
            self.page.wait_for_selector(SELECTORS['importacao']['input_arquivo'], 
                                        state='visible', 
                                        timeout=DEFAULT_TIMEOUT)
            logger.info(f"[{self.task_id}] ✅ Navegação para Importação concluída.")
        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Falha ao navegar para a página de Importação: {str(e)}")
            raise NavigationError(f"Erro ao acessar a URL de Importação: {URLS['importacao']}. Detalhes: {e}")