import re
import datetime
from decimal import Decimal, InvalidOperation

# --- Funções Genéricas de Limpeza e Formatação ---

def clean_numeric_string(value):
    """
    Remove todos os caracteres não numéricos de uma string.
    Usado para CPF/CNPJ, CEP, Inscrição Municipal, Números de Documento, etc.
    (Conforme workflow: 'Remover caracteres especiais (., /, -)')
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'\D', '', value)

def sanitize_and_truncate(value, max_length):
    """
    Converte para string, remove quebras de linha e trunca no tamanho máximo.
    Usado para campos de texto como Razão Social, Endereço, Bairro, etc.
    (Ex: Limitar a 150 caracteres)
    """
    if value is None:
        return ''
    
    # Converte (caso seja número, etc.), remove espaços extras e quebras de linha
    text = str(value).strip().replace('\n', ' ').replace('\r', ' ')
    
    # Trunca no tamanho máximo
    return text[:max_length]

def to_boolean_str(value):
    """
    Converte valores "truthy" (Sim, True, S, 1) para a string '1'
    e valores "falsy" (Não, False, N, 0) para a string '0'.
    (Conforme workflow: Aceitar: Sim/Não, True/False, S/N, 1/0)
    """
    if value is None:
        return '0' # Default para 'NÃO'

    cleaned_val = str(value).strip().lower()
    
    if cleaned_val in ['sim', 's', 'true', '1']:
        return '1'
    if cleaned_val in ['nao', 'não', 'n', 'false', '0']:
        return '0'
        
    return '0' # Default para 'NÃO' se não reconhecido

def format_date_ddmmaaaa(date_value):
    """
    Tenta converter uma string de data (com vários formatos) 
    para o formato 'ddmmaaaa' exigido.
    (Conforme workflow: Converter data [...] para formato ddmmaaaa)
    
    Retorna a string formatada ou None se a data for inválida.
    """
    if date_value is None:
        return None

    # Se for um objeto datetime do pandas/excel, formata direto
    if isinstance(date_value, (datetime.date, datetime.datetime)):
        return date_value.strftime('%d%m%Y')

    date_str = str(date_value).strip()
    
    # Remove separadores comuns
    cleaned_date_str = re.sub(r'[\./-]', '', date_str)
    
    # Se já estiver no formato ddmmaaaa (8 dígitos), tenta validar
    if len(cleaned_date_str) == 8:
        try:
            # Valida se é uma data real
            datetime.datetime.strptime(cleaned_date_str, '%d%m%Y')
            return cleaned_date_str # Retorna a string limpa
        except ValueError:
            pass # Continua para outras tentativas

    # Tenta formatos comuns (ex: YYYY-MM-DD, DD/MM/YYYY)
    possible_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
    
    for fmt in possible_formats:
        try:
            parsed_date = datetime.datetime.strptime(date_str.split(' ')[0], fmt) # Ignora horas
            return parsed_date.strftime('%d%m%Y')
        except ValueError:
            continue
            
    # Se falhar em tudo, retorna None
    return None

def format_monetary_value(value, source_decimal_separator='virgula'):
    """
    Converte um valor monetário (string) para o formato 'Decimal' (ponto como separador),
    removendo 'R$' e separadores de milhar.
    
    (Conforme workflow: Aplicar separador decimal correto (sempre ponto no TXT final))
    (Baseado na opção do formulário)
    
    Retorna uma string pronta para 'Decimal' (ex: "1234.50") ou None.
    """
    if value is None:
        return None
        
    if isinstance(value, (int, float, Decimal)):
        # Se já for numérico, apenas formata
        return str(Decimal(value).quantize(Decimal('0.01')))

    value_str = str(value).strip()

    # Remove 'R$' e espaços
    cleaned_str = value_str.replace('R$', '').strip()

    # Determina o que remover (milhar) e o que trocar (decimal)
    if source_decimal_separator == 'virgula':
        # Formato Brasil (1.234,50)
        # Remove '.' (milhar) e troca ',' por '.' (decimal)
        cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
    else:
        # Formato USA (1,234.50)
        # Remove ',' (milhar)
        cleaned_str = cleaned_str.replace(',', '')

    # Remove qualquer coisa que não seja dígito ou o ponto decimal
    cleaned_str = re.sub(r'[^\d.]', '', cleaned_str)

    # Valida se é um Decimal válido
    try:
        # Arredonda para 2 casas decimais
        decimal_value = Decimal(cleaned_str).quantize(Decimal('0.01'))
        return str(decimal_value)
    except (InvalidOperation, ValueError):
        return None

# --- Funções Específicas de Domínio (Validação) ---

# Lista de UFs válidas (Conforme workflow: Verificar sigla válida (UF))
VALID_UFS = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
}

def validate_uf(uf_str):
    """
    Verifica se a string da UF é válida (2 caracteres e existe na lista).
    Retorna a UF em maiúsculas se válida, senão None.
    """
    if uf_str is None:
        return None
    
    uf_upper = str(uf_str).strip().upper()
    
    if len(uf_upper) == 2 and uf_upper in VALID_UFS:
        return uf_upper
    
    return None


# --- Lógica de Validação de Dígito Verificador (CPF/CNPJ) ---

def _validate_cpf_dv(cpf):
    """Função interna para validar DV de CPF."""
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais (ex: 111.111.111-11)
    if cpf == cpf[0] * 11:
        return False

    # Cálculo do primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto
    
    if dv1 != int(cpf[9]):
        return False

    # Cálculo do segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto

    return dv2 == int(cpf[10])

def _validate_cnpj_dv(cnpj):
    """Função interna para validar DV de CNPJ."""
    if len(cnpj) != 14:
        return False

    # Pesos para o cálculo do primeiro DV
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    # Cálculo do primeiro DV
    soma = 0
    for i in range(12):
        soma += int(cnpj[i]) * pesos1[i]
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto

    if dv1 != int(cnpj[12]):
        return False
    
    # Pesos para o cálculo do segundo DV
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    # Cálculo do segundo DV
    soma = 0
    for i in range(13):
        soma += int(cnpj[i]) * pesos2[i]
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto
        
    return dv2 == int(cnpj[13])

def validate_cpf_cnpj(number_str):
    """
    Valida o dígito verificador de um CPF (11 dígitos) ou CNPJ (14 dígitos).
    Espera receber uma string *já limpa* (apenas números).
    """
    if not number_str:
        return False
        
    if len(number_str) == 11:
        return _validate_cpf_dv(number_str)
    elif len(number_str) == 14:
        return _validate_cnpj_dv(number_str)
    else:
        # Se não tiver 11 ou 14 dígitos, é inválido para esta validação.
        return False