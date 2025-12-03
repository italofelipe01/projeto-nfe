# -*- coding: utf-8 -*-
import os
import pandas as pd
import datetime
from app.config import Config


def read_data_file(file_path):
    """
    Lê o arquivo físico (CSV ou XLSX) do disco.
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == ".csv":
            with open(file_path, "r", encoding="utf-8-sig") as f:
                line = f.readline()
                sep = ";" if line.count(";") > line.count(",") else ","

            df = pd.read_csv(file_path, sep=sep, dtype=str, skipinitialspace=True)
        elif file_ext in [".xlsx", ".xls"]:
            import openpyxl

            # Verificação de Múltiplas Abas (Regra de Negócio)
            try:
                wb = openpyxl.load_workbook(file_path, read_only=True)
                if len(wb.sheetnames) > 1:
                    wb.close()
                    raise ValueError(
                        "Arquivos com múltiplas abas não são permitidos. "
                        "Por favor, deixe apenas uma aba contendo os dados."
                    )
                wb.close()
            except Exception as e:
                # Se for o ValueError acima, re-raise. Se for erro de leitura, deixa o pandas tentar ou falhar.
                if "múltiplas abas" in str(e):
                    raise e
                # Caso contrário, continua e deixa o pandas lidar ou loga warning
                print(f"Aviso: Não foi possível verificar abas com openpyxl: {e}")

            df = pd.read_excel(file_path, dtype=str, engine="openpyxl")
        else:
            raise ValueError(f"Extensão não suportada: {file_ext}")

        df.dropna(how="all", inplace=True)
        return df, None

    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path}: {e}")
        return None, f"Erro ao ler arquivo: {e}"


def generate_txt_file(header_line, valid_lines, task_id):
    """
    Escreve o .txt final no diretório 'downloads'.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversao_{task_id[:8]}_{timestamp}.txt"
        file_path = os.path.join(Config.DOWNLOADS_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header_line + "\n")
            for line in valid_lines:
                f.write(line + "\n")

        return filename, None

    except Exception as e:
        print(f"Erro ao salvar arquivo TXT: {e}")
        return None, f"Erro ao salvar arquivo TXT final: {e}"


def generate_error_report(error_details, task_id):
    """
    Escreve um arquivo .txt contendo os erros encontrados.
    """
    try:
        if not error_details:
            return None, None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"erros_{task_id[:8]}_{timestamp}.txt"
        file_path = os.path.join(Config.DOWNLOADS_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("RELATORIO DE ERROS DE PROCESSAMENTO\n")
            f.write(f"Data/Hora: {timestamp}\n")
            f.write("-" * 50 + "\n\n")

            for item in error_details:
                line_num = item["line"]
                messages = item["errors"]
                f.write(f"LINHA {line_num}:\n")
                for msg in messages:
                    f.write(f"  - {msg}\n")
                f.write("\n")

        return filename, None

    except Exception as e:
        print(f"Erro ao salvar arquivo de erros: {e}")
        return None, f"Erro ao salvar arquivo de erros: {e}"
