# -*- coding: utf-8 -*-
"""
Módulo de Utilitários do RPA.

Este arquivo contém funções auxiliares reutilizáveis
para todo o sistema de automação.
"""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from playwright.sync_api import Page, Browser

from rpa.config_rpa import (
    EXECUTION_LOGS_DIR,
    SCREENSHOTS_DIR,
    LOG_LEVEL,
    LOG_TO_FILE,
    SCREENSHOT_ON_ERROR,
    SCREENSHOT_ON_SUCCESS
)

# --- Configuração de Logging ---

def setup_logger(task_id: str) -> logging.Logger:
    """
    Configura um logger específico para uma tarefa RPA.
    
    Args:
        task_id (str): ID único da tarefa (ex: UUID)
        
    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(f'RPA.{task_id}')
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove handlers existentes para evitar duplicação
    logger.handlers.clear()
    
    # Formato detalhado dos logs
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console (sempre ativo)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (se configurado)
    if LOG_TO_FILE:
        log_filename = f"rpa_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_filepath = EXECUTION_LOGS_DIR / log_filename
        
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.debug(f"Log arquivo criado: {log_filepath}")
    
    return logger

# --- Funções de Screenshot ---

def take_screenshot(
    page: Page,
    task_id: str,
    stage: str,
    logger: Optional[logging.Logger] = None
) -> Optional[str]:
    """
    Captura um screenshot da página atual.
    
    Args:
        page (Page): Instância da página do Playwright
        task_id (str): ID da tarefa
        stage (str): Nome da etapa (ex: 'login', 'upload', 'error')
        logger (Logger, optional): Logger para registrar ações
        
    Returns:
        str: Caminho do arquivo de screenshot ou None se falhar
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{task_id}_{stage}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        page.screenshot(path=str(filepath), full_page=True)
        
        if logger:
            logger.info(f"📸 Screenshot capturado: {stage} → {filepath.name}")
        
        return str(filepath)
    
    except Exception as e:
        if logger:
            logger.error(f"❌ Erro ao capturar screenshot: {e}")
        return None

def take_screenshot_on_error(
    page: Page,
    task_id: str,
    error_msg: str,
    logger: Optional[logging.Logger] = None
) -> Optional[str]:
    """
    Captura screenshot em caso de erro (se configurado).
    
    Args:
        page (Page): Instância da página
        task_id (str): ID da tarefa
        error_msg (str): Mensagem de erro
        logger (Logger, optional): Logger
        
    Returns:
        str: Caminho do screenshot ou None
    """
    if not SCREENSHOT_ON_ERROR:
        return None
    
    if logger:
        logger.warning(f"⚠️ Erro detectado: {error_msg}")
    
    return take_screenshot(page, task_id, 'error', logger)

def take_screenshot_on_success(
    page: Page,
    task_id: str,
    logger: Optional[logging.Logger] = None
) -> Optional[str]:
    """
    Captura screenshot em caso de sucesso (se configurado).
    
    Args:
        page (Page): Instância da página
        task_id (str): ID da tarefa
        logger (Logger, optional): Logger
        
    Returns:
        str: Caminho do screenshot ou None
    """
    if not SCREENSHOT_ON_SUCCESS:
        return None
    
    return take_screenshot(page, task_id, 'success', logger)

# --- Funções de Espera Inteligente ---

def safe_wait_for_selector(
    page: Page,
    selector: str,
    timeout: int = 10000,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Aguarda um seletor aparecer na página com tratamento de erro.
    
    Args:
        page (Page): Instância da página
        selector (str): Seletor CSS do elemento
        timeout (int): Timeout em milissegundos
        logger (Logger, optional): Logger
        
    Returns:
        bool: True se elemento foi encontrado, False caso contrário
    """
    try:
        page.wait_for_selector(selector, timeout=timeout)
        if logger:
            logger.debug(f"✅ Elemento encontrado: {selector}")
        return True
    except Exception as e:
        if logger:
            logger.warning(f"⏱️ Timeout aguardando elemento '{selector}': {e}")
        return False

def safe_click(
    page: Page,
    selector: str,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Clica em um elemento de forma segura (aguarda estar visível e clicável).
    
    Args:
        page (Page): Instância da página
        selector (str): Seletor CSS do elemento
        logger (Logger, optional): Logger
        
    Returns:
        bool: True se clicou com sucesso, False caso contrário
    """
    try:
        # Aguarda o elemento estar visível e habilitado
        element = page.wait_for_selector(selector, state='visible', timeout=10000)
        if element:
            element.click()
            if logger:
                logger.debug(f"🖱️ Clicou em: {selector}")
            return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"❌ Erro ao clicar em '{selector}': {e}")
        return False

def safe_fill(
    page: Page,
    selector: str,
    value: str,
    logger: Optional[logging.Logger] = None,
    clear_first: bool = True
) -> bool:
    """
    Preenche um campo de input de forma segura.
    
    Args:
        page (Page): Instância da página
        selector (str): Seletor CSS do campo
        value (str): Valor a ser preenchido
        logger (Logger, optional): Logger
        clear_first (bool): Limpar campo antes de preencher
        
    Returns:
        bool: True se preencheu com sucesso, False caso contrário
    """
    try:
        element = page.wait_for_selector(selector, state='visible', timeout=10000)
        if element:
            if clear_first:
                element.fill('')  # Limpa o campo primeiro
            element.fill(value)
            if logger:
                # Não registra o valor em logs (pode ser senha)
                logger.debug(f"✍️ Preencheu campo: {selector}")
            return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"❌ Erro ao preencher '{selector}': {e}")
        return False

# --- Funções de Retry ---

def retry_on_failure(
    func,
    max_attempts: int = 3,
    delay: int = 5,
    logger: Optional[logging.Logger] = None,
    *args,
    **kwargs
) -> Any:
    """
    Tenta executar uma função várias vezes em caso de falha.
    
    Args:
        func: Função a ser executada
        max_attempts (int): Número máximo de tentativas
        delay (int): Segundos entre tentativas
        logger (Logger, optional): Logger
        *args, **kwargs: Argumentos da função
        
    Returns:
        Any: Resultado da função
        
    Raises:
        Exception: Última exceção capturada se todas as tentativas falharem
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if logger:
                logger.debug(f"🔄 Tentativa {attempt}/{max_attempts}: {func.__name__}")
            
            result = func(*args, **kwargs)
            
            if logger:
                logger.info(f"✅ Sucesso na tentativa {attempt}")
            
            return result
        
        except Exception as e:
            last_exception = e
            if logger:
                logger.warning(f"⚠️ Falha na tentativa {attempt}: {e}")
            
            if attempt < max_attempts:
                if logger:
                    logger.info(f"⏳ Aguardando {delay}s antes da próxima tentativa...")
                time.sleep(delay)
            else:
                if logger:
                    logger.error(f"❌ Todas as {max_attempts} tentativas falharam")
    
    # Se chegou aqui, todas as tentativas falharam
    raise last_exception

# --- Funções de Validação ---

def validate_file_exists(file_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Verifica se um arquivo existe no sistema.
    
    Args:
        file_path (str): Caminho do arquivo
        logger (Logger, optional): Logger
        
    Returns:
        bool: True se arquivo existe, False caso contrário
    """
    path = Path(file_path)
    exists = path.exists() and path.is_file()
    
    if logger:
        if exists:
            logger.debug(f"✅ Arquivo encontrado: {path.name}")
        else:
            logger.error(f"❌ Arquivo não encontrado: {file_path}")
    
    return exists

# --- Funções de Geração de ID ---

def generate_task_id() -> str:
    """
    Gera um ID único para uma tarefa RPA.
    
    Returns:
        str: UUID (primeiros 8 caracteres)
    """
    return str(uuid.uuid4())[:8]

# --- Funções de Limpeza ---

def cleanup_browser(browser: Optional[Browser], logger: Optional[logging.Logger] = None):
    """
    Fecha o navegador de forma segura.
    
    Args:
        browser (Browser, optional): Instância do navegador
        logger (Logger, optional): Logger
    """
    if browser:
        try:
            browser.close()
            if logger:
                logger.info("🔒 Navegador fechado com sucesso")
        except Exception as e:
            if logger:
                logger.error(f"❌ Erro ao fechar navegador: {e}")

# --- Funções de Formatação ---

def format_duration(seconds: float) -> str:
    """
    Formata duração em segundos para formato legível.
    
    Args:
        seconds (float): Duração em segundos
        
    Returns:
        str: Duração formatada (ex: "2m 30s", "45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.0f}s"

def sanitize_log_message(message: str, sensitive_words: list = None) -> str:
    """
    Remove informações sensíveis de mensagens de log.
    
    Args:
        message (str): Mensagem original
        sensitive_words (list, optional): Lista de palavras a serem mascaradas
        
    Returns:
        str: Mensagem sanitizada
    """
    if sensitive_words is None:
        sensitive_words = ['senha', 'password', 'pass', 'token', 'secret']
    
    sanitized = message
    for word in sensitive_words:
        if word.lower() in message.lower():
            # Substitui por asteriscos (mas mantém o contexto)
            sanitized = message.replace(word, '***')
    
    return sanitized