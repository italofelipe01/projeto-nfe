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

# Dependência opcional para validação real de CPF/CNPJ
try:
    from validate_docbr import CPF, CNPJ
    HAS_VALIDATE_DOCBR = True
except ImportError:
    HAS_VALIDATE_DOCBR = False
    CPF = None  # Correção Pylance: Define CPF como None
    CNPJ = None # Correção Pylance: Define CNPJ como None
    print("AVISO: Biblioteca 'validate_docbr' não instalada. Validação de CPF/CNPJ será básica.")

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

    cleaned = re.sub(r'\D', '', str(value))
    
    if not cleaned and is_required:
         return False, "Campo obrigatório contém apenas caracteres não numéricos."
    
    if not cleaned and not is_required:
        return True, "" # Válido (ex: campo "S/N" em "Número Endereço")

    if max_len and len(cleaned) > max_len:
        return False, f"Deve ter no máximo {max_len} dígitos (recebeu {len(cleaned)})."
    
    return True, ""


def validate_decimal(value, is_required=True, max_len=10, decimal_separator='virgula'):
    """
    /// Validador para campos monetários (Valor Tributável, Valor Documento).
    /// Tenta converter o valor para float e verifica o tamanho.
    /// Usa o 'decimal_separator' para simular a limpeza do transformer.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        if is_required:
            return False, "Campo obrigatório não preenchido."
        return True, ""

    # Tenta converter para float
    try:
        # Simula a limpeza que o transformer fará
        cleaned_str = str(value).replace('R$', '').strip()
        
        # Lógica de limpeza usa o separador decimal
        if decimal_separator == 'virgula':
            # Formato Brasil (1.234,56) -> 1234.56
            cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        else:
            # Formato EUA (1,234.56) -> 1234.56
            cleaned_str = cleaned_str.replace(',', '')
            
        # Remove qualquer outro caractere não numérico que sobrou
        cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

        float_val = float(cleaned_str)
            
        formatted_val = f"{float_val:.2f}"
        
        # Checa o tamanho ANTES do ponto decimal
        if len(formatted_val.split('.')[0]) > (max_len - 3):
            return False, f"Valor excede o máximo de {max_len} caracteres (ex: 1234567.89)."

    except (ValueError, TypeError):
        return False, f"Valor '{value}' não é um decimal válido."
        
    return True, ""

def validate_aliquota(value, decimal_separator='virgula'):
    """
    /// Validador para Alíquota.
    /// Regra: Obrigatório, numérico, entre 0 e 100.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return False, "Alíquota é obrigatória."
        
    try:
        # Lógica de limpeza usa o separador decimal
        cleaned_str = str(value).strip()
        if decimal_separator == 'virgula':
            cleaned_str = cleaned_str.replace(',', '.')
        
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
    /// Se 'validate_docbr' estiver instalada E 'check_dv' for True,
    /// valida o dígito verificador.
    """
    is_valid, err = validate_numeric(value, is_required=True, max_len=14)
    if not is_valid:
        return is_valid, err

    cleaned = re.sub(r'\D', '', str(value))
    
    if len(cleaned) not in (11, 14):
        return False, f"CPF/CNPJ deve ter 11 ou 14 dígitos (recebeu {len(cleaned)})."
    
    # <--- CORREÇÃO: Adicionamos "CPF is not None" e "CNPJ is not None"
    # Isso garante ao Pylance que, se o bloco for executado,
    # CPF e CNPJ são "chamáveis" e não "None".
    if HAS_VALIDATE_DOCBR and check_dv and CPF is not None and CNPJ is not None:
        # Validação completa (dígito verificador)
        if len(cleaned) == 11 and not CPF().validate(cleaned):
            return False, "CPF inválido (dígito verificador não confere)."
        if len(cleaned) == 14 and not CNPJ().validate(cleaned):
            return False, "CNPJ inválido (dígito verificador não confere)."
    
    return True, ""

def validate_date_format(value, is_required=True):
    """
    /// Validador de Data.
    /// Tenta converter a string para um objeto de data.
    /// Aceita formatos flexíveis (dd/mm/aaaa, aaaa-mm-dd, etc.)
    /// desde que o Pandas consiga entender.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        if is_required:
            return False, "Data é obrigatória."
        return True, "" # Válido (opcional e vazio, ex: Data Pagto)

    try:
        # Usa o 'dayfirst=True' para priorizar o formato DD/MM
        pd.to_datetime(str(value), dayfirst=True)
    except (ValueError, TypeError):
        return False, f"Data '{value}' não é uma data válida ou está em formato irreconheível."
        
    return True, ""

def validate_boolean_string(value):
    """
    /// Validador para campos "Sim/Não".
    /// Aceita 1/0, S/N, Sim/Não, True/False.
    /// O campo pode ser opcional (vazio), que será tratado como "0" (Não).
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, "" # Válido (vazio será '0')
        
    val_lower = str(value).strip().lower()
    
    # Lista de todos os valores aceitáveis
    valid_inputs = [
        '1', '0', 's', 'n', 'sim', 'não', 'nao', 
        'true', 'false', 't', 'f', 'verdadeiro', 'falso'
    ]
    
    if val_lower not in valid_inputs:
        return False, f"Valor '{value}' é inválido. Use Sim/Não, 1/0, etc."
        
    return True, ""


def validate_estado(value):
    """
    /// Validador de Estado (UF).
    /// Regra: Opcional, mas se preenchido, deve ter 2 caracteres.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, "" # Opcional
        
    cleaned = _clean_alphanumeric(str(value)) # Limpa (helper local)
    
    if len(cleaned) != 2:
        return False, f"UF '{cleaned}' é inválida. Deve ter 2 caracteres (ex: GO)."
        
    return True, ""

def validate_cep(value):
    """
    /// Validador de CEP.
    /// Regra: Opcional, mas se preenchido, deve ter 8 dígitos.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return True, "" # Opcional
        
    is_valid, err = validate_numeric(value, is_required=False, max_len=8)
    if not is_valid:
        return is_valid, err
        
    cleaned = re.sub(r'\D', '', str(value))
    
    if cleaned and len(cleaned) != 8:
        return False, f"CEP deve ter 8 dígitos (recebeu {len(cleaned)})."
        
    return True, ""

def validate_tributavel_vs_documento(val_tributavel_str, val_documento_str):
    """
    /// Validador de Regra de Negócio.
    /// Regra: Valor Tributável não pode ser maior que o Valor do Documento.
    /// Recebe os valores JÁ FORMATADOS (ex: "1000.50").
    """
    try:
        val_trib = float(val_tributavel_str)
        val_doc = float(val_documento_str)
        
        # Adiciona uma pequena tolerância para erros de ponto flutuante
        if (val_trib - val_doc) > 0.001:
            return False, f"Valor Tributável (R${val_trib}) não pode ser maior que o Valor do Documento (R${val_doc})."
            
    except (ValueError, TypeError):
        return False, "Erro ao comparar valores (Tributável/Documento)."

    return True, ""


# --- NOVOS VALIDADORES (Layout 21 campos) ---

def validate_item_lc(value):
    """
    /// Validador para 'Item LC' (20º campo).
    /// Regra: Opcional, numérico, max 4 dígitos.
    """
    is_valid, err = validate_numeric(value, is_required=False, max_len=4)
    if not is_valid:
        return is_valid, err
    return True, ""

def validate_unidade_economica(value):
    """
    /// Validador para 'Unidade Econômica' (21º campo).
    /// Regra: Opcional, booleano (1/0, S/N, etc.).
    """
    is_valid, err = validate_boolean_string(value)
    if not is_valid:
        return is_valid, err
    return True, ""

# --- Funções Auxiliares (usadas apenas neste arquivo) ---

def _clean_alphanumeric(value):
    """Helper local para limpar texto."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip().replace('\n', ' ').replace('\r', '')