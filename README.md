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

## Resultado

O sistema processa os extratos e gera uma tabela unificada com as seguintes colunas:

| Data                | Data_Contabil       | Banco           | Agencia_Conta            | Tipo_Transacao      | Descricao                     | Valor   | Valor_Entrada | Valor_Saida | Categoria_Auto   | Categoria | Descricao_Manual | Saldo_no_Banco | Saldo_Real |
| ------------------- | ------------------- | --------------- | ------------------------ | ------------------- | ----------------------------- | ------- | ------------- | ----------- | ---------------- | --------- | ---------------- | -------------- | ---------- |
| aaaa-mm-dd 00:00:00 | aaaa-mm-dd 00:00:00 | Banco do Brasil | CARD FinalXXXX           | Compra              | PG *YYYY PARC 01/02 ZZZZ (BR) | -239.58 | 0             | 239.58      | Cartão Crédito |           |                  | 8.44           | -231.14    |
| aaaa-mm-dd 00:00:00 | aaaa-mm-dd 00:00:00 | Banco do Brasil | CARD FinalXXXX           | Compra              | PG *YYYY PARC 02/02 ZZZZ (BR) | -239.58 | 0             | 239.58      | Cartão Crédito |           |                  | 8.44           | -470.72    |
| aaaa-mm-dd 00:00:00 | aaaa-mm-dd 00:00:00 | C6 Bank         | Ag: 1 / Conta: 123456789 | CREDITO OPERACAO B3 | dd/mm/aaaa                    | 0.02    | 0.02          | 0           | Investimentos    |           |                  | 8.46           | -470.70    |

**Observações:**

- Os extratos de cada banco possuem formatos diferentes, então algumas colunas podem variar. No entanto, as informações essenciais são sempre preservadas na tabela final.
- As colunas "Categoria" e "Descricao_Manual" são deixadas em branco para que o usuário possa preencher manualmente, se necessário.
- Compras no cartão de crédito e pagamentos de fatura são automaticamente classificados como "Cartão Crédito". Diferente do extrato original, as compras aparecem como saída (valor negativo) e o pagamento da fatura como entrada (valor positivo).
- Transferências entre contas de bancos diferentes (por exemplo, do Bradesco para o C6 Bank) são reconhecidas e marcadas como "Transferência Própria". Sempre haverá uma correspondência entre a saída de um banco e a entrada no outro, com o mesmo valor e data.

---

## Como Rodar

### Pré-requisitos

- Python 3.8+
- Pip (gerenciador de pacotes do Python)

### 1. Interface Web (Recomendado)

#### Setup Automático

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
- Ativar o ambiente virtual Python (venv)
- Instalar dependências da interface web (requirements.txt)
- Criar pastas obrigatórias do projeto (logs, media, staticfiles, backups)
- Gerar arquivo `.env` com configurações seguras para desenvolvimento
- Executar migrações do banco de dados Django
- Coletar arquivos estáticos da interface web
- Configurar permissões básicas dos diretórios

> **Nota:** O script é otimizado para desenvolvimento local e usa HTTP por padrão.

Em seguida, você pode executar o sistema web:

```bash
# Executar o sistema
python3 main.py
```

O sistema irá iniciar em `http://localhost:8000`

> **Primeira execução:** O sistema pode solicitar criação de usuário administrador na primeira vez.

### 2. Interface Terminal

Primeiro, instale as dependências do terminal:

```bash
# Ativar ambiente virtual (se não estiver ativo)
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências do terminal
pip install -r requirements.txt
```

Para usar via linha de comando:

```bash
# Ver opções disponíveis
python3 main.py --help

# Processar todos os extratos
python3 main.py --all

# Usar diretamente o módulo terminal
python3 core/main_terminal.py --help
```
