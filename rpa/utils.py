# -*- coding: utf-8 -*-
"""
Módulo de Utilitários (rpa/utils.py).

Responsabilidade:
1. Configurar o sistema de logs (File + Console).
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# Diretórios de Log
# Define a raiz do projeto subindo dois níveis a partir deste arquivo
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / 'rpa_logs'
EXECUTION_LOGS_DIR = LOGS_DIR / 'execution_logs'

# Garante que o diretório de logs exista
EXECUTION_LOGS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(name='rpa_logger'):
    """
    Configura um logger que escreve tanto no console quanto em arquivo.
    
    Returns:
        logging.Logger: Instância configurada do logger.
    """
    logger = logging.getLogger(name)
    
    # Evita duplicação de handlers se o logger já estiver configurado
    # Isso previne que a mesma mensagem apareça repetida no terminal
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)

    # Formato do Log: [Data/Hora] [Nível] Mensagem
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. Handler de Arquivo (Salva o histórico completo)
    # O nome do arquivo inclui a data para facilitar a organização diária
    log_filename = f"execution_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(EXECUTION_LOGS_DIR / log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG) # Arquivo registra TUDO (Debug, Info, Erro)

    # 2. Handler de Console (Feedback visual no terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO) # Console mostra apenas Info e Erros (mais limpo)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger