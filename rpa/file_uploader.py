# -*- coding: utf-8 -*-
"""
Módulo de Upload de Arquivo (rpa/file_uploader.py).

Responsabilidade:
1. Interagir com a página de importação do portal ISS.net.
2. Injetar o arquivo .txt no input de upload.
3. Gerenciar as configurações de importação (checkboxes).
4. Clicar no botão de importação e aguardar a conclusão do processamento.
"""
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

# Módulos de configuração e utilitários
from rpa.config_rpa import SELECTORS, UPLOAD_TIMEOUT
from rpa.error_handler import ProcessingError
from rpa.utils import setup_logger, validate_file_exists

# Configuração do Logger para este módulo
logger = setup_logger("rpa_file_uploader")


class ISSUploader:
    """
    Encapsula a lógica de upload do arquivo de declaração no portal.
    """

    def __init__(self, page: Page, task_id: str):
        """
        Inicializa o uploader.

        Args:
            page (Page): Objeto Page do Playwright.
            task_id (str): ID da tarefa para rastreamento nos logs.
        """
        self.page = page
        self.task_id = task_id

    def upload_file(self, file_path: str) -> None:
        """
        Realiza o upload do arquivo TXT, tratando interações e esperas.

        Args:
            file_path (str): Caminho absoluto do arquivo a ser enviado.

        Raises:
            ProcessingError: Se o arquivo for inválido ou se ocorrer um erro durante o upload.
        """
        logger.info(f"[{self.task_id}] 📤 Iniciando processo de upload do arquivo: {Path(file_path).name}")

        # --- Validação Preliminar do Arquivo ---
        is_valid, error_msg = validate_file_exists(file_path)
        if not is_valid:
            logger.error(f"[{self.task_id}] Validação falhou: {error_msg}")
            raise ProcessingError(f"Arquivo inválido para upload: {error_msg}")

        try:
            sels = SELECTORS["importacao"]

            # 1. Configuração de Opções (Checkbox Separador)
            logger.debug(f"[{self.task_id}] Verificando e marcando o checkbox 'Separador Ponto e Vírgula'.")
            chk_separador_locator = self.page.locator(sels["chk_separador"])
            if chk_separador_locator.is_visible():
                chk_separador_locator.check()
                logger.debug(f"[{self.task_id}] Checkbox 'Separador Ponto e Vírgula' marcado.")

            # 2. Injeção do Arquivo
            logger.debug(f"[{self.task_id}] Injetando o arquivo no input oculto.")
            self.page.set_input_files(sels["input_arquivo"], str(file_path))

            # 3. Disparo do Envio
            logger.info(f"[{self.task_id}] Clicando no botão 'Importar' para iniciar o processamento.")
            self.page.click(sels["btn_importar"])

            # 4. Sincronização de Carregamento (Crítico)
            loading_sel = sels["loading_overlay"]
            logger.debug(f"[{self.task_id}] Aguardando o início do processamento (overlay de loading).")
            try:
                # Espera o overlay de "Aguarde" aparecer.
                self.page.wait_for_selector(loading_sel, state="visible", timeout=5000)
                logger.debug(f"[{self.task_id}] Overlay de carregamento detectado. Aguardando desaparecimento.")
            except PlaywrightTimeout:
                # Se o overlay não aparecer, pode ser que o processo tenha sido instantâneo.
                logger.warning(f"[{self.task_id}] Overlay de loading não foi detectado (pode ter sido muito rápido).")

            # Espera o overlay de "Aguarde" desaparecer, indicando o fim do processamento.
            self.page.wait_for_selector(
                loading_sel, state="detached", timeout=UPLOAD_TIMEOUT
            )
            logger.info(f"[{self.task_id}] ✅ Processamento do arquivo no servidor finalizado com sucesso.")

        except Exception as e:
            logger.error(f"[{self.task_id}] ❌ Erro crítico durante o processo de upload: {str(e)}")
            raise ProcessingError(f"Falha na etapa de upload do arquivo. O portal pode ter apresentado instabilidade.") from e
