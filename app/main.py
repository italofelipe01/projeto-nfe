import os
import uuid
import threading
import pandas as pd  # Importação necessária para a função load_configurations
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# --- Importações Internas do Projeto ---

# Importa as configurações (UPLOADS_DIR, DOWNLOADS_DIR, etc.)
from app.config import UPLOADS_DIR, DOWNLOADS_DIR, ALLOWED_EXTENSIONS, PROJECT_ROOT
from app.converter import process_conversion
from flask import jsonify, request
from rpa.bot_controller import run_rpa_process


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

# Dicionário em memória para armazenar o status das conversões.
# Chave: task_id, Valor: dict com status, progresso, etc.
# Conforme 'arquitetura_projeto.pdf'.
conversions = {}


@app.route('/rpa/execute', methods=['POST'])
def execute_rpa():
    data = request.json
    filename = data.get('filename')
    mode = data.get('mode') # 'dev' ou 'prod'
    
    if not filename:
        return jsonify({'success': False, 'message': 'Nome do arquivo não fornecido.'}), 400
        
    # Caminho completo do arquivo (assumindo que está na pasta de downloads/processados)
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    
    is_dev = (mode == 'dev')
    
    # Executa o RPA (Isso bloqueia a thread. Idealmente usar Celery/Redis Queue para produção real, 
    # mas para este escopo, threading ou execução direta serve).
    try:
        result = run_rpa_process(file_path, is_dev_mode=is_dev)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
# --- Carregamento de Configurações ---

def load_configurations():
    """
    # Lê o 'configuracoes.csv' da raiz do projeto UMA VEZ na inicialização.
    # Estes dados são usados para preencher o dropdown no frontend.
    """
    try:
        # Usa o PROJECT_ROOT do config.py para encontrar o CSV na raiz
        csv_path = os.path.join(PROJECT_ROOT, 'configuracoes.csv')
        df = pd.read_csv(csv_path)
        
        # Converte o DataFrame para uma lista de dicionários
        # (formato [{coluna: valor}, {coluna: valor}, ...])
        return df.to_dict('records')
    except FileNotFoundError:
        print("AVISO: 'configuracoes.csv' não encontrado. O dropdown ficará vazio.")
        return []
    except Exception as e:
        print(f"Erro ao ler 'configuracoes.csv': {e}")
        return []

# Carrega as configurações UMA VEZ quando o servidor inicia
app_configurations = load_configurations()


# --- Funções Auxiliares ---

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida (ex: .csv, .xlsx)."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_task_status(task_id, status, progress, message, details, **kwargs):
    """
    # Função 'callback' crucial.
    # É usada pelo 'app/converter.py' (que roda em outro thread)
    # para reportar o progresso da tarefa de volta para este módulo.
    # Ela atualiza o dicionário 'conversions' em memória.
    """
    if task_id in conversions:
        conversions[task_id]['status'] = status
        conversions[task_id]['progress'] = progress
        conversions[task_id]['message'] = message
        conversions[task_id]['details'] = details
        
        # Adiciona quaisquer outros dados (como 'filename', 'total', 'success', etc.)
        conversions[task_id].update(kwargs)
    else:
        print(f"Erro: Tentativa de atualizar Task ID {task_id} que não existe.")

# --- Definição das Rotas (Endpoints) ---

@app.route('/')
def index():
    """
    # Rota principal (GET /).
    # Renderiza o 'index.html' e injeta as configurações
    # (lidas do configuracoes.csv) no template.
    """
    return render_template('index.html', configurations=app_configurations)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    # Rota de upload (POST /upload).
    # Este é o ponto de entrada da conversão.
    # 1. Valida o arquivo recebido.
    # 2. Salva o arquivo temporariamente.
    # 3. Inicia a função 'process_conversion' em um thread separado (para não travar).
    # 4. Retorna imediatamente um 'task_id' para o frontend.
    """
    # 1. Validação da Requisição
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    form_data = request.form.to_dict() # Pega todos os dados do formulário

    original_filename = file.filename

    if not original_filename:
        return jsonify({'error': 'Nome de arquivo vazio ou inválido'}), 400
    
    if not allowed_file(original_filename):
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

    # 2. Geração do Task ID e Salvamento do Arquivo
    task_id = str(uuid.uuid4()) # ID único para a tarefa
    filename = secure_filename(original_filename)
    
    # Adiciona o task_id ao nome do arquivo salvo para garantir que seja único
    saved_filename = f"{task_id}_{filename}"
    file_path = os.path.join(app.config['UPLOADS_DIR'], saved_filename)
    
    file.save(file_path)

    # 3. Inicialização do Status (registra a tarefa no dict)
    conversions[task_id] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Na fila para processamento...',
        'details': ''
    }

    # 4. Início do Processamento em Background
    # (Conforme 'arquitetura_projeto.pdf' "deveria ser assíncrono")
    # Usamos 'threading.Thread' para que a conversão (que pode demorar)
    # não trave o servidor Flask.
    processor_thread = threading.Thread(
        target=process_conversion, # O orquestrador que importamos
        args=(task_id, file_path, form_data, update_task_status) # Argumentos
    )
    processor_thread.start()

    # 5. Retorno Imediato do Task ID
    # O frontend (app.js) usará esse ID para o polling
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    """
    # Rota de status (GET /status/<task_id>).
    # O 'app.js' chama esta rota repetidamente (polling) para
    # verificar o progresso da tarefa no dicionário 'conversions'.
    """
    task_status = conversions.get(task_id, None)
    
    if not task_status:
        return jsonify({'status': 'error', 'message': 'Tarefa não encontrada'}), 404
        
    return jsonify(task_status)

@app.route('/download/<filename>')
def download_file(filename):
    """
    # Rota de download (GET /download/<filename>).
    # O 'app.js' redireciona o usuário para cá quando
    # a conversão é concluída e o botão "Baixar" é clicado.
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
    
    