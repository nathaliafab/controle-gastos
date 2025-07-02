# controle-gastos

Sistema para unificar extratos de diferentes bancos em uma tabela única, facilitando análises posteriores.

## Bancos Suportados

- Banco do Brasil (conta corrente .csv e cartão de crédito .pdf)
- Bradesco (conta corrente .csv)
- C6 Bank (conta corrente .csv)
- Itaú (conta corrente .xls e cartão de crédito .xls)

## Uso

1. Clone o repositório:

```bash
git clone https://github.com/nathaliafab/controle-gastos.git
cd controle-gastos
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Copie o arquivo de exemplo:

```bash
cp config-exemplo.json config.json
```

4. Edite o `config.json` com suas informações:

- Atualize os nomes dos arquivos de extrato
- Preencha seu nome e CPF
- Ajuste as categorias conforme necessário

## Como Usar

1. Baixe os extratos dos bancos e coloque na pasta `extratos/`
2. Execute o processador:

```bash
python main.py
```

O relatório será gerado na pasta `output/` em formato Excel.
