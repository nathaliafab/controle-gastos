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

### Instalação das Dependências

```bash
pip install -r requirements.txt
pip install -r web_interface/requirements-web.txt
```

### Configurar Banco de Dados (primeira vez)

```bash
echo "export SECRET_KEY='$(openssl rand -hex 40)'" > .DJANGO_SECRET_KEY
source .DJANGO_SECRET_KEY
cd web_interface
python3 manage.py makemigrations
python3 manage.py migrate
cd ..
```

### Executar o Sistema

#### Interface Web (Padrão)

Simplesmente execute o arquivo principal:

```bash
python3 main.py
```

O sistema irá:

1. Detectar automaticamente se o Django está instalado
2. Executar migrações do banco de dados
3. Iniciar o servidor web em `http://localhost:8000`

#### Interface Terminal

Para usar via linha de comando:

```bash
python3 main.py --help
```

Exemplo de uso:

```bash
python3 main.py --all
```

Ou diretamente:

```bash
python3 core/main_terminal.py --all
```
