# -*- coding: utf-8 -*-
"""
Módulo de Manipulação de Arquivos (I/O).

Este arquivo centraliza as funções que leem e escrevem no
sistema de arquivos (disco).
- read_data_file: Lê o CSV/XLSX do usuário.
- generate_txt_file: Escreve o .txt final no diretório 'downloads'.
"""

import os
import pandas as pd
import datetime

# Importa a pasta de destino dos arquivos gerados
from app.config import DOWNLOADS_DIR

def read_data_file(file_path):
    """
    /// ETAPA 1 (Leitura): Lê o arquivo físico (CSV ou XLSX) do disco.
    /// Usa a biblioteca Pandas para carregar os dados em memória (um DataFrame).
    /// Lê todas as colunas como 'str' (texto) para preservar zeros à esquerda
    /// (ex: CEP, Modelo).
    """
    # Identifica a extensão do arquivo
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == '.csv':
            # Detecção automática do separador do CSV (ponto-e-vírgula ou vírgula)
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()
                sep = ';' if first_line.count(';') > first_line.count(',') else ','

            df = pd.read_csv(
                file_path,
                sep=sep,
                dtype=str,  # IMPORTANTE: Lê tudo como texto
                skipinitialspace=True
            )
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(
                file_path,
                dtype=str,  # IMPORTANTE: Lê tudo como texto
                engine='openpyxl'
            )
        else:
            raise ValueError(f"Extensão de arquivo não suportada: {file_ext}")

        # Remove linhas que estão 100% vazias
        df.dropna(how='all', inplace=True)
        return df, None

    except Exception as e:
        print(f"Erro ao ler o arquivo {file_path}: {e}")
        return None, f"Erro ao ler arquivo: {e}. Verifique se o formato é CSV ou XLSX válido."


def generate_txt_file(header_line, valid_lines, task_id):
    """
    /// ETAPA 5 (Escrita do Arquivo): Cria o arquivo .txt final.
    /// Ele escreve o cabeçalho (1ª linha) e depois escreve cada uma
    /// das linhas de dados que foram validadas com sucesso.
    """
    try:
        # Cria um nome de arquivo único para evitar sobreposições
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conversao_{task_id[:8]}_{timestamp}.txt"
        file_path = os.path.join(DOWNLOADS_DIR, filename)

        # Abre o arquivo para escrita (encoding 'utf-8')
        with open(file_path, 'w', encoding='utf-8') as f:
            # 1. Escreve o cabeçalho
            f.write(header_line + '\n')
            
            # 2. Escreve cada linha de dados válida
            for line in valid_lines:
                f.write(line + '\n')
                
        # Retorna o nome do arquivo (ex: "conversao_a9bea57e_20251117_113000.txt")
        # para o 'main.py' poder criar o link de download.
        return filename, None

    except Exception as e:
        print(f"Erro ao salvar arquivo TXT: {e}")
        return None, f"Erro ao salvar arquivo TXT final: {e}"