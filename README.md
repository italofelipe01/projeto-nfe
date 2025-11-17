# Projeto Conversor de Declarações ISS.net

Este projeto é uma aplicação web Full-Stack (Python/Flask + JavaScript) projetada para resolver um problema de negócio específico: a conversão de arquivos de notas fiscais (Serviços Contratados) de formatos comuns (CSV, XLSX) para o layout de importação `.txt` específico exigido pelo sistema ISS.net.

A aplicação automatiza a validação de dados, a formatação de campos e a detecção de erros, transformando um processo manual e propenso a erros em uma tarefa de um clique.

## 1\. Funcionalidades Principais

  * **Interface Web Amigável:** Uma interface de três etapas (Upload, Processamento, Resultado) construída em HTML, CSS e JavaScript.
  * **Upload Flexível:** Aceita arquivos `.csv` e `.xlsx` (incluindo drag-and-drop).
  * **Processamento Assíncrono:** Utiliza `threading` no backend (Flask) para que o processamento de arquivos longos não trave o servidor, com feedback em tempo real para o usuário via *polling*.
  * **Mapeamento de Colunas (DE-PARA):** O sistema não exige um formato rígido de entrada. Ele mapeia nomes de colunas comuns (ex: "numero nf", "número nf") para os campos internos do layout (ex: `numero_documento`).
  * **Validação de Dados Abrangente:** O sistema valida cada linha *antes* de processá-la, verificando:
      * Tipos de dados (datas, números, decimais).
      * Formatos (ex: CPF/CNPJ, CEP, UF).
      * Regras de negócio (ex: "Valor Tributável" não pode ser maior que "Valor do Documento").
      * **Duplicatas:** Detecta e rejeita automaticamente notas com o mesmo `Número de Documento` e `CNPJ/CPF do Prestador` dentro do *mesmo arquivo*.
  * **Transformação de Dados:** Formata automaticamente os dados para o padrão do layout ISS.net (ex: datas para `ddmmaaaa`, valores para `1234.50`, booleanos para `1` ou `0`).
  * **Relatório de Erros Detalhado:** Ao final, exibe um resumo (Total, Sucessos, Erros) e lista exatamente quais linhas falharam e o motivo, permitindo a correção rápida no arquivo de origem.
  * **Geração de Dropdown:** Carrega automaticamente os dados do `configuracoes.csv` para preencher o formulário do "Tomador de Serviço", agilizando o preenchimento.

## 2\. Tecnologias Utilizadas

  * **Backend:**
      * **Python 3**
      * **Flask:** Micro-framework web para servir a aplicação e as rotas de API (`/upload`, `/status`, `/download`).
      * **Pandas:** Usado para a leitura robusta de arquivos `.csv` e `.xlsx` e para a detecção de duplicatas.
      * **openpyxl:** Dependência (usada pelo Pandas) para ler arquivos `.xlsx`.
      * **validate-docbr:** Usada para a validação de dígitos verificadores de CPF/CNPJ.
  * **Frontend:**
      * **HTML5**
      * **CSS3** (Vanilla)
      * **JavaScript (ES6+):** (Vanilla) Usado para controle da interface, validação de formulário, AJAX (Fetch API) para upload e *polling* de status.

## 3\. Estrutura do Projeto

A lógica da aplicação está contida no diretório `app/` e é separada por responsabilidade:

```
projeto-nfe/
│
├── app/
│   ├── __init__.py
│   ├── main.py             # (Servidor Flask) Define as rotas (endpoints) e orquestra o app.
│   ├── converter.py        # (Orquestrador) O "cérebro" da conversão. Chamado pelo main.py.
│   ├── validators.py       # (Regras de Entrada) Valida os dados BRUTOS do arquivo do usuário.
│   ├── transformers.py     # (Regras de Saída) Formata os dados validados para o padrão do TXT.
│   ├── layout_config.py    # (Regras de Negócio) ONDE A MÁGICA ACONTECE. Define o DE-PARA e a ORDEM.
│   ├── file_handler.py     # (I/O) Funções auxiliares para ler (Pandas) e salvar arquivos TXT.
│   └── config.py           # Configurações do app (ex: pastas de UPLOADS).
│
├── static/
│   ├── css/style.css       # Estilos
│   └── js/app.js           # Lógica do Frontend (AJAX, Polling, UI)
│
├── templates/
│   └── index.html          # A página HTML principal.
│
├── docs/
│   ├── Documentação ISS.net.md   # (Exemplo) A especificação que define o layout.
│   └── ...
│
├── uploads/                # (Temporário) Onde os arquivos CSV/XLSX são salvos.
├── downloads/              # (Temporário) Onde os arquivos TXT gerados são salvos.
│
├── configuracoes.csv       # Arquivo de dados para preencher o dropdown de empresas.
└── requirements.txt        # Dependências do Python.
```

## 4\. Lógica de Negócio Central

O valor desta aplicação está na implementação das regras de negócio do ISS.net (presentes na documentação). Isso é centralizado em 3 arquivos:

1.  **`app/layout_config.py`**

      * `COLUMN_MAPPING`: Um dicionário Python que mapeia dezenas de possíveis nomes de coluna (ex: `['numero nf', 'número nf']`) para um nome interno (`numero_documento`). É o "DE-PARA" que torna o sistema flexível.
      * `BODY_FIELDS_ORDER`: Uma lista que define a ordem *exata* dos 21 campos no arquivo `.txt` final.

2.  **`app/validators.py`**

      * Contém todas as funções que verificam se os dados do *arquivo de entrada* são válidos (ex: `validate_date_format`, `validate_cpf_cnpj`, `validate_tributavel_vs_documento`).

3.  **`app/transformers.py`**

      * Contém todas as funções que formatam os dados para o *arquivo de saída* (ex: `transform_date` converte uma data para `ddmmaaaa`, `transform_monetary` converte "R$ 1.234,56" para "1234.56").

## 5\. Instalação e Execução

Para rodar este projeto localmente:

1.  **Clone o repositório:**

    ```bash
    git clone [URL_DO_REPOSITORIO]
    cd projeto-nfe
    ```

2.  **Crie e ative um ambiente virtual:**

    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute a aplicação:**

    ```bash
    python app/main.py
    ```

5.  **Acesse no navegador:**
    Abra `http://127.0.0.1:5000`

## 6\. Como Usar (Guia Rápido)

1.  Acesse `http://127.0.0.1:5000`.
2.  Na **Etapa 1**:
      * Selecione uma empresa no dropdown "Selecionar Configuração de Tomador" (isso preencherá a Inscrição, Razão Social, Mês e Ano).
      * *Se não usar o dropdown*, preencha Inscrição Municipal, Razão Social, Mês e Ano manualmente.
      * Preencha o **Código do Serviço Contratado**.
      * Selecione o "Separador decimal" (Vírgula ou Ponto) que o *seu arquivo CSV/XLSX utiliza*.
      * Indique se o sistema deve validar o "Dígito Verificador" do CPF/CNPJ.
      * Arraste ou clique para fazer o upload do seu arquivo `.csv` ou `.xlsx`.
3.  Clique em **"Converter"**.
4.  A **Etapa 2** mostrará o progresso da validação.
5.  A **Etapa 3** mostrará o resultado:
      * **Sucesso:** O botão "Baixar Arquivo TXT" ficará ativo.
      * **Com Erros:** O campo "Detalhes dos Erros" será preenchido, indicando quais linhas falharam e o porquê. Corrija seu arquivo de origem e tente novamente.
      * **Erro Crítico:** Uma mensagem vermelha indicará se colunas essenciais não foram encontradas ou se o arquivo está vazio.

-----