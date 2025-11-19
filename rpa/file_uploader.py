# -*- coding: utf-8 -*-
"""
Módulo de Upload (rpa/file_uploader.py).

Responsabilidade:
1. Manipular o input de arquivo oculto (bypass visual).
2. Gerenciar checkboxes de configuração (Separador decimal, DV).
3. Sincronizar o "Aguarde" do servidor para evitar leituras falsas.
"""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from rpa.config_rpa import SELECTORS, UPLOAD_TIMEOUT
from rpa.utils import setup_logger, save_screenshot

logger = setup_logger()

class ISSUploader:
    def __init__(self, page: Page, task_id: str):
        self.page = page
        self.task_id = task_id

    def upload_file(self, file_path: str):
        """
        Realiza o upload do arquivo TXT validado.
        
        Estratégia:
        Usa set_input_files diretamente no ID oculto, ignorando o botão estilizado.
        Aguarda explicitamente o ciclo de vida do overlay de loading.
        """
        logger.info(f"[{self.task_id}] 📤 Preparando upload do arquivo: {file_path}")

        try:
            sels = SELECTORS['importacao']

            # 1. Configuração de Pré-requisitos
            # O portal pode ter checkboxes que afetam como o TXT é lido (Ponto vs Vírgula).
            # É boa prática garantir o estado desses elementos.
            if self.page.locator(sels['chk_separador']).is_visible():
                # Marca para usar Ponto (.) como separador, conforme padrão do nosso conversor
                self.page.check(sels['chk_separador'])
                logger.debug(f"[{self.task_id}] Checkbox 'Separador Ponto' marcado.")

            # 2. Injeção do Arquivo (Input Hidden)
            # O seletor '#txtUpload' geralmente está com style='display:none' ou opacity:0.
            # O Playwright detecta isso e força o evento de upload sem precisar de clique visual.
            self.page.set_input_files(sels['input_arquivo'], str(file_path))
            logger.debug(f"[{self.task_id}] Arquivo injetado no input hidden.")

            # 3. Disparo do Envio
            save_screenshot(self.page, self.task_id, "pre_click_importar")
            self.page.click(sels['btn_importar'])
            logger.info(f"[{self.task_id}] Botão 'Importar' clicado.")

            # 4. Sincronização de Carregamento (O Passo Mais Crítico)
            loading_sel = sels['loading_overlay']
            
            try:
                # Fase A: Espera o loading APARECER.
                # Timeout curto (5s) pois deve ser quase instantâneo após o clique.
                # Se não aparecer, pode ser que o upload foi rápido demais ou falhou o clique.
                self.page.wait_for_selector(loading_sel, state='visible', timeout=5000)
                logger.debug(f"[{self.task_id}] Overlay de carregamento detectado.")
            except PlaywrightTimeout:
                logger.warning(f"[{self.task_id}] Overlay de loading não apareceu (pode ter sido muito rápido).")

            # Fase B: Espera o loading SUMIR (ficar 'detached').
            # Aqui usamos o UPLOAD_TIMEOUT longo (ex: 120s) definido no config,
            # pois o processamento do servidor governamental pode ser lento.
            self.page.wait_for_selector(loading_sel, state='detached', timeout=UPLOAD_TIMEOUT)
            logger.info(f"[{self.task_id}] Processamento do servidor finalizado.")

            # Snapshot para auditoria visual do resultado
            save_screenshot(self.page, self.task_id, "pos_processamento")

        except Exception as e:
            save_screenshot(self.page, self.task_id, "erro_no_upload")
            logger.error(f"[{self.task_id}] Erro crítico durante upload: {e}")
            raise e