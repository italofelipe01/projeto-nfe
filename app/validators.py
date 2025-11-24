# -*- coding: utf-8 -*-
"""
Módulo de Validações.

Este arquivo centraliza todas as funções de validação de dados.
Cada função é responsável por validar UMA ÚNICA regra de negócio
ou formato de campo, retornando (True, "") se válido,
ou (False, "Mensagem de Erro") se inválido.
"""

import pandas as pd
import re
from datetime import datetime  # Adicionado para validação estrita de data

# Dependência opcional para validação real de CPF/CNPJ
try:
    from validate_docbr import CPF, CNPJ

    HAS_VALIDATE_DOCBR = True
except ImportError:
    HAS_VALIDATE_DOCBR = False
    CPF = None
    CNPJ = None
    print(
        "AVISO: Biblioteca 'validate_docbr' não instalada. Validação de CPF/CNPJ será básica."
    )

# --- Validadores Principais ---


def validate_numeric(value, is_required=True, max_len=None):
    """
    /// Validador genérico para campos que devem ser numéricos.
    /// Verifica se é obrigatório, se contém apenas dígitos e se
    /// respeita o tamanho máximo.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        if is_required:
            return False, "Campo obrigatório não preenchido."
        return True, ""  # Válido (opcional e vazio)

    cleaned = re.sub(r"\D", "", str(value))

    if not cleaned and is_required:
        return False, "Campo obrigatório contém apenas caracteres não numéricos."

    if not cleaned and not is_required:
        return True, ""  # Válido (ex: campo "S/N" em "Número Endereço")

    if max_len and len(cleaned) > max_len:
        return False, f"Deve ter no máximo {max_len} dígitos (recebeu {len(cleaned)})."

    return True, ""


def validate_decimal(value, is_required=True, max_len=10, decimal_separator="virgula"):
    """
    /// Validador para campos monetários (Valor Tributável, Valor Documento).
    /// Tenta converter o valor para float e verifica o tamanho.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        if is_required:
            return False, "Campo obrigatório não preenchido."
        return True, ""

    try:
        cleaned_str = str(value).replace("R$", "").strip()

        if decimal_separator == "virgula":
            cleaned_str = cleaned_str.replace(".", "").replace(",", ".")
        else:
            cleaned_str = cleaned_str.replace(",", "")

        cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

        float_val = float(cleaned_str)
        formatted_val = f"{float_val:.2f}"

        if len(formatted_val.split(".")[0]) > (max_len - 3):
            return False, f"Valor excede o máximo de {max_len} caracteres."

    except (ValueError, TypeError):
        return False, f"Valor '{value}' não é um decimal válido."

    return True, ""


def validate_aliquota(value, decimal_separator="virgula"):
    """
    /// Validador para Alíquota.
    /// Regra: Obrigatório, numérico, entre 0 e 100.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return False, "Alíquota é obrigatória."

    try:
        cleaned_str = str(value).strip()
        if decimal_separator == "virgula":
            cleaned_str = cleaned_str.replace(",", ".")

        cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)
        float_val = float(cleaned_str)

        if not (0 <= float_val <= 100):
            return False, f"Alíquota '{float_val}%' fora do intervalo (0-100)."

    except (ValueError, TypeError):
        return False, f"Alíquota '{value}' não é um número válido."

    return True, ""


def validate_cpf_cnpj(value, check_dv=True):
    """
    /// Validador de CPF/CNPJ.
    /// Regra: Obrigatório, 11 (CPF) ou 14 (CNPJ) dígitos.
    """
    is_valid, err = validate_numeric(value, is_required=True, max_len=14)
    if not is_valid:
        return is_valid, err

    cleaned = re.sub(r"\D", "", str(value))

    if len(cleaned) not in (11, 14):
        return False, f"CPF/CNPJ deve ter 11 ou 14 dígitos (recebeu {len(cleaned)})."

    if HAS_VALIDATE_DOCBR and check_dv and CPF is not None and CNPJ is not None:
        if len(cleaned) == 11 and not CPF().validate(cleaned):
            return False, "CPF inválido (dígito verificador não confere)."
        if len(cleaned) == 14 and not CNPJ().validate(cleaned):
            return False, "CNPJ inválido (dígito verificador não confere)."

    return True, ""


def validate_date_format(value, is_required=True):
    """
    /// Validador de Data Estrito.
    /// Verifica se a data existe no calendário (ex: rejeita 30/02).
    /// Aceita formatos DD/MM/AAAA ou AAAA-MM-DD.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        if is_required:
            return False, "Data é obrigatória."
        return True, ""

    val_str = str(value).strip()

    # Lista de formatos aceitos
    # O formato '%d/%m/%Y' garante dia/mês/ano com 4 dígitos
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]

    for fmt in formats:
        try:
            # Se a data não existir (ex: 30/02/2025), strptime lança ValueError
            datetime.strptime(val_str, fmt)
            return True, ""
        except ValueError:
            continue

    return False, f"Data '{value}' inválida. Use DD/MM/AAAA (ex: 25/10/2025)."


def validate_boolean_string(value):
    """
    /// Validador para campos "Sim/Não".
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, ""

    val_lower = str(value).strip().lower()
    valid_inputs = [
        "1",
        "0",
        "s",
        "n",
        "sim",
        "não",
        "nao",
        "true",
        "false",
        "t",
        "f",
        "verdadeiro",
        "falso",
    ]

    if val_lower not in valid_inputs:
        return False, f"Valor '{value}' inválido. Use Sim/Não."

    return True, ""


def validate_estado(value):
    """
    /// Validador de Estado (UF).
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, ""

    cleaned = _clean_alphanumeric(str(value))
    if len(cleaned) != 2:
        return False, f"UF '{cleaned}' inválida (deve ter 2 letras)."

    return True, ""


def validate_cep(value):
    """
    /// Validador de CEP.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, ""

    is_valid, err = validate_numeric(value, is_required=False, max_len=8)
    if not is_valid:
        return is_valid, err

    cleaned = re.sub(r"\D", "", str(value))
    if cleaned and len(cleaned) != 8:
        return False, f"CEP deve ter 8 dígitos (recebeu {len(cleaned)})."

    return True, ""


def validate_tributavel_vs_documento(val_tributavel_str, val_documento_str):
    """
    /// Validador de Regra de Negócio: Valor Tributável <= Valor Documento.
    """
    try:
        val_trib = float(val_tributavel_str)
        val_doc = float(val_documento_str)

        if (val_trib - val_doc) > 0.001:
            return (
                False,
                f"Erro: Valor Tributável (R${val_trib}) > Valor Documento (R${val_doc}).",
            )

    except (ValueError, TypeError):
        return False, "Erro ao comparar valores."

    return True, ""


# --- NOVOS VALIDADORES (Layout 21 campos) ---


def validate_item_lc(value):
    """
    /// Validador para 'Item LC'.
    """
    is_valid, err = validate_numeric(value, is_required=False, max_len=4)
    if not is_valid:
        return is_valid, err
    return True, ""


def validate_unidade_economica(value):
    """
    /// Validador para 'Unidade Econômica'.
    """
    is_valid, err = validate_boolean_string(value)
    if not is_valid:
        return is_valid, err
    return True, ""


def _clean_alphanumeric(value):
    """Helper local para limpar texto."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip().replace("\n", " ").replace("\r", "")
