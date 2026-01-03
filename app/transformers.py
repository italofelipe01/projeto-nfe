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
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN

def normalize_currency(value):
    """
    /// Normaliza valores numéricos usando uma abordagem híbrida robusta.
    /// Step 1: Check if already number.
    /// Step 2: String cleanup.
    /// Step 3: Heuristic Analysis (Scenario A/B/C).
    """
    if pd.isna(value) or value is None:
        return "0.00"

    # Step 1: Type Check
    if isinstance(value, (int, float)):
        return str(value)

    # Step 2: String Cleanup
    val_str = str(value).strip()
    # Remove R$ e espaços extras
    val_str = val_str.replace("R$", "").strip()

    if not val_str:
        return "0.00"

    # Step 3: Heuristic Analysis

    # Case A (Brazilian Standard): Comma exists
    if "," in val_str:
        # The comma IS the decimal separator. The dots are thousands.
        # Action: Remove all dots. Replace comma with dot.
        val_str = val_str.replace(".", "")
        val_str = val_str.replace(",", ".")

    # Case B (System/International): Dot exists and NO Comma
    elif "." in val_str:
        # The dot IS the decimal separator.
        # Action: Keep the dot. Parse as float (implicitly done by returning the string for Decimal)
        pass

    # Case C (Clean Integer): No dots, no commas
    else:
        # Action: Parse directly.
        pass

    return val_str

def clean_numeric_string(value, max_len=None, pad_fixed_width=False):
    """
    /// Limpa e padroniza campos numéricos.
    /// Remove formatação (pontos, traços, barras) e deixa apenas os dígitos.
    /// Ex: "11.222.333/0001-44" -> "11222333000144"
    /// Se pad_fixed_width=True e max_len for fornecido, aplica zfill.
    """
    if pd.isna(value) or value is None:
        return ""

    # Usa RegEx (re.sub) para remover tudo que não for um dígito (\D)
    cleaned = re.sub(r"\D", "", str(value))

    if max_len:
        if len(cleaned) > max_len:
            # Garante a regra de negócio de tamanho máximo (ex: CEP max 8)
            cleaned = cleaned[:max_len]
        elif pad_fixed_width and len(cleaned) < max_len:
            # Padroniza com zeros à esquerda se solicitado
            cleaned = cleaned.zfill(max_len)

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


def preserve_exact_decimal(value, decimal_separator="virgula"):
    """
    /// Preserva o valor decimal exato (Immutable Decimal).
    /// Utiliza o 'normalize_currency' para inferir o formato.
    /// 1. Normaliza separadores (híbrido BR/US).
    /// 2. Valida se é numérico (Decimal).
    /// 3. Retorna a string exata, sem arredondamentos.
    """
    # 1. Normaliza
    val_str = normalize_currency(value)

    # 2. Validate (Strict 'No Text' Validation)
    try:
        # Verifica se é um número válido
        Decimal(val_str)
    except InvalidOperation:
        raise ValueError(f"Valor inválido encontrado: {value}. Apenas números são permitidos.")

    # 3. Return Exact String
    return val_str


def transform_monetary(value, decimal_separator, max_len=10):
    """
    /// Normaliza valores monetários.
    /// Trunca para 2 casas decimais SEM arredondar.
    /// Ex: 1234.5678 -> 1234.56
    """
    try:
        val_str = preserve_exact_decimal(value, decimal_separator)

        # Cria objeto Decimal para manipulação precisa
        d = Decimal(val_str)

        # Trunca para 2 casas decimais (ROUND_DOWN)
        truncated = d.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        # Currency Columns: formatting must enforce "{:.2f}".format(value)
        return "{:.2f}".format(truncated)
    except ValueError:
        # Propaga o erro para ser capturado pelo relatório de erros
        raise
    except Exception as e:
        raise ValueError(f"Erro ao transformar valor monetário: {e}")


def transform_aliquota(value, decimal_separator, max_len=None):
    """
    /// Normaliza a alíquota.
    /// Formata para até 4 casas decimais, preservando a precisão.
    /// Ex: 2.5 -> 2.5, 2.12349 -> 2.1234
    """
    try:
        val_str = preserve_exact_decimal(value, decimal_separator)
        d = Decimal(val_str)

        # Enforce up to 4 decimals (truncate)
        truncated = d.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

        # Rate (Alíquota): Allow up to 4 decimal places.
        # "{:.4f}".format(value).rstrip('0').rstrip('.')
        return "{:.4f}".format(truncated).rstrip("0").rstrip(".")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Erro ao transformar alíquota: {e}")


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
    cleaned = re.sub(r"\D", "", val_str)

    return cleaned.zfill(4)


def transform_date(value):
    """
    /// Normaliza datas.
    /// Converte "25/10/2025" ou "2025-10-25" para "dd/mm/aaaa" ("25/10/2025").
    /// Assume que 'validate_date_format' já confirmou que é uma data válida.
    """
    if pd.isna(value) or value is None:
        return ""

    val_str = str(value).strip()
    if " " in val_str:
        val_str = val_str.split(" ")[0]

    formats = ["%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"]
    for fmt in formats:
        try:
            date_obj = datetime.strptime(val_str, fmt)
            # REQUISITO: Output deve ser DD/MM/AAAA (com barras)
            return date_obj.strftime("%d/%m/%Y")
        except ValueError:
            continue

    # Se chegamos aqui, nenhum formato bateu.
    raise ValueError(f"Data '{value}' inválida ou formato desconhecido. Use DD/MM/AAAA ou AAAA-MM-DD.")


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
