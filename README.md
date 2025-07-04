# controle-gastos

Sistema para unificar extratos de diferentes bancos em uma tabela única, facilitando análises posteriores.

## Features

- Processamento automático de extratos bancários
- Categorização inteligente de transações
- Identificação e filtro de transferências próprias
- Geração de gráficos Sankey interativos
- Interface web para facilitar o uso
- Suporte a múltiplos arquivos por banco
- Exportação em Excel

## Bancos Suportados

| Banco                     | Tipo de Extrato                      | Formato  |
| ------------------------- | ------------------------------------ | -------- |
| **C6 Bank**         | Conta Corrente                       | CSV      |
| **Bradesco**        | Conta Corrente                       | CSV      |
| **Banco do Brasil** | Conta Corrente                       | CSV      |
| **BB Cartão**      | Cartão de Crédito                  | PDF      |
| **Itaú**           | Conta Corrente e Cartão de Crédito | XLS/XLSX |

## Como Rodar

### Pré-requisitos

- Python 3.8+
- Pip (gerenciador de pacotes do Python)

### Setup Automático

Execute o script de configuração para desenvolvimento:

```bash
# Linux/Mac
./setup_dev.sh

# Windows (Git Bash ou WSL)
bash setup_dev.sh
```

Este script irá:

- Detectar automaticamente seu sistema operacional (Windows/Linux/Mac)
- Criar um ambiente virtual Python (venv)
- Instalar dependências da interface web (requirements-web.txt)
- Criar pastas obrigatórias do projeto (logs, media, staticfiles, backups)
- Gerar arquivo `.env` com configurações seguras para desenvolvimento
- Executar migrações do banco de dados Django
- Coletar arquivos estáticos da interface web
- Configurar permissões básicas dos diretórios

> **Nota:** O script é otimizado para desenvolvimento local e usa HTTP por padrão.

### Executar o Sistema

Após o setup, você pode executar o sistema de duas formas:

#### 1. Interface Web (Recomendado)

```bash
# Ativar ambiente virtual (se não estiver ativo)
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Executar o sistema
python3 main.py
```

O sistema irá iniciar em `http://localhost:8000`

> **Primeira execução:** O sistema pode solicitar criação de usuário administrador na primeira vez.

#### 2. Interface Terminal

Para usar via linha de comando sem interface web:

```bash
# Ver opções disponíveis
python3 main.py --help

# Processar todos os extratos
python3 main.py --all

# Usar diretamente o módulo terminal
python3 core/main_terminal.py --help
```
