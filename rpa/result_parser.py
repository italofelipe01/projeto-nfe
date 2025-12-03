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
        Prioriza a leitura da Grid de Resultados.
        """
        logger.info(f"[{self.task_id}] 🧐 Iniciando leitura dos resultados...")

        try:
            sels = SELECTORS["importacao"]
            result_data = {"success": False, "message": "", "details": ""}

            # 1. Tenta ler da Grid de Resultados (Prioritário)
            grid_row = self.page.locator(sels.get("grid_status_row", "#dgImportacao tr:nth-child(2)"))

            # Aguarda um pouco para garantir que a grid carregou após o refresh
            try:
                grid_row.wait_for(state="visible", timeout=5000)
                grid_text = grid_row.inner_text().strip()
                logger.info(f"[{self.task_id}] Texto capturado na Grid: {grid_text}")

                # Mapa de Status da Grid
                lower_text = grid_text.lower()

                if "aguardando" in lower_text:
                    result_data["success"] = False
                    result_data["message"] = "Arquivo ainda em processamento (Aguardando)."
                    result_data["details"] = "O sistema da prefeitura está lento. Tente novamente mais tarde."

                elif "erro" in lower_text:
                    result_data["success"] = False
                    result_data["message"] = "Processado com Erros."
                    # Tenta extrair detalhes se possível, ou usa o texto da linha
                    result_data["details"] = grid_text

                elif "sucesso" in lower_text or "êxito" in lower_text:
                    result_data["success"] = True
                    result_data["message"] = "Processado com Sucesso!"
                    result_data["details"] = grid_text

                else:
                    # Status desconhecido
                    result_data["success"] = False
                    result_data["message"] = f"Status desconhecido: {grid_text}"

                return result_data

            except Exception as e_grid:
                logger.warning(f"[{self.task_id}] Não foi possível ler a grid ({e_grid}). Tentando método legado...")

            # 2. Fallback: Método Legado (Mensagem no topo da tela)
            # Aguarda a presença do container de mensagem
            msg_element = self.page.locator(sels["msg_resultado"])
            if msg_element.is_visible():
                full_text = msg_element.inner_text().strip()
                logger.debug(f"[{self.task_id}] Texto bruto capturado (Legado): {full_text}")

                is_success = "sucesso" in full_text.lower() or "êxito" in full_text.lower()
                result_data["success"] = is_success
                result_data["message"] = full_text

                if not is_success:
                    error_label = self.page.locator(sels.get("msg_erro_detalhe", "#lblErro"))
                    if error_label.is_visible():
                        result_data["details"] = error_label.inner_text().strip()

                return result_data

            # Se nada for encontrado
            return {
                "success": False,
                "message": "Não foi possível determinar o resultado do processamento.",
                "details": "Nenhuma mensagem de sucesso ou erro foi encontrada."
            }

        except Exception as e:
            logger.error(f"[{self.task_id}] Erro ao interpretar resultado visual: {e}")

            return {
                "success": False,
                "message": "Erro técnico ao ler a resposta do portal.",
                "details": str(e),
            }
