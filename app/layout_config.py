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

# Define os campos do formulário (cabeçalho) que são obrigatórios
# Baseado no 'workflow_conversao.pdf'
REQUIRED_HEADER_FIELDS = [
    'inscricao_municipal',
    'mes',
    'ano',
    'razao_social',
    'codigo_servico' # <-- MODIFICAÇÃO: Adicionado de volta
]

# Define a ordem exata dos 19 campos no corpo do arquivo TXT
# Baseado no 'regras_layout_txt.pdf'
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
    'tributado_municipio'
]