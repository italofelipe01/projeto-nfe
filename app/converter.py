# -*- coding: utf-8 -*-
"""
Módulo Orquestrador da Conversão.

Coordena a leitura, validação, transformação e geração do arquivo TXT,
chamando os módulos 'file_handler', 'validators' e 'transformers'.
"""

import datetime

# Configurações de layout
from app.layout_config import COLUMN_MAPPING, BODY_FIELDS_ORDER

# Módulos de processamento
from app import file_handler
from app import transformers
from app import validators
from rpa.utils import setup_logger

logger = setup_logger("app_converter")

# --- Funções de Lógica de Negócio ---


def _find_column_mappings(df_columns):
    # ETAPA 2: Mapeia colunas do arquivo (ex: 'Valor Total') para nomes internos
    normalized_df_columns = {col.lower().strip(): col for col in df_columns}
    mapping = {}
    missing_required_cols = []

    # Itera sobre os 21 campos que o layout exige
    for internal_name, possible_names in COLUMN_MAPPING.items():
        found = False
        for possible_name in possible_names:
            if possible_name.lower() in normalized_df_columns:
                original_col_name = normalized_df_columns[possible_name.lower()]
                mapping[internal_name] = original_col_name
                found = True
                break

        if not found:
            missing_required_cols.append(internal_name)

    return mapping, missing_required_cols


def _validate_and_transform_row(row_data, mapping, decimal_separator, valida_dv):
    # ETAPA 3: Processa uma única linha de dados.
    # Delega validações para 'validators' e formatação para 'transformers'.
    transformed_row = {}
    row_errors = []

    # 1. Pega os dados brutos da linha usando o mapeamento
    raw_data = {}
    for internal_name, original_col_name in mapping.items():
        raw_data[internal_name] = row_data.get(original_col_name)

    # 2. Bloco de validação e transformação campo a campo
    try:
        # --- Modelo ---
        val = raw_data.get("modelo")
        is_valid, err = validators.validate_numeric(val, is_required=True, max_len=3)
        if not is_valid:
            row_errors.append(f"Modelo: {err}")
        transformed_row["modelo"] = transformers.clean_numeric_string(val, 3)

        # --- Número Documento ---
        val = raw_data.get("numero_documento")
        is_valid, err = validators.validate_numeric(
            val, is_required=True, max_len=50
        )  # Limite atualizado
        if not is_valid:
            row_errors.append(f"Número Documento: {err}")
        transformed_row["numero_documento"] = transformers.clean_numeric_string(val, 50)

        # --- CPF/CNPJ Prestador ---
        val = raw_data.get("cpf_cnpj_prestador")
        # Passa a flag 'valida_dv' para o validador
        is_valid, err = validators.validate_cpf_cnpj(val, check_dv=valida_dv)
        if not is_valid:
            row_errors.append(f"CPF/CNPJ Prestador: {err}")
        transformed_row["cpf_cnpj_prestador"] = transformers.clean_numeric_string(
            val, 14
        )

        # --- CEP Prestador ---
        val = raw_data.get("cep_prestador")
        is_valid, err = validators.validate_cep(val)
        if not is_valid:
            row_errors.append(f"CEP Prestador: {err}")
        transformed_row["cep_prestador"] = transformers.clean_numeric_string(val, 8)

        # --- DDD ---
        val = raw_data.get("ddd")
        is_valid, err = validators.validate_numeric(val, is_required=False, max_len=2)
        if not is_valid:
            row_errors.append(f"DDD: {err}")
        transformed_row["ddd"] = transformers.clean_numeric_string(val, 2)

        # --- Razão Social Prestador ---
        val = raw_data.get("razao_social_prestador")
        transformed_row["razao_social_prestador"] = transformers.clean_alphanumeric(
            val, 150
        )

        # --- Inscrição Municipal Prestador ---
        val = raw_data.get("inscricao_municipal_prestador")
        transformed_row["inscricao_municipal_prestador"] = (
            transformers.clean_alphanumeric(val, 15)
        )

        # --- Endereço Prestador ---
        val = raw_data.get("endereco_prestador")
        transformed_row["endereco_prestador"] = transformers.clean_alphanumeric(
            val, 200
        )

        # --- Número Endereço ---
        val = raw_data.get("numero_endereco")
        is_valid, err = validators.validate_numeric(val, is_required=False, max_len=6)
        if not is_valid:
            row_errors.append(f"Número Endereço: {err}")
        transformed_row["numero_endereco"] = transformers.clean_numeric_string(val, 6)

        # --- Bairro Prestador ---
        val = raw_data.get("bairro_prestador")
        transformed_row["bairro_prestador"] = transformers.clean_alphanumeric(val, 50)

        # --- Cidade Prestador ---
        val = raw_data.get("cidade_prestador")
        transformed_row["cidade_prestador"] = transformers.clean_alphanumeric(val, 50)

        # --- UF Prestador ---
        val = raw_data.get("uf_prestador")
        is_valid, err = validators.validate_estado(val)
        if not is_valid:
            row_errors.append(f"Estado (UF): {err}")
        transformed_row["uf_prestador"] = transformers.clean_alphanumeric(
            val, 2
        ).upper()

        # --- Data Emissão ---
        val = raw_data.get("data_emissao")
        is_valid, err = validators.validate_date_format(val, is_required=True)
        if not is_valid:
            row_errors.append(f"Data Emissão: {err}")
        transformed_row["data_emissao"] = transformers.transform_date(val)

        # --- Data Pagamento ---
        val = raw_data.get("data_pagamento")
        is_valid, err = validators.validate_date_format(val, is_required=False)
        if not is_valid:
            row_errors.append(f"Data Pagamento: {err}")
        transformed_row["data_pagamento"] = transformers.transform_date(val)

        # --- Imposto Retido ---
        val = raw_data.get("imposto_retido")
        is_valid, err = validators.validate_boolean_string(val)
        if not is_valid:
            row_errors.append(f"Imposto Retido: {err}")
        transformed_row["imposto_retido"] = transformers.transform_boolean(val)

        # --- Tributado Município ---
        val = raw_data.get("tributado_municipio")
        is_valid, err = validators.validate_boolean_string(val)
        if not is_valid:
            row_errors.append(f"Tributado Município: {err}")
        transformed_row["tributado_municipio"] = transformers.transform_boolean(val)

        # --- Valor Tributável ---
        val_trib = raw_data.get("valor_tributavel")
        # Passa o 'decimal_separator' para o validador
        is_valid, err = validators.validate_decimal(
            val_trib, is_required=True, max_len=10, decimal_separator=decimal_separator
        )
        if not is_valid:
            row_errors.append(f"Valor Tributável: {err}")
        transformed_row["valor_tributavel"] = transformers.transform_monetary(
            val_trib, decimal_separator
        )

        # --- Valor Documento ---
        val_doc = raw_data.get("valor_documento")
        # Passa o 'decimal_separator' para o validador
        is_valid, err = validators.validate_decimal(
            val_doc, is_required=True, max_len=10, decimal_separator=decimal_separator
        )
        if not is_valid:
            row_errors.append(f"Valor Documento: {err}")
        transformed_row["valor_documento"] = transformers.transform_monetary(
            val_doc, decimal_separator
        )

        # --- Alíquota ---
        val = raw_data.get("aliquota")
        # Passa o 'decimal_separator' para o validador
        is_valid, err = validators.validate_aliquota(
            val, decimal_separator=decimal_separator
        )
        if not is_valid:
            row_errors.append(f"Alíquota: {err}")
        transformed_row["aliquota"] = transformers.transform_aliquota(
            val, decimal_separator
        )

        # --- Item LC ---
        val = raw_data.get("item_lc")
        is_valid, err = validators.validate_item_lc(val)
        if not is_valid:
            row_errors.append(f"Item LC: {err}")
        transformed_row["item_lc"] = transformers.clean_numeric_string(val, 4)

        # --- Unidade Econômica ---
        val = raw_data.get("unidade_economica")
        is_valid, err = validators.validate_unidade_economica(val)
        if not is_valid:
            row_errors.append(f"Unidade Econômica: {err}")
        transformed_row["unidade_economica"] = transformers.transform_boolean(val)

        # --- Validação de Regra de Negócio ---
        is_valid, err = validators.validate_tributavel_vs_documento(
            transformed_row["valor_tributavel"], transformed_row["valor_documento"]
        )
        if not is_valid:
            row_errors.append(err)

    except Exception as e:
        logger.error(f"Erro inesperado ao transformar linha: {e}")
        row_errors.append(f"Erro interno de processamento: {e}")

    return transformed_row, row_errors


def _generate_header(form_data):
    # ETAPA 4: Cria a linha de cabeçalho do TXT (usa dados do formulário).
    try:
        inscricao = form_data.get("inscricao_municipal", "").strip()
        mes = form_data.get("mes", "").strip().zfill(2)
        ano = form_data.get("ano", "").strip()
        now = datetime.datetime.now()
        timestamp = now.strftime("%H:%M %d/%m/%Y")
        razao_social = form_data.get("razao_social", "").strip()
        campo_4 = f"{timestamp}{razao_social}"
        cod_servico = form_data.get("codigo_servico", "").strip()
        frase_fixa = "EXPORTACAO DECLARACAO ELETRONICA-ONLINE-NOTA CONTROL"

        header_line = ";".join([inscricao, mes, ano, campo_4, cod_servico, frase_fixa])

        return header_line, None

    except Exception as e:
        logger.error(f"Erro ao gerar cabeçalho: {e}")
        return None, f"Erro ao gerar cabeçalho: {e}. Verifique os campos do formulário."


# --- Função Principal (Entry Point) ---


def process_conversion(task_id, file_path, form_data, update_status_callback):
    # Ponto de entrada da conversão (chamado pelo main.py em um Thread).
    logger.info(f"[{task_id}] Iniciando processo de conversão para: {file_path}")

    total_rows = 0
    success_count = 0
    error_count = 0
    error_details = []

    try:
        # --- ETAPA 1: Ler o Arquivo ---
        update_status_callback(task_id, "processing", 10, "Lendo arquivo...", "")
        logger.debug(f"[{task_id}] Lendo arquivo de dados...")

        df, read_error = file_handler.read_data_file(file_path)

        if read_error:
            raise Exception(read_error)

        if df is None:
            raise Exception("Erro desconhecido: O DataFrame não foi carregado.")

        total_rows = len(df)
        if total_rows == 0:
            raise Exception("Arquivo está vazio ou não contém dados.")

        # --- ETAPA 2: Mapear Colunas ---
        update_status_callback(task_id, "processing", 20, "Verificando colunas...", "")
        logger.debug(f"[{task_id}] Verificando mapeamento de colunas...")

        mapping, missing_cols = _find_column_mappings(df.columns)

        if missing_cols:
            missing_str = ", ".join(missing_cols)
            raise Exception(f"Colunas obrigatórias não encontradas: {missing_str}")

        # --- ETAPA 2.5: Verificar Duplicatas (NOVA ETAPA) ---
        update_status_callback(
            task_id, "processing", 25, "Verificando duplicatas...", ""
        )
        logger.debug(f"[{task_id}] Verificando duplicatas...")

        # Define a chave de duplicidade (quais colunas definem uma "nota igual"?)
        # Usamos 'numero_documento' e 'cpf_cnpj_prestador' como chave.
        try:
            col_num_doc = mapping["numero_documento"]
            col_cnpj = mapping["cpf_cnpj_prestador"]
        except KeyError:
            # Isso pode falhar se o usuário mapeou 'numero nf' mas não 'cnpj'
            raise Exception(
                "Não foi possível encontrar colunas de Número Documento ou CPF/CNPJ para checar duplicatas."
            )

        # Remove espaços das colunas chave para garantir comparação correta
        # (ex: " 123 " == "123")
        df[col_num_doc] = df[col_num_doc].astype(str).str.strip()
        df[col_cnpj] = df[col_cnpj].astype(str).str.strip()

        # Encontra TODAS as linhas que são duplicadas (keep=False)
        # O Pandas identifica duplicatas com base nos dados brutos do arquivo.
        duplicated_mask = df.duplicated(subset=[col_num_doc, col_cnpj], keep=False)

        # Guarda os índices (do DataFrame original) que são duplicados
        # Usamos um 'set' para performance (verificação O(1) dentro do loop)
        duplicated_indices = set(df[duplicated_mask].index)
        # --- FIM DA ETAPA 2.5 ---

        # --- ETAPA 3: Processar Linha a Linha ---
        update_status_callback(
            task_id,
            "processing",
            30,
            "Iniciando validação...",
            f"Linha 0 de {total_rows}",
        )
        logger.debug(f"[{task_id}] Iniciando validação de {total_rows} linhas.")

        valid_data_dicts = []

        # Lê as flags do formulário (com os nomes corretos do HTML)
        decimal_separator = form_data.get("separador_decimal", "virgula")
        valida_dv = form_data.get("digito_verificador") == "sim"

        for i, (original_index, row) in enumerate(df.iterrows()):
            line_number = i + 2

            # Chama a validação normal
            transformed_row_dict, row_errors = _validate_and_transform_row(
                row, mapping, decimal_separator, valida_dv
            )

            # --- CORREÇÃO: Adiciona verificação de duplicidade ---
            # Se o índice original desta linha estava na lista de duplicados,
            # adicionamos o erro.
            if original_index in duplicated_indices:
                row_errors.append(
                    "Erro de Duplicidade: Esta nota (Nº Documento + Prestador) está duplicada no arquivo."
                )

            if row_errors:
                error_count += 1
                error_details.append({"line": line_number, "errors": row_errors})
            else:
                success_count += 1
                valid_data_dicts.append(transformed_row_dict)

            if i % 10 == 0 or i == total_rows - 1:
                progress = 30 + int(60 * (i / total_rows))
                update_status_callback(
                    task_id,
                    "processing",
                    progress,
                    "Validando dados...",
                    f"Linha {i + 1} de {total_rows}",
                )

        # --- ETAPA 4: Gerar Cabeçalho ---
        update_status_callback(task_id, "processing", 90, "Gerando cabeçalho...", "")
        logger.debug(f"[{task_id}] Gerando cabeçalho do arquivo...")
        header_line, header_error = _generate_header(form_data)
        if header_error:
            raise Exception(header_error)

        if success_count == 0:
            raise Exception("Nenhum registro válido processado. Verifique os erros.")

        # --- ETAPA 5: Formatar Linhas e Gerar Arquivo TXT ---
        update_status_callback(task_id, "processing", 95, "Montando arquivo TXT...", "")
        logger.debug(f"[{task_id}] Montando arquivo final...")

        final_txt_lines = []
        for row_dict in valid_data_dicts:
            # Usa BODY_FIELDS_ORDER para garantir a ordem exata dos 21 campos
            line_items = [row_dict.get(field, "") for field in BODY_FIELDS_ORDER]
            final_line_str = ";".join(line_items) + ";"
            final_txt_lines.append(final_line_str)

        # Chama 'file_handler' para escrever o arquivo
        filename, write_error = file_handler.generate_txt_file(
            header_line, final_txt_lines, task_id
        )
        if write_error:
            raise Exception(write_error)

        # GERA RELATÓRIO DE ERROS (se houver)
        error_filename = None
        if error_count > 0:
            error_filename, err_gen = file_handler.generate_error_report(
                error_details, task_id
            )
            if err_gen:
                logger.warning(
                    f"[{task_id}] Falha ao gerar relatório de erros: {err_gen}"
                )

        # --- ETAPA 6: Sucesso ---
        logger.info(f"[{task_id}] Conversão concluída com sucesso. Arquivo: {filename}")
        update_status_callback(
            task_id,
            "completed",
            100,
            "Conversão Concluída!",
            "",
            filename=filename,
            error_filename=error_filename,  # Passa o nome do arquivo de erros
            total=total_rows,
            success=success_count,
            errors=error_count,
            error_details=error_details,
            meta_inscricao=form_data.get("inscricao_municipal"),
        )

    except Exception as e:
        # --- Tratamento de Erro Global ---
        logger.exception(f"[{task_id}] Erro fatal na conversão: {e}")
        update_status_callback(
            task_id,
            "error",
            100,
            "Erro na Conversão",
            str(e),
            total=total_rows,
            success=success_count,
            errors=error_count,
            error_details=error_details,
        )
    finally:
        pass
