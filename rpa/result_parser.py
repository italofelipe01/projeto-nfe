# -*- coding: utf-8 -*-
"""
Módulo de Leitura de Resultados (rpa/result_parser.py).

Responsabilidade:
1. Identificar a mensagem de retorno do portal após o upload.
2. Classificar o resultado em Sucesso ou Erro.
3. Estruturar o retorno de dados para o backend.
"""

from playwright.sync_api import Page
from rpa.config_rpa import SELECTORS
from rpa.utils import setup_logger

logger = setup_logger()


class ISSResultParser:
    def __init__(self, page: Page, task_id: str):
        self.page = page
        self.task_id = task_id

    def parse(self) -> dict:
        """
        Analisa a tela final para extrair o status do processamento.
        """
        logger.info(f"[{self.task_id}] 🧐 Iniciando leitura dos resultados...")

        try:
            sels = SELECTORS["importacao"]

            # 1. Aguarda a presença do container de mensagem
            msg_element = self.page.locator(sels["msg_resultado"])
            msg_element.wait_for(state="visible")

            # 2. Extração do Texto
            full_text = msg_element.inner_text().strip()
            logger.debug(f"[{self.task_id}] Texto bruto capturado: {full_text}")

            # 3. Classificação (Regra de Negócio)
            is_success = "sucesso" in full_text.lower() or "êxito" in full_text.lower()

            result_data = {"success": is_success, "message": full_text, "details": ""}

            # 4. Tratamento de Erros Específicos (Log detalhado)
            if not is_success:
                # Tenta capturar label de detalhes técnicos se existir
                error_label = self.page.locator(
                    sels.get("msg_erro_detalhe", "#lblErro")
                )
                if error_label.is_visible():
                    result_data["details"] = error_label.inner_text().strip()

                logger.warning(
                    f"[{self.task_id}] Processamento finalizou com REJEIÇÃO: {result_data['message']} | Detalhes: {result_data['details']}"
                )
            else:
                logger.info(f"[{self.task_id}] Processamento finalizou com SUCESSO.")

            return result_data

        except Exception as e:
            logger.error(f"[{self.task_id}] Erro ao interpretar resultado visual: {e}")

            return {
                "success": False,
                "message": "Erro técnico ao ler a resposta do portal.",
                "details": str(e),
            }
