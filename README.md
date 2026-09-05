# MetaFoco System - Controle de Endividamento e Visualização de Dados

Sistema web completo para controle de endividamento, importação de planilhas Excel e geração de dashboards empresariais.

## Stack
- **Backend**: Python + FastAPI + SQLAlchemy
- **Banco de dados**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript puro + ApexCharts (gráficos) + jsPDF/html2canvas (exportação)

## Estrutura
```
.
├── backend/
│   ├── main.py            # Aplicação FastAPI (servidor + rotas)
│   ├── database.py        # Conexão com PostgreSQL
│   ├── init_db.py         # Cria tabelas + usuário SuperAdmin
│   ├── import_initial.py  # Importa a planilha inicial
│   ├── models/            # Modelos SQLAlchemy (Usuario, Contrato)
│   ├── routers/           # Endpoints (auth, contratos, upload, dashboard)
│   ├── utils/             # Autenticação e autorização
│   └── requirements.txt
├── frontend/
│   ├── css/styles.css     # Tema escuro (estilo Grafana)
│   ├── js/auth.js         # Lógica de autenticação no frontend
│   ├── assets/            # Logo, imagens
│   └── pages/
│       ├── login.html     # Tela de login
│       ├── dashboard.html # Dashboard com gráficos, filtros e exportação
│       ├── contratos.html # Cadastro manual e listagem de contratos
│       ├── upload.html    # Upload de arquivos Excel
│       └── usuarios.html  # Gestão de usuários (apenas admin)
├── start.sh               # Script para iniciar o sistema
└── agents.md              # Histórico de desenvolvimento da IA
```

## Como executar

### Pré-requisitos
- Python 3.9+
- PostgreSQL em execução (local, porta 5432)
- Usuário PostgreSQL `postgres` com permissão local

### Execução automática (recomendado)
```bash
./start.sh
```

### Execução manual
```bash
# 1. Criar banco
psql -U postgres -h localhost -c "CREATE DATABASE metafoco;"

# 2. Instalar dependências
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Inicializar banco (tabelas + SuperAdmin)
python init_db.py

# 4. Importar planilha inicial (opcional, já feito)
python import_initial.py "../_Endividamento Shinoda versao 06.xlsm"

# 5. Iniciar servidor
python main.py
```

Acesse **http://localhost:8000** no navegador.

## Credenciais iniciais
| Perfil | Usuário | Senha |
|--------|---------|-------|
| SuperAdmin | `admin_meta` | `M&t@_F0CO_2026` |

## Funcionalidades

### 1. Input de dados
- **Importação inicial**: transcreve a aba `ENDIVIDAMENTO` da planilha para o banco preservando formatos.
- **Upload de arquivos**: upload de novas planilhas com **insert sem duplicação**
  (chave única: contrato + instituição + parcela + data base).
- **Cadastro manual**: botão "Cadastrar contrato" com formulário completo, com detecção de duplicados.

### 2. Visualização
- Dashboards com KPIs (total contratado, curto prazo, longo prazo, total a pagar)
- Gráficos por instituição, modalidade, empresa, índice, garantias e vencimentos
- Filtros (data base, instituição, empresa, modalidade, índice)
- Exportação em **PDF**, **PNG** e **CSV**
- Botão de **refresh** para atualização de dados

### 3. Controle de usuários
- Perfil **SuperAdmin** (full access) - `admin_meta`
- Perfil **Leitura** - apenas visualiza gráficos
- Perfil **Gestor** - upload e funcionalidades
- Apenas `admin_meta` cria usuários
- Senha padrão `Meta12345` para novos usuários
- Primeiro login exige troca de senha
- Admin pode resetar senha de usuários (botão)

### 4. Regras de negócio
- Exposição por instituição (saldo a pagar)
- Classificação curto prazo (até 12 meses) vs longo prazo (acima de 12 meses)
- Análise por modalidade, índice (PRÉ, CDI, TLP, USD) e garantias

## Configuração
Edite `backend/.env` para ajustar:
- `DATABASE_URL` - string de conexão do PostgreSQL
- `SECRET_KEY` - chave de assinatura JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES` - expiração do token

## Porta de execução
O servidor padrão usa a porta **8000**. Se estiver ocupada, ajuste no final de `backend/main.py`.