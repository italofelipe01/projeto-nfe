import os
import uuid
import threading
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
from app.converter import process_conversion
from rpa.bot_controller import run_rpa_process


bp = Blueprint("main", __name__)
conversions = {}


def load_configurations():
    try:
        csv_path = os.path.join(Config.PROJECT_ROOT, "configuracoes.csv")
        if not os.path.exists(csv_path):
            return []
        df = pd.read_csv(csv_path)
        return df.to_dict("records")
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return []


app_configurations = load_configurations()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def update_task_status(task_id, status, progress, msg, details, **kwargs):
    if task_id in conversions:
        conversions[task_id]["status"] = status
        conversions[task_id]["progress"] = progress
        conversions[task_id]["message"] = msg
        conversions[task_id]["details"] = details
        conversions[task_id].update(kwargs)


@bp.route("/")
def index():
    return render_template("index.html", configurations=app_configurations)


@bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    form_data = request.form.to_dict()
    original_filename = file.filename

    if not original_filename or not allowed_file(original_filename):
        return jsonify({"error": "Arquivo inválido"}), 400

    task_id = str(uuid.uuid4())
    filename = secure_filename(original_filename)
    saved_filename = f"{task_id}_{filename}"

    file_path = os.path.join(current_app.config["UPLOADS_DIR"], saved_filename)
    os.makedirs(current_app.config["UPLOADS_DIR"], exist_ok=True)
    file.save(file_path)

    conversions[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Na fila...",
        "details": "",
    }

    processor_thread = threading.Thread(
        target=process_conversion,
        args=(task_id, file_path, form_data, update_task_status),
    )
    processor_thread.start()

    return jsonify({"task_id": task_id})


@bp.route("/status/<task_id>")
def status(task_id):
    task_status = conversions.get(task_id)
    if not task_status:
        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    return jsonify(task_status)


@bp.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(
        current_app.config["DOWNLOADS_DIR"],
        secure_filename(filename),
        as_attachment=True,
    )


@bp.route("/rpa/execute", methods=["POST"])
def execute_rpa():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON inválido."}), 400

    filename = data.get("filename")
    mode = data.get("mode")
    inscricao_municipal = data.get("inscricao_municipal")

    if not filename:
        return jsonify({"success": False, "message": "Nome do arquivo ausente."}), 400

    if not inscricao_municipal:
        return (
            jsonify({"success": False, "message": "Inscrição Municipal obrigatória."}),
            400,
        )

    file_path = os.path.join(current_app.config["DOWNLOADS_DIR"], filename)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "Arquivo não encontrado."}), 404

    is_dev = mode == "dev"
    rpa_task_id = str(uuid.uuid4())

    try:
        result = run_rpa_process(
            task_id=rpa_task_id,
            file_path=file_path,
            inscricao_municipal=inscricao_municipal,
            is_dev_mode=is_dev,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
