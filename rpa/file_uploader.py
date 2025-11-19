# -*- coding: utf-8 -*-
"""
Módulo de Upload (rpa/file_uploader.py).

Responsabilidade:
1. Manipular o input de arquivo oculto (bypass visual).
2. Gerenciar checkboxes de configuração.
3. Sincronizar o "Aguarde" do servidor.
"""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from rpa.config_rpa import SELECTORS, UPLOAD_TIMEOUT
from rpa.utils import setup_logger

logger = setup_logger()

class ISSUploader:
    def __init__(self, page: Page, task_id: str):
        self.page = page
        self.task_id = task_id

    def upload_file(self, file_path: str):
        """
        Realiza o upload do arquivo TXT validado.
        """
        logger.info(f"[{self.task_id}] 📤 Preparando upload do arquivo: {file_path}")

        try:
            sels = SELECTORS['importacao']

            # 1. Configuração de Pré-requisitos (Checkbox Separador)
            if self.page.locator(sels['chk_separador']).is_visible():
                self.page.check(sels['chk_separador'])
                logger.debug(f"[{self.task_id}] Checkbox 'Separador Ponto' marcado.")

            # 2. Injeção do Arquivo (Input Hidden)
            self.page.set_input_files(sels['input_arquivo'], str(file_path))
            logger.debug(f"[{self.task_id}] Arquivo injetado no input hidden.")

            # 3. Disparo do Envio
            self.page.click(sels['btn_importar'])
            logger.info(f"[{self.task_id}] Botão 'Importar' clicado.")

            # 4. Sincronização de Carregamento (Crítico)
            loading_sel = sels['loading_overlay']
            
            try:
                # Fase A: Espera o loading APARECER
                self.page.wait_for_selector(loading_sel, state='visible', timeout=5000)
                logger.debug(f"[{self.task_id}] Overlay de carregamento detectado.")
            except PlaywrightTimeout:
                logger.warning(f"[{self.task_id}] Overlay de loading não apareceu (pode ter sido muito rápido).")

            # Fase B: Espera o loading SUMIR (Processamento concluído)
            self.page.wait_for_selector(loading_sel, state='detached', timeout=UPLOAD_TIMEOUT)
            logger.info(f"[{self.task_id}] Processamento do servidor finalizado.")

        except Exception as e:
            logger.error(f"[{self.task_id}] Erro crítico durante upload: {e}")
            raise e