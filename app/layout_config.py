# -*- coding: utf-8 -*-
"""
Módulo de Configuração do Layout.

Este arquivo é um dos mais importantes do projeto. Ele centraliza
as regras de negócio que definem o layout do arquivo TXT.
Ele NÃO contém lógica, apenas estruturas de dados (dicionários e listas)
que são usadas pelos outros módulos (converter, validators).
"""

# Mapeia nomes de colunas do arquivo do usuário (lista) para o nome interno (chave).
# Este é o "DE-PARA" (Tradução) do sistema.
# A 'chave' (ex: 'numero_documento') é o nome que usamos internamente no Python.
# A 'lista' (ex: ['numero nf', 'número nf', 'numero documento']) são os
# possíveis nomes de coluna que o usuário pode fornecer no arquivo CSV/XLSX.
# Isso torna o sistema flexível a pequenas variações no arquivo de entrada.
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
    'tributado_municipio': ['tributado no municipio', 'tributado no município', 'tribut. municipio'],
    
    # --- ATUALIZAÇÃO (Layout 21 campos) ---
    # Campos adicionados com base na documentação do ISS.net e no 'modelo.txt'.
    
    # 'Item LC' refere-se ao código do Item da Lista de Serviços (Lei Complementar).
    'item_lc': ['item lc', 'item da lista', 'item', 'codigo lc', 'código lc'],
    
    # 'Unidade Econômica' é um campo booleano (0 ou 1)
    'unidade_economica': ['unidade economica', 'unidade econômica', 'unid. economica']
    # --- FIM DA ATUALIZAÇÃO ---
}

# Define os campos do formulário (que vêm da interface web)
# que são obrigatórios para gerar o CABEÇALHO do arquivo TXT.
# Se algum desses faltar, o processo nem inicia.
REQUIRED_HEADER_FIELDS = [
    'inscricao_municipal',
    'mes',
    'ano',
    'razao_social',
    'codigo_servico'
]

# Define a ordem EXATA dos 21 campos no CORPO do arquivo TXT.
# Esta é a regra de negócio mais crítica do layout.
# A lista 'BODY_FIELDS_ORDER' é usada pelo 'converter.py' para
# montar a string final de cada linha, garantindo que
# 'modelo' seja sempre o 1º campo, 'numero_documento' o 2º, e assim por diante.
BODY_FIELDS_ORDER = [
    'modelo',
    'numero_documento',
    'valor_tributavel',
    'valor_documento',
    'aliquota',
    'data_emissao',
    'data_pagamento',
    'cpf_cnpj_prestador',
    'razao_social_prestador',
    'inscricao_municipal_prestador',
    'imposto_retido',
    'cep_prestador',
    'endereco_prestador',
    'numero_endereco',
    'bairro_prestador',
    'cidade_prestador',
    'uf_prestador',
    'ddd',
    'tributado_municipio',
    
    # --- ATUALIZAÇÃO (Layout 21 campos) ---
    # Adicionamos os dois novos campos ao FINAL da lista,
    # para que sejam o 20º e 21º campo no TXT.
    'item_lc',
    'unidade_economica'
    # --- FIM DA ATUALIZAÇÃO ---
]