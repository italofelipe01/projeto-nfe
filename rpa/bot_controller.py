from playwright.sync_api import sync_playwright
from rpa.config_rpa import RPAConfig
from rpa.utils import setup_logger, save_screenshot
import os

logger = setup_logger()

def run_rpa_process(file_path, is_dev_mode=False):
    """
    Executa o fluxo completo de RPA.
    
    Args:
        file_path (str): Caminho absoluto do arquivo .txt a ser enviado.
        is_dev_mode (bool): Se True, abre o navegador visível (headful).
    
    Returns:
        dict: Resultado da operação {'success': bool, 'message': str, 'details': str}
    """
    logger.info(f"Iniciando RPA. Modo Dev: {is_dev_mode}. Arquivo: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error("Arquivo não encontrado para upload.")
        return {'success': False, 'message': "Arquivo TXT não encontrado no servidor."}

    with sync_playwright() as p:
        # Configuração do Browser
        browser = p.chromium.launch(
            headless=not is_dev_mode, # Se dev_mode=True, headless=False
            slow_mo=500 if is_dev_mode else 0 # Adiciona delay em dev para visualização
        )
        context = browser.new_context(record_video_dir="rpa_logs/videos" if is_dev_mode else None)
        page = context.new_page()

        try:
            # --- 1. Login ---
            logger.info("Navegando para página de login...")
            page.goto(RPAConfig.URL_LOGIN)
            
            logger.info("Preenchendo credenciais...")
            page.fill(RPAConfig.SELECTOR_USER, RPAConfig.USER)
            page.fill(RPAConfig.SELECTOR_PASS, RPAConfig.PASSWORD)
            page.click(RPAConfig.SELECTOR_BTN_LOGIN)
            
            # Checkpoint: Verificar se login funcionou
            # Sugestão: Esperar por um elemento que só existe logado (ex: Menu Sair ou Nome da Empresa)
            try:
                page.wait_for_url("**/Default.aspx", timeout=10000) # Exemplo de URL pós login
                logger.info("Login realizado com sucesso.")
            except:
                logger.warning("URL não mudou conforme esperado, verificando erro de login.")
                if page.locator(".erro-login").is_visible(): # Exemplo seletor erro
                    raise Exception("Usuário ou senha inválidos.")

            # --- 2. Navegação até Importação ---
            logger.info("Navegando para menu de importação...")
            # Aqui você deve implementar a sequência de cliques ou goto direto
            # page.click(RPAConfig.SELECTOR_MENU_DECLARACOES)
            # page.click(RPAConfig.SELECTOR_SUBMENU_SERVICOS)
            
            # --- 3. Upload ---
            logger.info("Iniciando upload do arquivo...")
            # Espera o input de arquivo aparecer
            page.wait_for_selector(RPAConfig.SELECTOR_INPUT_FILE)
            
            # Define o arquivo no input
            page.set_input_files(RPAConfig.SELECTOR_INPUT_FILE, file_path)
            
            # Configurações adicionais (checkboxes, selects)
            # page.check(RPAConfig.SELECTOR_CHECK_DIGITO)
            
            # Clica em Enviar/Importar
            page.click(RPAConfig.SELECTOR_BTN_ENVIAR)
            
            # --- 4. Captura de Resultado ---
            logger.info("Aguardando processamento...")
            
            # Espera aparecer sucesso OU erro. Promise.race pode ser usado, 
            # ou espera genérica se o elemento de mensagem for o mesmo.
            page.wait_for_selector(f"{RPAConfig.SELECTOR_MSG_SUCESSO}, {RPAConfig.SELECTOR_MSG_ERRO}")
            
            if page.locator(RPAConfig.SELECTOR_MSG_SUCESSO).is_visible():
                msg = page.inner_text(RPAConfig.SELECTOR_MSG_SUCESSO)
                logger.info(f"Sucesso: {msg}")
                save_screenshot(page, "success")
                return {'success': True, 'message': msg}
            else:
                err = page.inner_text(RPAConfig.SELECTOR_MSG_ERRO)
                logger.error(f"Erro no portal: {err}")
                save_screenshot(page, "portal_error")
                return {'success': False, 'message': "O portal retornou erro.", 'details': err}

        except Exception as e:
            logger.exception("Exceção crítica durante execução do RPA")
            save_screenshot(page, "exception")
            return {'success': False, 'message': f"Erro interno do Robô: {str(e)}"}
            
        finally:
            logger.info("Fechando navegador.")
            context.close()
            browser.close()