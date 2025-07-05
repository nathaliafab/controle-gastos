#!/bin/bash
# Definir cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Configuração para Desenvolvimento Local${NC}"
echo "=============================================="

# Detectar sistema operacional
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON_CMD="python"
    VENV_ACTIVATE="venv/Scripts/activate"
    echo -e "${YELLOW}🪟 Sistema Windows detectado${NC}"
else
    PYTHON_CMD="python3"
    VENV_ACTIVATE="venv/bin/activate"
    echo -e "${YELLOW}🐧 Sistema Linux/Mac detectado${NC}"
fi

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo -e "${GREEN}🐍 Criando ambiente virtual Python...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
else
    echo -e "${YELLOW}⚠️  Ambiente virtual já existe${NC}"
fi

# Ativar ambiente virtual
echo -e "${GREEN}🔄 Ativando ambiente virtual...${NC}"
source $VENV_ACTIVATE

# Criar diretórios necessários
echo -e "${GREEN}📁 Criando diretórios necessários...${NC}"
mkdir -p logs
mkdir -p media/{extratos,configs,resultados}
mkdir -p staticfiles
mkdir -p backups

# Configurar permissões básicas
echo -e "${GREEN}🔐 Configurando permissões...${NC}"
chmod 755 logs
chmod 755 media
chmod 755 staticfiles
chmod 755 media/extratos
chmod 755 media/configs
chmod 755 media/resultados
chmod 755 backups

# Gerar .env para desenvolvimento se não existir
if [ ! -f .env ]; then
    echo -e "${GREEN}🔑 Gerando configurações para desenvolvimento...${NC}"
    
    # Gerar SECRET_KEY
    SECRET_KEY=$(python3 -c "
import secrets
import string
alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_=+[]{}|;:,.<>?'
secret_key = ''.join(secrets.choice(alphabet) for _ in range(64))
")
    
    # Gerar ENCRYPTION_KEY
    ENCRYPTION_KEY=$(python3 -c "
import secrets
import string
alphabet = string.ascii_letters + string.digits
encryption_key = ''.join(secrets.choice(alphabet) for _ in range(32))
")
    
    # Criar arquivo .env para DESENVOLVIMENTO
    cat > .env << EOF
# Configurações para DESENVOLVIMENTO LOCAL
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Configurações de banco de dados
DATABASE_URL=sqlite:///db.sqlite3

# Configurações de segurança - DESENVOLVIMENTO (HTTP/HTTPS local)
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY
SECURE_REFERRER_POLICY=strict-origin-when-cross-origin

# Configurações de cookies - DESENVOLVIMENTO (HTTP/HTTPS local)
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SECURE=False
CSRF_COOKIE_HTTPONLY=True
CSRF_COOKIE_SAMESITE=Lax

# Configurações de upload
FILE_UPLOAD_MAX_MEMORY_SIZE=50MB
MAX_UPLOAD_SIZE=50MB

# Configurações de rate limiting
RATELIMIT_ENABLE=False
RATELIMIT_USE_CACHE=default

# Configurações de logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/app.log
EOF
    
    chmod 600 .env
    echo -e "${GREEN}✅ Arquivo .env criado para desenvolvimento${NC}"
else
    echo -e "${YELLOW}⚠️  Arquivo .env já existe${NC}"
fi

# Verificar dependências
echo -e "${GREEN}📦 Verificando dependências...${NC}"
if [ -f "web_interface/requirements.txt" ]; then
    pip install -r web_interface/requirements.txt
else
    echo -e "${YELLOW}⚠️  Arquivo requirements.txt não encontrado${NC}"
fi

# Executar migrações
echo -e "${GREEN}🗄️  Executando migrações...${NC}"
cd web_interface
python3 manage.py makemigrations
python3 manage.py migrate
cd ..

# Coletar arquivos estáticos
echo -e "${GREEN}📦 Coletando arquivos estáticos...${NC}"
cd web_interface
python3 manage.py collectstatic --noinput
cd ..

echo ""
echo -e "${GREEN}🎉 Configuração para desenvolvimento concluída!${NC}"
echo ""
echo -e "${YELLOW}📋 Para usar:${NC}"
echo "1. Execute: python3 main.py"
echo "2. Acesse: http://127.0.0.1:8000/"
echo "3. Para terminal: python3 core/main_terminal.py --help"
echo ""
echo -e "${YELLOW}🔧 Configurações aplicadas:${NC}"
echo "- DEBUG=True (desenvolvimento)"
echo "- HTTP simples (sem SSL)"
echo "- Cookies não-secure (HTTP local)"
echo "- Rate limiting desabilitado"
echo "- Logging em DEBUG"
echo ""
echo -e "${GREEN}✅ Pronto para desenvolvimento!${NC}"
