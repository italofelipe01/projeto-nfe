# Projeto NFe - Automação ISS.net Goiânia

Este projeto é uma solução híbrida de **Processamento de Dados** e **Automação Robótica de Processos (RPA)** desenvolvida para facilitar a declaração de serviços contratados no portal ISS.net da Prefeitura de Goiânia.

O sistema atua em duas frentes principais:
1.  **Conversão e Validação (ETL):** Transforma planilhas (CSV/Excel) no layout estrito `.txt` exigido pelo sistema "Nota Control".
2.  **Automação de Envio (RPA):** Realiza o login seguro e o upload do arquivo gerado diretamente no portal, contornando desafios técnicos como teclados virtuais e grids dinâmicos.

---

## 🚀 Arquitetura do Sistema

O projeto segue uma arquitetura modular para garantir escalabilidade e manutenção:

* **Backend Web (Flask):** Gerencia a interface de usuário, upload de arquivos, validação de regras de negócio e geração do layout `.txt`. Implementa o padrão *Application Factory*.
* **Core RPA (Playwright):** Módulo isolado responsável pela interação com o portal governamental. Executa em thread separada para não bloquear a interface web.
* **Frontend:** Interface leve para upload e feedback de progresso (Polling de status da tarefa).

---

## 🛠️ Pré-requisitos

* **Python 3.10+**
* **Navegadores:** Chromium (instalado via Playwright)

---

## ⚙️ Instalação e Configuração

### 1. Instalação das Dependências

Execute o comando abaixo para instalar as bibliotecas necessárias (Flask, Pandas, Playwright, etc.):

```bash
pip install -r requirements.txt
````

### 2\. Instalação dos Binários do Navegador

O Playwright requer a instalação dos binários dos navegadores para controlar a automação:

```bash
playwright install chromium
```

### 3\. Configuração de Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto com as credenciais de acesso ao portal ISS.net. O projeto utiliza um **Login Master (Contador)** para acessar todas as empresas.

```env
# Configurações do Robô
RPA_MODE=development # ou production
ISSNET_URL=https://www.issnetonline.com.br/goiania/online/login/login.aspx

# Credenciais GLOBAIS do Portal ISS.net
ISSNET_USER=seu_usuario_master
ISSNET_PASS=sua_senha_master

# Configurações do Flask
FLASK_ENV=development
SECRET_KEY=sua_chave_secreta
```

### 4\. Arquivo de Configurações (CSV)

Certifique-se de que o arquivo `configuracoes.csv` esteja na raiz do projeto. Ele define a lista de empresas disponíveis e seus detalhes específicos.

**Estrutura do CSV (Separador: Ponto e Vírgula `;`):**
`id;apelido;razao_social;inscricao_municipal;cnpj`

Exemplo:
```csv
1;EMPRESA ALPHA;RAZAO SOCIAL ALPHA LTDA;123456;12345678000199
2;EMPRESA BETA;RAZAO SOCIAL BETA LTDA;654321;98765432000199
```

-----

## ▶️ Como Executar

Para iniciar o servidor web e a interface de controle:

```bash
python run.py
```

O sistema estará acessível em: `http://127.0.0.1:5000`

-----

## 📂 Estrutura do Projeto

```text
projeto-nfe/
├── app/                     # Núcleo da Aplicação Web
│   ├── __init__.py          # Application Factory
│   ├── main.py              # Rotas (Blueprint) e Endpoints API
│   ├── converter.py         # Lógica de Conversão ETL
│   ├── validators.py        # Regras de Validação (CPF, Datas, Valores)
│   ├── file_handler.py      # I/O de Arquivos
│   └── config.py            # Configurações do Flask
├── rpa/                     # Núcleo de Automação (Robô)
│   ├── bot_controller.py    # Orquestrador (Facade)
│   ├── authentication.py    # Login (Bypass de Teclado Virtual)
│   ├── portal_navigator.py  # Navegação em Menus e Grids Dinâmicos
│   ├── file_uploader.py     # Injeção de Arquivo em Input Oculto
│   └── config_rpa.py        # Seletores e Variáveis RPA
├── rpa_logs/                # Logs de Execução e Screenshots de Erro
├── static/                  # Assets (CSS, JS, Fontes)
├── templates/               # HTML (Interface do Usuário)
├── uploads/                 # Área temporária de uploads
├── downloads/               # Área de saída dos arquivos .txt gerados
├── run.py                   # Ponto de entrada da aplicação
└── requirements.txt         # Dependências do projeto
```

-----

## 🤖 Detalhes Técnicos do RPA

O módulo RPA foi projetado para superar proteções específicas do portal ISS.net:

1.  **Teclado Virtual:** O campo de senha é *readonly*. O robô lê o mapeamento visual dos botões (`#btn1` a `#btn5`) em tempo real e clica na combinação correta baseada na senha definida no `.env`.
2.  **Grid Dinâmica:** A seleção de empresas ignora IDs dinâmicos (`dgEmpresas_ct13`), utilizando filtros de CNPJ e seletores estruturais robustos.
3.  **Upload Oculto:** O arquivo não é enviado clicando no botão visual, mas sim injetado diretamente no `input` oculto (`#txtUpload`) do DOM.
4.  **Tratamento de Erros:** Screenshots automáticos são salvos em `rpa_logs/screenshots` em caso de falha no login ou no envio.

-----

## 📄 Layout de Conversão

O sistema converte arquivos CSV/Excel seguindo estritamente o manual "Importação de Serviços Contratados", garantindo:

  * Cabeçalho padrão com a frase de validação "EXPORTACAO DECLARACAO ELETRONICA-ONLINE-NOTA CONTROL".
  * Sanitização de CPFs/CNPJs.
  * Formatação de valores decimais e datas.
