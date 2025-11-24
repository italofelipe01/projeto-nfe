# -*- coding: utf-8 -*-
"""
Módulo de Manipulação de Arquivos (I/O).
"""

import os
import pandas as pd
import datetime

# CORREÇÃO: Importa a Classe Config em vez da variável direta
from app.config import Config

def read_data_file(file_path):
    """
    Lê o arquivo físico (CSV ou XLSX) do disco.
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == '.csv':
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()
                sep = ';' if first_line.count(';') > first_line.count(',') else ','

            df = pd.read_csv(
                file_path,
                sep=sep,
                dtype=str,
                skipinitialspace=True
            )
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(
                file_path,
                dtype=str,
                engine='openpyxl'
            )
        else:
            raise ValueError(f"Extensão de arquivo não suportada: {file_ext}")

        df.dropna(how='all', inplace=True)
        return df, None

    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path}: {e}")
        return None, f"Erro ao ler arquivo: {e}"


def generate_txt_file(header_line, valid_lines, task_id):
    """
    Escreve o .txt final no diretório 'downloads'.
    """
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conversao_{task_id[:8]}_{timestamp}.txt"
        
        # CORREÇÃO: Acesso via Config.DOWNLOADS_DIR
        file_path = os.path.join(Config.DOWNLOADS_DIR, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header_line + '\n')
            for line in valid_lines:
                f.write(line + '\n')
                
        return filename, None

    except Exception as e:
        print(f"Erro ao salvar arquivo TXT: {e}")
        return None, f"Erro ao salvar arquivo TXT final: {e}"