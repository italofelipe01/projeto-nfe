import os
import uuid
import threading
import pandas as pd  # <-- MODIFICAÇÃO: Importar pandas
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# --- Importações Internas do Projeto ---

# Importa as configurações (UPLOADS_DIR, DOWNLOADS_DIR, etc.)
from app.config import UPLOADS_DIR, DOWNLOADS_DIR, ALLOWED_EXTENSIONS, PROJECT_ROOT

# Importa a função de conversão (que criaremos a seguir)
try:
    from app.converter import process_conversion
except ImportError:
    # Se 'converter.py' ainda não foi criado, definimos uma função temporária
    def process_conversion(task_id, file_path, form_data, update_status_callback):
        print(f"AVISO: Função process_conversion real não encontrada. Usando placeholder.")
        import time
        update_status_callback(task_id, 'processing', 10, 'Iniciando placeholder', '')
        time.sleep(1)
        update_status_callback(task_id, 'processing', 50, 'Processando placeholder', 'Linha 10 de 20')
        time.sleep(1)
        update_status_callback(task_id, 'completed', 100, 'Concluído (placeholder)', '', 
                             filename='placeholder.txt', total=20, success=20, errors=0, error_details='')

# --- Configuração da Aplicação Flask ---

# (Correção de 05/Nov): Apontamos explicitamente para as pastas 'templates'
# e 'static' que estão no diretório raiz (um nível acima de 'app').
app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

# Carrega as configurações do arquivo config.py
app.config.from_object('app.config')

# Garante que os diretórios de upload e download existam
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Dicionário simples para armazenar o status das conversões em memória
# (Conforme 'arquitetura_projeto.pdf')
conversions = {}

# --- INÍCIO DA MODIFICAÇÃO: Carregar Configurações ---
def load_configurations():
    """Lê o 'configuracoes.csv' e retorna uma lista de dicionários."""
    try:
        # Usa o PROJECT_ROOT do config.py para encontrar o CSV na raiz
        csv_path = os.path.join(PROJECT_ROOT, 'configuracoes.csv')
        df = pd.read_csv(csv_path)
        
        # Converte o DataFrame para uma lista de dicionários
        # 'records' é o formato [{coluna: valor}, {coluna: valor}, ...]
        return df.to_dict('records')
    except FileNotFoundError:
        print("AVISO: 'configuracoes.csv' não encontrado. O dropdown ficará vazio.")
        return []
    except Exception as e:
        print(f"Erro ao ler 'configuracoes.csv': {e}")
        return []

# Carrega as configurações UMA VEZ quando o servidor inicia
app_configurations = load_configurations()
# --- FIM DA MODIFICAÇÃO ---


# --- Funções Auxiliares ---

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_task_status(task_id, status, progress, message, details, **kwargs):
    # Função 'callback' usada pelo 'converter.py' (em outro thread)
    # para reportar o progresso da tarefa.
    """
    Função 'callback' para atualizar o status da tarefa no dicionário principal.
    Isso permite que a lógica de conversão (em outro thread) reporte o progresso.
    """
    if task_id in conversions:
        conversions[task_id]['status'] = status
        conversions[task_id]['progress'] = progress
        conversions[task_id]['message'] = message
        conversions[task_id]['details'] = details
        
        # Adiciona quaisquer outros dados (como 'filename', 'total_records', etc.)
        conversions[task_id].update(kwargs)
    else:
        print(f"Erro: Tentativa de atualizar Task ID {task_id} que não existe.")

# --- Definição das Rotas (Endpoints) ---

@app.route('/')
def index():
    # Rota principal (GET /). Renderiza o HTML.
    """
    Rota principal (GET /).
    Renderiza o formulário HTML (index.html).
    (Conforme 'arquitetura_projeto.pdf')
    """
    # --- INÍCIO DA MODIFICAÇÃO: Passa as configurações para o template ---
    return render_template('index.html', configurations=app_configurations)
    # --- FIM DA MODIFICAÇÃO ---

@app.route('/upload', methods=['POST'])
def upload_file():
    # Rota de upload (POST /upload).
    # Recebe o arquivo e os dados do formulário e inicia a conversão.
    """
    Rota de upload (POST /upload).
    Recebe o arquivo e os dados do formulário, inicia a conversão 
    em um thread separado e retorna um ID de tarefa.
    (Conforme 'arquitetura_projeto.pdf')
    """
    # 1. Validação da Requisição
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    form_data = request.form.to_dict() # Pega todos os dados do formulário

    # === INÍCIO DA CORREÇÃO PYLANCE ===
    # O tipo de 'file.filename' é 'str | None'.
    # Precisamos checar se é 'None' ou uma string vazia ('') antes de usá-lo.
    original_filename = file.filename

    if not original_filename:
        # Esta checagem 'if not' captura tanto 'None' quanto '""'.
        return jsonify({'error': 'Nome de arquivo vazio ou inválido'}), 400
    
    # A partir daqui, Pylance sabe que 'original_filename' é uma 'str'.
    if not allowed_file(original_filename):
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
    # === FIM DA CORREÇÃO PYLANCE ===

    # 2. Geração do Task ID e Salvamento do Arquivo
    task_id = str(uuid.uuid4()) # Gera um ID único para a tarefa
    
    # === CORREÇÃO PYLANCE ===
    # Usamos a variável 'original_filename' que já foi validada.
    filename = secure_filename(original_filename)
    
    # Adicionamos o task_id ao nome do arquivo salvo para garantir que seja único
    saved_filename = f"{task_id}_{filename}"
    file_path = os.path.join(app.config['UPLOADS_DIR'], saved_filename)
    
    file.save(file_path)

    # 3. Inicialização do Status
    conversions[task_id] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Na fila para processamento...',
        'details': ''
    }

    # 4. Início do Processamento em Background
    # (Conforme 'arquitetura_projeto.pdf' "deveria ser assíncrono")
    # Usamos 'threading.Thread' para que a conversão (que pode demorar)
    # não trave o servidor.
    processor_thread = threading.Thread(
        target=process_conversion,
        args=(task_id, file_path, form_data, update_task_status)
    )
    processor_thread.start()

    # 5. Retorno Imediato do Task ID
    # O frontend (app.js) usará esse ID para o polling
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    # Rota de status (GET /status/<task_id>).
    # O 'app.js' chama esta rota repetidamente (polling) para verificar o progresso.
    """
    Rota de status (GET /status/<task_id>).
    Verifica o progresso da conversão.
    (Conforme 'arquitetura_projeto.pdf')
    """
    task_status = conversions.get(task_id, None)
    
    if not task_status:
        return jsonify({'status': 'error', 'message': 'Tarefa não encontrada'}), 404
        
    return jsonify(task_status)

@app.route('/download/<filename>')
def download_file(filename):
    # Rota de download (GET /download/<filename>).
    # O 'app.js' redireciona o usuário para cá quando ele clica em "Baixar".
    """
    Rota de download (GET /download/<filename>).
    Força o download do arquivo TXT gerado.
    (Conforme 'arquitetura_projeto.pdf')
    """
    # Sanitiza o nome do arquivo para segurança
    safe_filename = secure_filename(filename)
    
    # Busca o arquivo no diretório de downloads (DOWNLOADS_DIR)
    return send_from_directory(
        app.config['DOWNLOADS_DIR'],
        safe_filename,
        as_attachment=True # Força o download em vez de exibir no navegador
    )

# --- Ponto de Entrada (para rodar com 'python app/main.py') ---
if __name__ == '__main__':
    app.run(debug=True)