# -*- coding: utf-8 -*-
"""
Módulo RPA - Automação do Portal ISS.net

Este pacote contém toda a lógica de automação robótica
para upload de arquivos no portal ISS.net de Goiânia.
"""

__version__ = "1.0.0"
__author__ = "EBM Desenvolvimento"

# Importações principais para facilitar o uso
from rpa.config_rpa import (
    ISSNET_URL,
    RPA_MODE,
    is_development_mode,
    is_production_mode,
    get_credentials_by_inscricao,
)

from rpa.utils import setup_logger, generate_task_id, validate_file_exists

__all__ = [
    "ISSNET_URL",
    "RPA_MODE",
    "is_development_mode",
    "is_production_mode",
    "get_credentials_by_inscricao",
    "setup_logger",
    "generate_task_id",
    "validate_file_exists",
]
