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
    /// Força estritamente 2 casas decimais usando Decimal.quantize.
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    if pd.isna(value) or value is None:
        return "0.00"

    # Remove símbolos comuns (R$) e espaços
    cleaned_str = str(value).replace("R$", "").strip()

    # CORREÇÃO: Padronização para 'virgula' e 'ponto'
    if decimal_separator == "virgula":
        # Formato Brasil (1.234,56) -> Remove ponto milhar, troca virgula decimal
        cleaned_str = cleaned_str.replace(".", "").replace(",", ".")
    else:
        # Formato EUA (1,234.56) -> Remove virgula milhar
        cleaned_str = cleaned_str.replace(",", "")

    # Remove qualquer outro caractere não numérico que sobrou
    cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

    try:
        d = Decimal(cleaned_str)
        # Força 2 casas decimais
        formatted_val = d.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        return str(formatted_val)
    except (ValueError, TypeError, InvalidOperation):
        return "0.00"


def transform_aliquota(value, decimal_separator, max_len=None):
    """
    /// Normaliza a alíquota.
    /// Força estritamente 2 casas decimais usando Decimal.quantize.
    /// Ex: 5 -> "5.00", 2.3456 -> "2.35"
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    if pd.isna(value) or value is None:
        return "0.00"

    cleaned_str = str(value).strip()

    # Se estiver vazio
    if not cleaned_str:
        return "0.00"

    # Padronização para 'virgula' e 'ponto'
    if decimal_separator == "virgula":
        cleaned_str = cleaned_str.replace(",", ".")

    # Remove qualquer coisa que não seja dígito ou ponto
    cleaned_str = re.sub(r"[^0-9.]", "", cleaned_str)

    try:
        d = Decimal(cleaned_str)
        # Força 2 casas decimais
        formatted_val = d.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        return str(formatted_val)

    except (ValueError, TypeError, InvalidOperation):
        return "0.00"


def transform_item_lc(value):
    """
    /// Normaliza o Item LC (Lista de Serviços).
    /// Deve ser tratado como TEXTO e ter 4 dígitos, preenchidos com zeros à esquerda.
    /// Ex: 703 -> "0703", "1414" -> "1414".
    """
    if pd.isna(value) or value is None:
        return "0000"

    val_str = str(value).strip()

    # Remove parte decimal se houver (ex: "703.0" -> "703")
    if "." in val_str:
         try:
             # Tenta converter para float depois int para remover decimal .0
             # Mas cuidado com 703.5 (não deveria acontecer em LC code)
             # Vamos assumir que LC é codigo inteiro.
             val_float = float(val_str)
             val_str = str(int(val_float))
         except ValueError:
             pass

    # Remove caracteres não numéricos (opcional, mas seguro para códigos)
    # Prompt diz: "If input is 703 -> 0703".
    # Vamos limpar apenas para garantir que " 703 " funcione.
    # Mas se vier "14.01", limpar remove o ponto -> "1401"?
    # LC usually is "14.01". Removing dot makes it "1401". This matches standard LC format often.
    # However, standard says "always contain 4 digits". "0703".
    # Let's strip non-digits to be safe.
    cleaned = re.sub(r"\D", "", val_str)

    return cleaned.zfill(4)


def transform_date(value):
    """
    /// Normaliza datas.
    /// Converte "25/10/2025" ou "2025-10-25" para "ddmmaaaa" ("25102025").
    /// Assume que 'validate_date_format' já confirmou que é uma data válida.
    """
    if pd.isna(value) or value is None:
        return ""

    val_str = str(value).strip()
    if " " in val_str:
        val_str = val_str.split(" ")[0]

    try:
        # pd.to_datetime é flexível para "adivinhar" o formato
        date_obj = pd.to_datetime(val_str, dayfirst=True)
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
