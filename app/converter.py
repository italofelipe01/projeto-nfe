import os
import pandas as pd
import datetime
from decimal import Decimal, InvalidOperation

# Importa as funções de limpeza e formatação do 'validators.py'
from app.validators import (
    clean_numeric_string,
    sanitize_and_truncate,
    to_boolean_str,
    format_date_ddmmaaaa,
    format_monetary_value,
    validate_uf
)

# Importa o diretório de destino do 'config.py'
from app.config import DOWNLOADS_DIR

# --- Mapeamento de Colunas ---
# Mapeia nomes de colunas do arquivo do usuário (lista) para o nome interno (chave)
# Baseado no 'workflow_conversao.pdf'
COLUMN_MAPPING = {
    # Campo Interno: [Lista de possíveis nomes no arquivo do usuário]
    'modelo': ['modelo', 'tipo documento'],
    'numero_documento': ['numero nf', 'número nf', 'numero documento', 'número documento'],
    'valor_tributavel': ['base de calculo', 'base de cálculo', 'valor tributavel', 'valor tributável'],
    'valor_documento': ['valor total', 'valor documento'],
    'aliquota': ['aliquota', 'alíquota', 'percentual iss'],
    'data_emissao': ['data emissao', 'data emissão', 'dt. emissao', 'dt. emissão'],
    'data_pagamento': ['data pagamento', 'data pagto', 'dt. pagamento', 'dt. pagto'],
    'cpf_cnpj_prestador': ['cpf/cnpj prestador', 'cpfcnpj prestador', 'cnpj', 'cpf'],
    'razao_social_prestador': ['nome prestador', 'razao social', 'razão social'],
    'inscricao_municipal_prestador': ['inscricao municipal prestador', 'inscrição municipal prestador', 'im prestador', 'im'],
    'imposto_retido': ['iss retido', 'imposto retido'],
    'cep_prestador': ['cep prestador', 'cep'],
    'endereco_prestador': ['endereco prestador', 'endereço prestador', 'logouro'],
    'numero_endereco': ['numero endereco', 'número endereço', 'numero', 'número'],
    'bairro_prestador': ['bairro prestador', 'bairro'],
    'cidade_prestador': ['cidade prestador', 'cidade', 'municipio', 'município'],
    'uf_prestador': ['uf/estado', 'uf', 'estado'],
    'ddd': ['ddd', 'codigo area', 'código área'],
    'tributado_municipio': ['tributado no municipio', 'tributado no município', 'tribut. municipio']
}

def find_column_name(df_columns, internal_name):
    # Função auxiliar para encontrar o nome da coluna no arquivo (case-insensitive)
    """
    Encontra o nome real da coluna no DataFrame com base nos 
    possíveis nomes do COLUMN_MAPPING.
    """
    possible_names = COLUMN_MAPPING.get(internal_name, [])
    for col in df_columns:
        if str(col).strip().lower() in possible_names:
            return col
    return None # Não encontrou

def process_conversion(task_id, file_path, form_data, update_status_callback):
    # Função principal executada pelo 'main.py' em um thread.
    # Recebe o ID da tarefa, o caminho do arquivo, os dados do formulário
    # e a função 'callback' para reportar o progresso.
    """
    Função principal de conversão.
    Chamada pelo 'main.py' em um thread.
    """
    try:
        # --- 1. Reportar Início ---
        update_status_callback(task_id, 'processing', 5, 'Lendo arquivo...', '')

        # --- 2. Ler o Arquivo (CSV ou XLSX) ---
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.csv':
                # Tenta encoding UTF-8, depois Latin-1 (comum no Brasil)
                try:
                    # Correção: Adicionado sep=';' para ler CSV com ponto e vírgula
                    df = pd.read_csv(file_path, sep=';')
                except UnicodeDecodeError:
                    # Correção: Adicionado sep=';' para ler CSV com ponto e vírgula
                    df = pd.read_csv(file_path, encoding='latin-1', sep=';')
            elif file_ext == '.xlsx':
                df = pd.read_excel(file_path, sheet_name=0) # Lê a primeira aba
            else:
                raise ValueError("Formato de arquivo não suportado.")
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo: {str(e)}")

        # === INÍCIO DA CORREÇÃO "nan" ===
        # Substitui todos os 'NaN' (Not a Number) do Pandas por strings vazias.
        # Isso evita que o 'NaN' seja escrito literalmente no arquivo TXT final.
        df = df.fillna("")
        # === FIM DA CORREÇÃO "nan" ===

        if df.empty:
            raise ValueError("O arquivo está vazio ou não pôde ser lido.")

        total_rows = len(df)
        update_status_callback(task_id, 'processing', 10, 'Arquivo lido. Mapeando colunas...', f'0 de {total_rows}')

        # --- 3. Mapear Colunas do DataFrame ---
        # Constrói um dicionário com os nomes de coluna encontrados no arquivo
        df_columns = df.columns
        mapped_cols = {}
        missing_cols = []
        for internal_name in COLUMN_MAPPING.keys():
            col_name = find_column_name(df_columns, internal_name)
            if col_name:
                mapped_cols[internal_name] = col_name
            else:
                missing_cols.append(internal_name)

        # Se colunas obrigatórias faltarem, falha a conversão
        if missing_cols:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_cols)}")

        # --- 4. Gerar Cabeçalho (Conforme 'regras_layout_txt.pdf') ---
        update_status_callback(task_id, 'processing', 15, 'Gerando cabeçalho...', '')
        
        now = datetime.datetime.now()
        data_geracao = now.strftime('%d%m%Y')
        hora_geracao = now.strftime('%H%M%S')
        
        # Coleta os dados do formulário (Etapa 1)
        inscricao_municipal = form_data.get('inscricao_municipal', '')
        mes = form_data.get('mes', '').zfill(2) # Garante 2 dígitos (ex: "01")
        ano = form_data.get('ano', '')
        razao_social_tomador = form_data.get('razao_social', '')
        codigo_servico = form_data.get('codigo_servico', '')
        
        # Monta a lista de campos do cabeçalho na ordem exata do layout
        header_parts = [
            inscricao_municipal,
            mes,
            ano,
            f"{hora_geracao}{data_geracao}{sanitize_and_truncate(razao_social_tomador, 100)}", # Combina 3 campos em 1
            codigo_servico,
            "EXPORTACAO DECLARACAO ELETRONICA-ONLINE-NOTA CONTROL" # Frase obrigatória
        ]
        
        # Validação do cabeçalho (permitindo 'codigo_servico' vazio)
        campos_obrigatorios_cabecalho = [
            inscricao_municipal,
            mes,
            ano,
            razao_social_tomador
        ]
        
        if not all(campos_obrigatorios_cabecalho):
            raise ValueError(f"Dados obrigatórios do formulário (IM, Mês, Ano, Razão Social) estão incompletos.")

        # Une os campos com ';' e adiciona o ';' final obrigatório
        header_line = ";".join(header_parts) + ";\n"

        # --- 5. Iterar, Validar e Transformar Linhas ---
        valid_lines = []
        error_details = []
        processed_count = 0
        success_count = 0
        error_count = 0
        
        # Pega a opção de separador decimal do formulário
        source_decimal_sep = form_data.get('separador_decimal', 'virgula')

        # Usamos enumerate() para obter um contador 'i' (int) garantido.
        for i, (index, row) in enumerate(df.iterrows()):
            
            processed_count += 1
            
            # Usamos nosso contador 'i' (que é 0-based)
            line_number = i + 2 # (i=0) + 1 (linha 1-based) + 1 (pelo cabeçalho)
            
            row_errors = []
            
            # Reporta o progresso ao frontend a cada 20 linhas
            if processed_count % 20 == 0:
                progress = 15 + int((processed_count / total_rows) * 80) # Calcula %
                update_status_callback(task_id, 'processing', progress, 'Validando linhas...', f'Linha {processed_count} de {total_rows}')

            try:
                # --- Início da Validação dos 19 Campos (Conforme 'regras_layout_txt.pdf') ---
                
                # 1. Modelo (Max 2, Numérico)
                modelo = clean_numeric_string(row.get(mapped_cols['modelo']))
                if not modelo: row_errors.append("Modelo é obrigatório.")
                modelo = sanitize_and_truncate(modelo, 2)
                
                # 2. Número Documento (Max 20, Numérico)
                num_doc = clean_numeric_string(row.get(mapped_cols['numero_documento']))
                if not num_doc: row_errors.append("Número do Documento é obrigatório.")
                num_doc = sanitize_and_truncate(num_doc, 20)

                # 3. Valor Tributável (Max 10, Decimal)
                val_tributavel_str = format_monetary_value(row.get(mapped_cols['valor_tributavel']), source_decimal_sep)
                if val_tributavel_str is None:
                    row_errors.append("Valor Tributável inválido.")
                    val_tributavel = Decimal(0) # Padrão para evitar crash
                else:
                    val_tributavel = Decimal(val_tributavel_str)
                    val_tributavel_str = sanitize_and_truncate(val_tributavel_str, 10)

                # 4. Valor Documento (Max 10, Decimal)
                val_doc_str = format_monetary_value(row.get(mapped_cols['valor_documento']), source_decimal_sep)
                if val_doc_str is None:
                    row_errors.append("Valor do Documento inválido.")
                    val_doc = Decimal(0) # Padrão para evitar crash
                else:
                    val_doc = Decimal(val_doc_str)
                    val_doc_str = sanitize_and_truncate(val_doc_str, 10)

                # 5. Alíquota (Max 3, Decimal)
                aliquota_str = format_monetary_value(row.get(mapped_cols['aliquota']), source_decimal_sep)
                if aliquota_str is None: row_errors.append("Alíquota inválida.")
                aliquota_str = sanitize_and_truncate(aliquota_str, 3)

                # 6. Data Emissão (ddmmaaaa)
                data_emissao = format_date_ddmmaaaa(row.get(mapped_cols['data_emissao']))
                if data_emissao is None: row_errors.append("Data de Emissão inválida.")

                # 7. Data Pagamento (ddmmaaaa)
                data_pagamento = format_date_ddmmaaaa(row.get(mapped_cols['data_pagamento']))
                if data_pagamento is None:
                    data_pagamento = "" # Campo opcional, pode ser vazio

                # 8. CPF/CNPJ (Max 14, Numérico)
                cpf_cnpj = clean_numeric_string(row.get(mapped_cols['cpf_cnpj_prestador']))
                if not cpf_cnpj: row_errors.append("CPF/CNPJ do Prestador é obrigatório.")
                cpf_cnpj = sanitize_and_truncate(cpf_cnpj, 14)

                # 9. Razão Social (Max 150, Alfanumérico)
                razao_prestador = sanitize_and_truncate(row.get(mapped_cols['razao_social_prestador']), 150)
                if not razao_prestador: row_errors.append("Razão Social do Prestador é obrigatória.")

                # 10. Inscrição Municipal Prestador (Max 15, Alfanumérico)
                im_prestador = sanitize_and_truncate(row.get(mapped_cols['inscricao_municipal_prestador']), 15)
                
                # 11. Imposto Retido (1, Booleano 0/1)
                imposto_retido = to_boolean_str(row.get(mapped_cols['imposto_retido']))

                # 12. CEP (Max 8, Numérico)
                cep = clean_numeric_string(row.get(mapped_cols['cep_prestador']))
                cep = sanitize_and_truncate(cep, 8)
                
                # 13. Endereço (Max 200, Alfanumérico)
                endereco = sanitize_and_truncate(row.get(mapped_cols['endereco_prestador']), 200)

                # 14. Número (Max 6, Numérico)
                numero_end = clean_numeric_string(row.get(mapped_cols['numero_endereco']))
                numero_end = sanitize_and_truncate(numero_end, 6)

                # 15. Bairro (Max 50, Alfanumérico)
                bairro = sanitize_and_truncate(row.get(mapped_cols['bairro_prestador']), 50)
                
                # 16. Cidade (Max 50, Alfanumérico)
                cidade = sanitize_and_truncate(row.get(mapped_cols['cidade_prestador']), 50)

                # 17. Estado (Max 2, Alfanumérico)
                uf = validate_uf(row.get(mapped_cols['uf_prestador'])) # Valida e formata
                if uf is None: uf = "" # Se inválido, envia vazio

                # 18. Código Área (DDD) (Max 2, Numérico)
                ddd = clean_numeric_string(row.get(mapped_cols['ddd']))
                ddd = sanitize_and_truncate(ddd, 2)
                
                # 19. Tributado no Município (1, Booleano 0/1)
                tributado_mun = to_boolean_str(row.get(mapped_cols['tributado_municipio']))

                # --- Validação de Regras de Negócio (Workflow) ---
                # Regra de erro mencionada no 'regras_layout_txt.pdf'
                if val_tributavel > val_doc:
                    row_errors.append("Valor Tributável não pode ser maior que o Valor do Documento.")

                # --- Fim da Validação ---

                if row_errors:
                    # Se houver erros nesta linha, registra-os e pula para a próxima
                    error_count += 1
                    error_details.append(f"Linha {line_number}: {'; '.join(row_errors)}")
                    continue

                # --- 6. Montar a Linha TXT (Se Válida) ---
                # A ordem dos campos é estritamente a definida no 'regras_layout_txt.pdf'
                final_line_parts = [
                    modelo, num_doc, val_tributavel_str, val_doc_str, aliquota_str,
                    data_emissao, data_pagamento, cpf_cnpj, razao_prestador, im_prestador,
                    imposto_retido, cep, endereco, numero_end, bairro, cidade, uf, ddd,
                    tributado_mun
                ]
                
                # Une os 19 campos com ';' e adiciona o ';' final obrigatório
                valid_lines.append(";".join(final_line_parts) + ";\n")
                success_count += 1

            except Exception as e:
                # Captura erros inesperados durante o processamento da *linha*
                error_count += 1
                error_details.append(f"Linha {line_number}: Erro interno de processamento - {str(e)}")

        # --- 7. Finalizar e Salvar Arquivo ---
        update_status_callback(task_id, 'processing', 95, 'Gerando arquivo TXT final...', '')
        
        if success_count == 0:
            # Se nenhuma linha for válida, falha a conversão
            raise ValueError("Nenhum registro válido foi processado. Verifique os erros.")

        # Monta o nome do arquivo de saída
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        final_filename = f"declaracao_servicos_{mes}{ano}_{timestamp}.txt"
        final_filepath = os.path.join(DOWNLOADS_DIR, final_filename)

        # Escreve o cabeçalho e as linhas válidas no arquivo TXT
        with open(final_filepath, 'w', encoding='utf-8') as f:
            f.write(header_line)
            f.writelines(valid_lines)
            
        # --- 8. Reportar Sucesso ---
        error_summary = "\n".join(error_details)
        
        # Envia o status final 'completed' e os dados de resumo para o frontend
        update_status_callback(
            task_id,
            'completed',
            100,
            'Conversão Concluída!',
            f'{success_count} sucesso(s), {error_count} erro(s).',
            filename=final_filename,
            total_records=total_rows,
            success_records=success_count,
            error_records=error_count,
            error_details=error_summary
        )

    except Exception as e:
        # --- 9. Reportar Erro Crítico ---
        # Captura erros de nível superior (leitura do arquivo, colunas faltando, etc.)
        print(f"[ERRO TASK {task_id}]: {str(e)}")
        # Envia o status 'error' para o frontend
        update_status_callback(
            task_id,
            'error',
            100,
            f"Erro Crítico: {str(e)}",
            ''
        )