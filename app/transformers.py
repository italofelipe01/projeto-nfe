# -*- coding: utf-8 -*-
"""
Módulo de Transformadores de Dados.

Este arquivo centraliza todas as funções de "limpeza" e formatação.
Elas são chamadas DEPOIS que os dados foram validados
(por 'validators.py') e formatam os dados brutos (ex: "R$ 1.000,50")
para o padrão final do TXT (ex: "1000.50").
"""

import pandas as pd
import re


def clean_numeric_string(value, max_len=None):
    """
    /// Limpa e padroniza campos numéricos.
    /// Remove formatação (pontos, traços, barras) e deixa apenas os dígitos.
    /// Ex: "11.222.333/0001-44" -> "11222333000144"
    """
    if pd.isna(value) or value is None:
        return ""

    # Usa RegEx (re.sub) para remover tudo que não for um dígito (\D)
    cleaned = re.sub(r"\D", "", str(value))

    if max_len and len(cleaned) > max_len:
        # Garante a regra de negócio de tamanho máximo (ex: CEP max 8)
        cleaned = cleaned[:max_len]

    return cleaned


def clean_alphanumeric(value, max_len=None):
    """
    /// Limpa campos de texto (alfanuméricos).
    /// Remove espaços desnecessários e quebras de linha (\n, \r)
    /// que poderiam quebrar o layout do arquivo TXT.
    /// Também aplica o limite máximo de caracteres.
    """
    if pd.isna(value) or value is None:
        return ""

    # Converte para string, remove espaços nas pontas e substitui quebras de linha
    cleaned = str(value).strip().replace("\n", " ").replace("\r", "")

    if max_len and len(cleaned) > max_len:
        # Trunca a string para o tamanho máximo permitido (ex: Razão Social max 150)
        cleaned = cleaned[:max_len]

    return cleaned


def transform_monetary(value, decimal_separator, max_len=10):
    """
    /// Normaliza valores monetários.
    /// Converte "R$ 1.234,56" (virgula) ou "1,234.56" (ponto)
    /// para o padrão do TXT: "1234.56" (ponto decimal, 2 casas).

    /// CORREÇÃO: Agora aceita 'virgula' e 'ponto' (em português),
    /// conforme recebido do formulário HTML e usado em validators.py.
    """
    if pd.isna(value) or value is None:
        return "0.00"

    # Remove símbolos comuns (R$) e espaços
    cleaned_str = str(value).replace("R$", "").strip()

    # CORREÇÃO: Padronização para 'virgula' e 'ponto' (português)
    if decimal_separator == "virgula":
        # Formato Brasil (1.234,56)
        # 1. Remove pontos de milhar: "1.234,56" → "1234,56"
        # 2. Substitui vírgula decimal por ponto: "1234,56" → "1234.56"
        cleaned_str = cleaned_str.replace(".", "").replace(",", ".")
    else:  # decimal_separator == 'ponto'
        # Formato EUA (1,234.56)
        # Remove apenas as vírgulas de milhar: "1,234.56" → "1234.56"
        cleaned_str = cleaned_str.replace(",", "")

    # Remove qualquer outro caractere não numérico que sobrou (ex: espaços, letras)
    cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

    try:
        # Converte para float e formata com 2 casas decimais (ex: "500.00")
        float_val = float(cleaned_str)
        formatted_val = f"{float_val:.2f}"
    except (ValueError, TypeError):
        # Se a conversão falhar (ex: string vazia após limpeza), retorna padrão
        return "0.00"

    return formatted_val


def transform_aliquota(value, decimal_separator, max_len=3):
    """
    /// Normaliza a alíquota (ex: "5" ou "2,5").
    /// Padroniza para "X.X" (ex: "5.0"), conforme 'modelo.txt'.

    /// CORREÇÃO: Agora aceita 'virgula' e 'ponto' (em português).
    """
    if pd.isna(value) or value is None:
        return "0.0"

    cleaned_str = str(value).strip()

    # CORREÇÃO: Padronização para 'virgula' e 'ponto' (português)
    if decimal_separator == "virgula":
        # Substitui vírgula por ponto para normalizar
        cleaned_str = cleaned_str.replace(",", ".")

    # Remove caracteres não numéricos (exceto ponto decimal)
    cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

    try:
        float_val = float(cleaned_str)
        # Formata com UMA casa decimal
        formatted_val = f"{float_val:.1f}"
    except (ValueError, TypeError):
        return "0.0"

    # Lógica para respeitar os 3 chars (ex: 10.0 tem 4)
    if len(formatted_val) > max_len and float_val < 10:
        return formatted_val[:max_len]  # "5.0"
    elif float_val >= 10:
        # Se for "10.0" ou "100.0", retorna só o inteiro "10" ou "100"
        return str(int(float_val))

    return formatted_val


def transform_date(value):
    """
    /// Normaliza datas.
    /// Converte "25/10/2025" ou "2025-10-25" para "ddmmaaaa" ("25102025").
    /// Assume que 'validate_date_format' já confirmou que é uma data válida.
    """
    if pd.isna(value) or value is None:
        return ""

    try:
        # pd.to_datetime é flexível para "adivinhar" o formato
        date_obj = pd.to_datetime(value, dayfirst=True)
        # .strftime formata a data para o padrão 'ddmmaaaa'
        return date_obj.strftime("%d%m%Y")
    except (ValueError, TypeError):
        return ""


def transform_boolean(value):
    """
    /// Normaliza campos booleanos (Sim/Não).
    /// Converte "Sim", "S", "1", "True" para "1" (Sim).
    /// Converte "Não", "N", "0", "False" (ou vazio) para "0" (Não).
    """
    if pd.isna(value) or value is None:
        return "0"  # Padrão é "Não" se o campo estiver vazio

    val_lower = str(value).strip().lower()

    # Lista de valores que consideramos como "SIM"
    if val_lower in ["1", "s", "sim", "true", "t", "verdadeiro"]:
        return "1"

    # Todos os outros casos são tratados como "NÃO"
    return "0"
