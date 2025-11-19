import os
import uuid
import threading
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# --- Importações Internas ---
from app.config import UPLOADS_DIR, DOWNLOADS_DIR, ALLOWED_EXTENSIONS, PROJECT_ROOT
from app.converter import process_conversion
# Importação atualizada do controlador refatorado
from rpa.bot_controller import run_rpa_process

# --- Configuração da Aplicação Flask ---
app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

# Carrega configurações
app.config.from_object('app.config')

# Garante diretórios
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Status em memória (Polling)
conversions = {}

# --- Rotas do RPA (NOVA IMPLEMENTAÇÃO) ---

@app.route('/rpa/execute', methods=['POST'])
def execute_rpa():
    """
    Endpoint para disparar o robô.
    Espera JSON: { 
        "filename": "arquivo_processado.txt", 
        "inscricao_municipal": "12345", 
        "mode": "dev" 
    }
    """
    data = request.json or {}
    
    # 1. Extração e Validação de Dados
    filename = data.get('filename')
    inscricao = data.get('inscricao_municipal')
    mode = data.get('mode', 'production') # Default para prod se não informado
    
    if not filename:
        return jsonify({'success': False, 'message': 'Nome do arquivo não fornecido.'}), 400
    
    if not inscricao:
        return jsonify({'success': False, 'message': 'Inscrição Municipal é obrigatória para o login.'}), 400
        
    # Reconstrói o caminho completo do arquivo (pasta downloads)
    # Nota: O arquivo TXT gerado pelo conversor fica em DOWNLOADS_DIR
    file_path = os.path.join(app.config['DOWNLOADS_DIR'], filename)
    
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': f'Arquivo não encontrado no servidor: {filename}'}), 404
    
    # 2. Preparação do Ambiente RPA
    # Gera um ID único para rastrear essa execução específica nos logs/vídeos
    rpa_task_id = f"rpa_{uuid.uuid4().hex[:8]}"
    is_dev = (mode == 'dev')
    
    print(f"🤖 [API] Iniciando RPA Task {rpa_task_id} para {inscricao} (Mode: {mode})")

    # 3. Execução Síncrona (Bloqueante para simplificar feedback imediato neste MVP)
    # Em produção real, isso deveria ir para uma fila (Celery), mas para este projeto,
    # vamos aguardar o retorno para mostrar o sucesso/erro imediatamente na tela.
    try:
        # Chamada corrigida com a nova assinatura do bot_controller
        result = run_rpa_process(
            task_id=rpa_task_id,
            file_path=file_path,
            inscricao_municipal=str(inscricao), # Garante string
            is_dev_mode=is_dev
        )
        
        # Adiciona o ID da tarefa ao resultado para referência
        result['task_id'] = rpa_task_id
        return jsonify(result)

    except Exception as e:
        print(f"❌ [API] Erro não tratado no RPA: {e}")
        return jsonify({
            'success': False, 
            'message': f"Erro interno no servidor RPA: {str(e)}",
            'task_id': rpa_task_id
        }), 500

# --- Rotas de Conversão (Legado mantido) ---

def load_configurations():
    try:
        csv_path = os.path.join(PROJECT_ROOT, 'configuracoes.csv')
        df = pd.read_csv(csv_path)
        # Converte todos os valores para string para evitar problemas de tipo no JSON
        return df.astype(str).to_dict('records')
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return []

app_configurations = load_configurations()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_task_status(task_id, status, progress, message, details, **kwargs):
    if task_id in conversions:
        conversions[task_id].update({
            'status': status,
            'progress': progress,
            'message': message,
            'details': details,
            **kwargs
        })

@app.route('/')
def index():
    return render_template('index.html', configurations=app_configurations)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    # Pega dados do form (incluindo a inscrição selecionada no dropdown)
    form_data = request.form.to_dict() 

    if not file.filename:
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Extensão não permitida'}), 400

    task_id = str(uuid.uuid4())
    safe_name = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOADS_DIR'], f"{task_id}_{safe_name}")
    
    file.save(save_path)

    conversions[task_id] = {
        'status': 'processing',
        'progress': 0, 
        'message': 'Iniciando...',
        'details': '',
        # Persiste a inscrição escolhida no status da tarefa para o Frontend recuperar depois
        'meta_inscricao': form_data.get('inscricao_municipal') 
    }

    thread = threading.Thread(
        target=process_conversion,
        args=(task_id, save_path, form_data, update_task_status)
    )
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    task = conversions.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Tarefa não encontrada'}), 404
    return jsonify(task)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(
        app.config['DOWNLOADS_DIR'],
        secure_filename(filename),
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)