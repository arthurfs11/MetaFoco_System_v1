#!/usr/bin/env bash
# Script de inicialização do MetaFoco System
set -e
cd "$(dirname "$0")"

echo "======================================"
echo "  MetaFoco System - Iniciando..."
echo "======================================"

# Verificar se PostgreSQL está rodando
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
  echo "[ERRO] PostgreSQL não está rodando. Inicie o PostgreSQL primeiro."
  exit 1
fi

# Criar banco se não existir
if ! psql -U postgres -h localhost -lqt | cut -d \| -f 1 | grep -qw metafoco; then
  echo "Criando banco de dados 'metafoco'..."
  psql -U postgres -h localhost -c "CREATE DATABASE metafoco;"
fi

cd backend

# Carregar credenciais de ambiente (backend/.env) se existir
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs) 2>/dev/null || true
fi
ADMIN_EMAIL="${ADMIN_EMAIL:-admin_meta}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

# Verificar venv
if [ ! -d "venv" ]; then
  echo "Criando ambiente virtual..."
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

# Inicializar banco (cria tabelas + SuperAdmin)
echo "Inicializando banco de dados..."
python init_db.py

# Importar planilha inicial (se houver contrato inicial a importar)
INITIAL_XLSX="../_Endividamento Shinoda versao 06.xlsm"
if [ -f "$INITIAL_XLSX" ] && [ "$(psql -U postgres -h localhost -d metafoco -t -c 'SELECT COUNT(*) FROM contratos;' | xargs)" = "0" ]; then
  echo "Importando planilha inicial de endividamento..."
  python import_initial.py "$INITIAL_XLSX"
else
  echo "Dados já importados ou planilha não encontrada. Pulando importação inicial."
fi

echo ""
echo "======================================"
echo "  Iniciando servidor em http://localhost:9090"
if [ -n "$ADMIN_PASSWORD" ]; then
  echo "  Usuário: $ADMIN_EMAIL  (credenciais em backend/.env)"
else
  echo "  Aviso: defina ADMIN_PASSWORD em backend/.env antes de iniciar"
fi
echo "======================================"
echo ""
python main.py