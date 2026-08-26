# ObservAR

Plataforma web para gestão, consulta e análise de dados de qualidade do ar.

O **ObservAR** centraliza dados provenientes da base MonitorAr e fornece recursos para importação, visualização e gerenciamento de medições ambientais, estações de monitoramento e usuários.

## Funcionalidades

- Autenticação de usuários.
- Autenticação em duas etapas com reconhecimento facial.
- Controle de acesso baseado em níveis de usuário.
- Dashboard para acompanhamento dos dados.
- Consulta de medições de qualidade do ar.
- Visualização das estações de monitoramento.
- Visualização geográfica das estações em mapa.
- Importação de arquivos CSV.
- Processamento de grandes arquivos em lotes de 1.000 registros.
- Detecção de arquivos já importados utilizando SHA-256.
- Prevenção de medições duplicadas.
- Identificação de conflitos durante importações.
- Histórico e acompanhamento das importações.
- Cancelamento de importações em andamento.
- Registro de autenticações e acessos.
- Área administrativa para gerenciamento de usuários.
- Cadastro de biometria facial.
- Área de análises internas.

## Tecnologias utilizadas

### Backend

- Python
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- Werkzeug

### Banco de dados

- MySQL

### Processamento de dados

- Pandas

### Frontend

- HTML5
- CSS3
- JavaScript
- Jinja2

### Segurança e autenticação

- Hash seguro de senhas com Werkzeug
- Controle de sessão com Flask
- Proteção CSRF
- Controle de acesso por nível de usuário
- Reconhecimento facial para segunda etapa de autenticação

### Testes

- Pytest

## Estrutura do projeto

```text
APS/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│
├── scripts/
├── tests/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Models

Responsáveis pela representação das entidades e relacionamentos do banco de dados, incluindo:

- Usuários
- Perfis
- Biometria facial
- Municípios
- Estações de monitoramento
- Parâmetros monitorados
- Medições de qualidade do ar
- Análises internas
- Logs de autenticação e acesso
- Histórico de importações

### Routes

Contêm as rotas HTTP da aplicação, incluindo autenticação, páginas principais e gerenciamento das importações.

### Services

Concentram as regras de negócio da aplicação, como:

- Autenticação
- Autorização
- Auditoria
- Biometria
- Importação de dados
- Processamento dos dados MonitorAr

### Templates

Interfaces HTML renderizadas pelo Flask utilizando Jinja2.

## Importação de dados

O ObservAR permite importar arquivos CSV contendo dados da base MonitorAr diretamente pela interface administrativa.

Os arquivos são processados em lotes de:

```text
1.000 registros
```

Essa estratégia permite trabalhar com arquivos de grande volume sem a necessidade de carregar todo o conteúdo simultaneamente na memória.

Antes da importação, o sistema calcula o hash **SHA-256** do arquivo para identificar arquivos que já foram processados anteriormente.

Durante o processamento, o sistema também verifica as medições existentes no banco de dados, permitindo:

- Inserir somente registros novos.
- Ignorar registros duplicados.
- Identificar conflitos.
- Evitar duplicação mesmo quando o arquivo possui outro nome.
- Manter histórico das importações realizadas.

## Banco de dados

A aplicação utiliza MySQL para armazenamento dos dados.

Entre as principais entidades estão:

```text
Usuario
Perfil
BiometriaFacial
Municipio
EstacaoMonitoramento
ParametroMonitorado
MedicaoQualidadeAr
AnaliseInterna
LogAutenticacao
LogAcesso
HistoricoImportacao
```

Os relacionamentos são gerenciados através do SQLAlchemy.

## Instalação

Clone o repositório:

```bash
git clone URL_DO_REPOSITORIO
```

Entre na pasta do projeto:

```bash
cd APS
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

### Windows

Ative o ambiente:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Configuração

O projeto possui um arquivo:

```text
.env.example
```

Utilize-o como referência para configurar as variáveis de ambiente necessárias para executar a aplicação.

Informações sensíveis, como senhas, chaves e credenciais do banco de dados, não devem ser adicionadas ao repositório.

## Executando a aplicação

Com o ambiente virtual ativo:

```bash
python app.py
```

A aplicação poderá então ser acessada pelo endereço configurado pelo Flask.

## Testes

Para executar todos os testes automatizados:

```bash
python -m pytest -q
```

Os testes verificam funcionalidades importantes da aplicação, incluindo:

- Autenticação
- Biometria
- Permissões
- Paginação
- Importação de dados
- Validação de CSV
- Prevenção de duplicidades

## Segurança

O ObservAR implementa diferentes mecanismos de proteção, incluindo:

- Armazenamento de senhas utilizando hash.
- Sessões autenticadas.
- Proteção contra requisições CSRF.
- Controle de permissões.
- Autenticação facial como segunda etapa.
- Registro de tentativas de autenticação.
- Registro de acessos.
- Validação dos arquivos enviados.
- Proteção contra importações duplicadas.

## Contexto

Projeto desenvolvido no contexto da disciplina **APS — Processamento de Imagem e Visão Computacional**.

O sistema combina gerenciamento de dados ambientais, autenticação, reconhecimento facial e visualização de informações relacionadas à qualidade do ar.
