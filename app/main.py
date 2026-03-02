import os
import uuid
import threading
import time
import pandas as pd
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_from_directory,
    current_app,
)
from werkzeug.utils import secure_filename
from app.config import Config
from app.layout_config import REQUIRED_HEADER_FIELDS
from app.converter import process_conversion
from rpa.bot_controller import run_rpa_process
from rpa.utils import setup_logger


bp = Blueprint("main", __name__)
conversions = {}
rpa_tasks = {}
logger = setup_logger("app_main")
conversions_lock = threading.Lock()
rpa_tasks_lock = threading.Lock()

TASK_TTL_SECONDS = int(os.environ.get("TASK_TTL_SECONDS", "3600"))
MAX_TASKS_IN_MEMORY = int(os.environ.get("MAX_TASKS_IN_MEMORY", "2000"))


def load_configurations():
    try:
        csv_path = os.path.join(Config.PROJECT_ROOT, "configuracoes.csv")
        if not os.path.exists(csv_path):
            return []
        # Lê o CSV com separador ponto e vírgula e garante que todos os campos sejam strings
        df = pd.read_csv(csv_path, sep=";", dtype=str)
        records = df.to_dict("records")

        # Formata o CNPJ para exibição
        for record in records:
            cnpj = record.get("cnpj", "")
            if len(cnpj) == 14:
                record["cnpj_formatted"] = (
                    f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
                )
            else:
                record["cnpj_formatted"] = cnpj

        return records
    except Exception as e:
        logger.error(f"Erro ao ler CSV: {e}")
        return []


app_configurations = load_configurations()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def validate_header_fields(form_data):
    missing = []
    for field in REQUIRED_HEADER_FIELDS:
        if not str(form_data.get(field, "")).strip():
            missing.append(field)
    return missing


def sanitize_task_payload(task_payload):
    return {k: v for k, v in task_payload.items() if not k.startswith("_")}


def cleanup_task_store(store, lock):
    now = time.time()
    with lock:
        expired_ids = [
            task_id
            for task_id, payload in store.items()
            if now - payload.get("_updated_at", payload.get("_created_at", now))
            > TASK_TTL_SECONDS
        ]
        for task_id in expired_ids:
            store.pop(task_id, None)

        overflow = len(store) - MAX_TASKS_IN_MEMORY
        if overflow > 0:
            ordered_ids = sorted(
                store.keys(),
                key=lambda task_id: store[task_id].get(
                    "_updated_at", store[task_id].get("_created_at", now)
                ),
            )
            for task_id in ordered_ids[:overflow]:
                store.pop(task_id, None)


def cleanup_all_tasks():
    cleanup_task_store(conversions, conversions_lock)
    cleanup_task_store(rpa_tasks, rpa_tasks_lock)


def resolve_safe_download_path(downloads_dir, requested_filename):
    if not requested_filename:
        return None, "Nome do arquivo ausente."

    requested_filename = str(requested_filename).strip()
    safe_filename = secure_filename(requested_filename)

    if not safe_filename or safe_filename != requested_filename:
        return None, "Nome de arquivo inválido."

    base_dir = os.path.abspath(downloads_dir)
    file_path = os.path.abspath(os.path.join(base_dir, safe_filename))

    if os.path.commonpath([base_dir, file_path]) != base_dir:
        return None, "Caminho de arquivo inválido."

    return file_path, None


def update_task_status(task_id, status, progress, msg, details, **kwargs):
    with conversions_lock:
        if task_id in conversions:
            conversions[task_id]["status"] = status
            conversions[task_id]["progress"] = progress
            conversions[task_id]["message"] = msg
            conversions[task_id]["details"] = details
            conversions[task_id]["_updated_at"] = time.time()
            conversions[task_id].update(kwargs)


@bp.route("/")
def index():
    cleanup_all_tasks()
    return render_template("index.html", configurations=app_configurations)


@bp.route("/upload", methods=["POST"])
def upload_file():
    logger.info("Recebendo requisição de upload.")
    cleanup_all_tasks()
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    form_data = request.form.to_dict()
    original_filename = file.filename

    if not original_filename or not allowed_file(original_filename):
        return jsonify({"error": "Arquivo inválido"}), 400

    missing_header_fields = validate_header_fields(form_data)
    if missing_header_fields:
        return (
            jsonify(
                {
                    "error": "Campos obrigatórios do cabeçalho ausentes.",
                    "missing_fields": missing_header_fields,
                }
            ),
            400,
        )

    task_id = str(uuid.uuid4())
    filename = secure_filename(original_filename)
    saved_filename = f"{task_id}_{filename}"

    file_path = os.path.join(current_app.config["UPLOADS_DIR"], saved_filename)
    os.makedirs(current_app.config["UPLOADS_DIR"], exist_ok=True)
    file.save(file_path)
    logger.info(f"Arquivo salvo em: {file_path}")

    with conversions_lock:
        conversions[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Na fila...",
            "details": "",
            "_created_at": time.time(),
            "_updated_at": time.time(),
        }

    processor_thread = threading.Thread(
        target=process_conversion,
        args=(task_id, file_path, form_data, update_task_status),
    )
    processor_thread.start()
    logger.info(f"Tarefa de conversão {task_id} iniciada em background.")

    return jsonify({"task_id": task_id})


@bp.route("/status/<task_id>")
def status(task_id):
    cleanup_all_tasks()
    with conversions_lock:
        task_status = conversions.get(task_id)
    if not task_status:
        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    return jsonify(sanitize_task_payload(task_status))


@bp.route("/download/<filename>")
def download_file(filename):
    cleanup_all_tasks()
    file_path, error = resolve_safe_download_path(
        current_app.config["DOWNLOADS_DIR"], filename
    )
    if error:
        return jsonify({"error": error}), 400

    if not os.path.exists(file_path):
        return jsonify({"error": "Arquivo não encontrado."}), 404

    return send_from_directory(
        current_app.config["DOWNLOADS_DIR"],
        os.path.basename(file_path),
        as_attachment=True,
    )


def update_rpa_status(task_id, message, success=None, details=None):
    """Callback para atualizar o status do RPA."""
    with rpa_tasks_lock:
        if task_id in rpa_tasks:
            rpa_tasks[task_id]["message"] = message
            rpa_tasks[task_id]["_updated_at"] = time.time()
            if success is not None:
                rpa_tasks[task_id]["success"] = success
            if details:
                rpa_tasks[task_id]["details"] = details


def rpa_worker(task_id, file_path, inscricao, is_dev, mes, ano):
    """Wrapper para rodar o RPA em thread separada."""
    logger.info(f"[{task_id}] Iniciando worker RPA para IM: {inscricao} (Comp: {mes}/{ano})")
    try:
        result = run_rpa_process(
            task_id=task_id,
            file_path=file_path,
            inscricao_municipal=inscricao,
            is_dev_mode=is_dev,
            mes=mes,
            ano=ano,
            status_callback=lambda msg: update_rpa_status(task_id, msg),
        )
        # Atualiza status final baseado no retorno do bot
        update_rpa_status(
            task_id,
            result.get("message", "Concluído"),
            success=result.get("success", False),
            details=result.get("details", ""),
        )
    except Exception as e:
        update_rpa_status(
            task_id,
            f"Erro Técnico: {str(e)}",
            success=False,
            details="Verifique os logs.",
        )


@bp.route("/rpa/status/<task_id>")
def rpa_status(task_id):
    cleanup_all_tasks()
    with rpa_tasks_lock:
        status = rpa_tasks.get(task_id)
    if not status:
        return jsonify({"success": False, "message": "Tarefa RPA não encontrada."}), 404
    return jsonify(sanitize_task_payload(status))


@bp.route("/rpa/execute", methods=["POST"])
def execute_rpa():
    cleanup_all_tasks()
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON inválido."}), 400

    filename = data.get("filename")
    mode = data.get("mode", "dev")
    inscricao_municipal = data.get("inscricao_municipal")
    mes = data.get("mes")
    ano = data.get("ano")

    if not filename:
        return jsonify({"success": False, "message": "Nome do arquivo ausente."}), 400

    if not inscricao_municipal:
        return (
            jsonify({"success": False, "message": "Inscrição Municipal obrigatória."}),
            400,
        )

    file_path, path_error = resolve_safe_download_path(
        current_app.config["DOWNLOADS_DIR"], filename
    )
    if path_error:
        return jsonify({"success": False, "message": path_error}), 400

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "Arquivo não encontrado."}), 404

    is_dev = mode == "dev"
    rpa_task_id = str(uuid.uuid4())

    # Inicializa status
    with rpa_tasks_lock:
        rpa_tasks[rpa_task_id] = {
            "success": None,  # None = Em andamento
            "message": "Inicializando...",
            "details": "",
            "_created_at": time.time(),
            "_updated_at": time.time(),
        }

    # Inicia Thread
    thread = threading.Thread(
        target=rpa_worker, args=(rpa_task_id, file_path, inscricao_municipal, is_dev, mes, ano)
    )
    thread.start()

    return jsonify(
        {"success": True, "task_id": rpa_task_id, "message": "Robô iniciado."}
    )
