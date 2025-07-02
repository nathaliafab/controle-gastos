import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import sys
from pathlib import Path
import argparse

def gerar_sankey_por_banco(df_banco, nome_banco, output_dir):
    """
    Gera um gráfico Sankey para um banco específico, mostrando suas receitas e despesas.
    O fluxo é: Origem (Receitas do Banco) -> Receita Detalhada -> Dinheiro Disponível (no Banco) -> Despesa Detalhada.
    As colunas são visivelmente distintas.
    """
    nodes_labels = []
    node_map = {}
    current_node_id = 0
    node_x_positions = []

    def add_node_with_pos(label, x_pos):
        nonlocal current_node_id
        if label not in node_map:
            node_map[label] = current_node_id
            nodes_labels.append(label)
            node_x_positions.append(x_pos)
            current_node_id += 1
        return node_map[label]

    sources = []
    targets = []
    values = []
    link_labels = []

    # Definindo as posições X para as 4 colunas visuais no gráfico por banco
    X_COL1 = 0.02  # Origem (Receitas do Banco)
    X_COL2 = 0.28  # Receita Detalhada
    X_COL3 = 0.54  # Dinheiro Disponível (no Banco)
    X_COL4 = 0.80  # Despesa Detalhada

    # Adicionar nós fixos e de colunas para este banco
    origem_receitas_banco_node_id = add_node_with_pos(f'Origem (Receitas do {nome_banco})', X_COL1) # Coluna 1
    dinheiro_disponivel_banco_node_id = add_node_with_pos(f'Dinheiro Disponível (no {nome_banco})', X_COL3) # Coluna 3

    # Pré-popular nós de Receita Detalhada (Coluna 2)
    for tipo_receita in df_banco[df_banco['Valor'] > 0]['Tipo_Transacao_AltoNivel'].unique():
        add_node_with_pos(f"Receita Detalhada: {tipo_receita}", X_COL2)
    for detalhe_provento in df_banco[df_banco['Valor'] > 0]['Tipo_Transacao_Detalhe'].unique():
        if detalhe_provento != '' and detalhe_provento != 'nan':
            add_node_with_pos(f"Detalhe Provento: {detalhe_provento}", X_COL2)
    
    # Pré-popular nós de Despesa Detalhada (Coluna 4)
    for categoria_despesa in df_banco[df_banco['Valor'] < 0]['Categoria_Agrupada'].unique():
        add_node_with_pos(f"Despesa Detalhada: {categoria_despesa}", X_COL4)

    # Processar Fluxos
    for _, row in df_banco.iterrows():
        if row['Valor'] > 0: # É uma Receita
            receita_alto_nivel_label = f"Receita Detalhada: {row['Tipo_Transacao_AltoNivel']}"
            receita_alto_nivel_node_id = node_map[receita_alto_nivel_label]

            # Link 1: Origem (Receitas do Banco) -> Receita Detalhada (Coluna 1 -> Coluna 2)
            sources.append(origem_receitas_banco_node_id)
            targets.append(receita_alto_nivel_node_id)
            values.append(row['Valor'])
            link_labels.append(f"Origem para {row['Tipo_Transacao_AltoNivel']}: R${row['Valor']:.2f}")

            # Se for "Proventos de Renda Variável", ramifica para o detalhe (Coluna 2 -> Coluna 2)
            if row['Tipo_Transacao_AltoNivel'] == 'Proventos de Renda Variável' and row['Tipo_Transacao_Detalhe'] != '' and row['Tipo_Transacao_Detalhe'] != 'nan':
                detalhe_provento_label = f"Detalhe Provento: {row['Tipo_Transacao_Detalhe']}"
                detalhe_provento_node_id = node_map[detalhe_provento_label]

                # Link: Receita Detalhada (Proventos) -> Detalhe Provento
                sources.append(receita_alto_nivel_node_id)
                targets.append(detalhe_provento_node_id)
                values.append(row['Valor'])
                link_labels.append(f"Proventos para {row['Tipo_Transacao_Detalhe']}: R${row['Valor']:.2f}")
                
                # Link: Detalhe Provento -> Dinheiro Disponível (no Banco) (Coluna 2 -> Coluna 3)
                sources.append(detalhe_provento_node_id)
                targets.append(dinheiro_disponivel_banco_node_id)
                values.append(row['Valor'])
                link_labels.append(f"{row['Tipo_Transacao_Detalhe']} para Dinheiro Disponível: R${row['Valor']:.2f}")
            else:
                # Link: Receita Detalhada -> Dinheiro Disponível (no Banco) (Coluna 2 -> Coluna 3)
                sources.append(receita_alto_nivel_node_id)
                targets.append(dinheiro_disponivel_banco_node_id)
                values.append(row['Valor'])
                link_labels.append(f"{row['Tipo_Transacao_AltoNivel']} para Dinheiro Disponível: R${row['Valor']:.2f}")

        else: # É uma Despesa (Valor < 0)
            despesa_categoria_label = f"Despesa Detalhada: {row['Categoria_Agrupada']}"
            despesa_categoria_node_id = node_map[despesa_categoria_label]

            # Link 1: Dinheiro Disponível (no Banco) -> Despesa Detalhada (Coluna 3 -> Coluna 4)
            sources.append(dinheiro_disponivel_banco_node_id)
            targets.append(despesa_categoria_node_id)
            values.append(abs(row['Valor']))
            link_labels.append(f"Dinheiro Disponível para {row['Categoria_Agrupada']}: R${abs(row['Valor']):.2f}")


    if not sources or not targets:
        print(f"Nenhum fluxo de dados válido encontrado para gerar o gráfico Sankey para o banco '{nome_banco}'.")
        return

    # --- Cores e Ícones para os Nós ---
    cores_nos = []
    node_icons = {
        'Origem (Receitas do ': '💰',
        'Receita Detalhada:': '📊',
        'Detalhe Provento:': '📈',
        'Dinheiro Disponível (no ': '💼',
        'Despesa Detalhada:': '💸',
    }

    # Calcular totais para cada nó para exibir no label
    node_totals = {}
    for i, label in enumerate(nodes_labels):
        total_incoming = sum(values[j] for j, target_node_id in enumerate(targets) if target_node_id == i)
        total_outgoing = sum(values[j] for j, source_node_id in enumerate(sources) if source_node_id == i)

        if label.startswith('Origem (Receitas do '):
            node_totals[i] = total_outgoing
        elif label.startswith('Dinheiro Disponível (no '):
            node_totals[i] = total_incoming # Dinheiro disponível recebe das receitas e envia para despesas
        else: # Para todos os outros nós (detalhamentos de receita e despesa)
            node_totals[i] = total_incoming

    final_nodes_labels = []
    for i, label in enumerate(nodes_labels):
        icon = ''
        for key, val in node_icons.items():
            if label.startswith(key):
                icon = val
                break
        
        # Cor para os nós
        if label.startswith('Origem (Receitas do '):
            cores_nos.append('rgba(39, 174, 96, 0.9)') # Verde escuro
        elif 'Receita Detalhada:' in label:
            cores_nos.append('rgba(46, 204, 113, 0.9)') # Verde claro
        elif 'Detalhe Provento:' in label:
            cores_nos.append('rgba(39, 174, 96, 0.7)') # Verde mais claro
        elif label.startswith('Dinheiro Disponível (no '):
            cores_nos.append('rgba(52, 73, 94, 0.9)') # Azul escuro/cinza
        elif 'Despesa Detalhada:' in label:
            cores_nos.append('rgba(231, 76, 60, 0.9)') # Vermelho
        else:
            cores_nos.append('skyblue') # Fallback

        final_nodes_labels.append(f"{icon} {label}<br>R$ {node_totals.get(i, 0):,.0f}")

    # Cores para os links baseadas na categoria de destino
    cores_links = []
    for i in range(len(sources)):
        target_node_label = nodes_labels[targets[i]]
        if 'Receita Detalhada:' in target_node_label or 'Detalhe Provento:' in target_node_label:
            cores_links.append('rgba(46, 204, 113, 0.3)') # Verde transparente (Origem para Receita Detalhada)
        elif target_node_label.startswith('Dinheiro Disponível (no '):
            cores_links.append('rgba(46, 204, 113, 0.3)') # Verde transparente (Receita Detalhada para Dinheiro Disponível)
        elif 'Despesa Detalhada:' in target_node_label:
            cores_links.append('rgba(231, 76, 60, 0.3)') # Vermelho transparente (Dinheiro Disponível para Despesa Detalhada)
        else:
            cores_links.append('rgba(149, 165, 166, 0.3)') # Cinza transparente fallback

    # Criar o gráfico Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=50, # Aumentado para maior espaçamento vertical entre os nós
            thickness=55, # Aumentado para nós mais "grossos"
            line=dict(color="rgba(0,0,0,0.8)", width=2),
            label=final_nodes_labels,
            color=cores_nos,
            x=node_x_positions,
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=cores_links,
            hovertemplate='%{source.label} → %{target.label}<br><b>R$ %{value:,.2f}</b><extra></extra>'
        )
    )])

    total_saidas_banco = abs(df_banco[df_banco['Valor'] < 0]['Valor'].sum())
    total_entradas_banco = df_banco[df_banco['Valor'] > 0]['Valor'].sum()
    saldo_banco = total_entradas_banco - total_saidas_banco
    
    cor_saldo = '#27ae60' if saldo_banco >= 0 else '#e74c3c'
    simbolo_saldo = '+' if saldo_banco >= 0 else ''

    fig.update_layout(
        title={
            'text': f"💰 Fluxo de Receitas e Despesas - {nome_banco}<br><span style='font-size:14px; color:#7f8c8d'>💸 Saídas Totais: R$ {abs(total_saidas_banco):,.2f} | 💵 Entradas Totais: R$ {total_entradas_banco:,.2f} | <span style='color:{cor_saldo}'>💼 Saldo: {simbolo_saldo}R$ {saldo_banco:,.2f}</span></span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50'}
        },
        font=dict(size=13, family="Arial", color='#2c3e50'),
        height=700,
        width=1200,
        margin=dict(t=100, l=50, r=50, b=50),
        paper_bgcolor='#f8f9fa',
        plot_bgcolor='#f8f9fa'
    )

    pio.templates.default = "plotly_white"

    output_file_html = Path(output_dir) / f"analise_gastos_sankey_{nome_banco.replace(' ', '_').lower()}.html"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fig.write_html(output_file_html, include_plotlyjs='cdn')

    print(f"Gráfico Sankey para '{nome_banco}' gerado com sucesso em '{output_file_html}'")
    print(f"💵 Total de Entradas ({nome_banco}): R$ {total_entradas_banco:,.2f}")
    print(f"💸 Total de Saídas ({nome_banco}): R$ {abs(total_saidas_banco):,.2f}")
    print(f"💼 Saldo Final ({nome_banco}): {simbolo_saldo}R$ {saldo_banco:,.2f}")


def gerar_sankey_geral(df_final, output_dir):
    """
    Gera um gráfico Sankey geral, mostrando o fluxo Receita -> Bancos -> Despesas.
    """
    nodes_labels = []
    node_map = {}
    current_node_id = 0
    node_x_positions = []

    def add_node_with_pos(label, x_pos):
        nonlocal current_node_id
        if label not in node_map:
            node_map[label] = current_node_id
            nodes_labels.append(label)
            node_x_positions.append(x_pos)
            current_node_id += 1
        return node_map[label]

    sources = []
    targets = []
    values = []
    link_labels = []

    # Definindo as posições X para as 3 colunas visuais
    X_COL1 = 0.05 # Receita Total
    X_COL2 = 0.40 # Bancos
    X_COL3 = 0.75 # Despesas

    # Adicionar nó de Receita Total (Coluna 1)
    receita_total_node_id = add_node_with_pos('Receita Total', X_COL1)

    # Pré-popular nós de bancos (Coluna 2)
    for banco in df_final['Banco'].unique():
        add_node_with_pos(f"Banco: {banco}", X_COL2)

    # Pré-popular nós de despesas (Coluna 3)
    for categoria_despesa in df_final[df_final['Valor'] < 0]['Categoria_Agrupada'].unique():
        add_node_with_pos(f"Despesa: {categoria_despesa}", X_COL3)

    # --- Links ---

    # 1. Receita Total -> Bancos
    df_receitas_por_banco = df_final[df_final['Valor'] > 0].groupby('Banco')['Valor'].sum().reset_index()
    for _, row_banco in df_receitas_por_banco.iterrows():
        banco_label = f"Banco: {row_banco['Banco']}"
        if banco_label in node_map: # Garante que o nó do banco existe
            banco_node_id = node_map[banco_label]
            sources.append(receita_total_node_id)
            targets.append(banco_node_id)
            values.append(row_banco['Valor'])
            link_labels.append(f"Receita Total para {row_banco['Banco']}: R${row_banco['Valor']:.2f}")

    # 2. Bancos -> Despesas
    df_despesas_por_banco_categoria = df_final[df_final['Valor'] < 0].groupby(['Banco', 'Categoria_Agrupada'])['Valor'].sum().reset_index()
    for _, row_desp in df_despesas_por_banco_categoria.iterrows():
        banco_label = f"Banco: {row_desp['Banco']}"
        despesa_categoria_label = f"Despesa: {row_desp['Categoria_Agrupada']}"
        
        if banco_label in node_map and despesa_categoria_label in node_map: # Garante que os nós existam
            banco_node_id = node_map[banco_label]
            despesa_categoria_node_id = node_map[despesa_categoria_label]
            sources.append(banco_node_id)
            targets.append(despesa_categoria_node_id)
            values.append(abs(row_desp['Valor']))
            link_labels.append(f"{row_desp['Banco']} para {row_desp['Categoria_Agrupada']}: R${abs(row_desp['Valor']):.2f}")

    if not sources or not targets:
        print(f"Nenhum fluxo de dados válido encontrado para gerar o gráfico Sankey geral.")
        return

    # --- Cores e Ícones para os Nós ---
    cores_nos = []
    node_icons = {
        'Receita Total': '💰',
        'Banco:': '🏦',
        'Despesa:': '💸',
    }

    # Calcular totais para cada nó para exibir no label
    node_totals = {}
    for i, label in enumerate(nodes_labels):
        total_incoming = sum(values[j] for j, target_node_id in enumerate(targets) if target_node_id == i)
        total_outgoing = sum(values[j] for j, source_node_id in enumerate(sources) if source_node_id == i)

        if label == 'Receita Total':
            node_totals[i] = total_outgoing
        else:
            node_totals[i] = total_incoming

    final_nodes_labels = []
    for i, label in enumerate(nodes_labels):
        icon = ''
        for key, val in node_icons.items():
            if label.startswith(key):
                icon = val
                break
        
        # Cor para os nós
        if 'Receita Total' in label:
            cores_nos.append('rgba(39, 174, 96, 0.9)') # Verde escuro
        elif 'Banco:' in label:
            cores_nos.append('rgba(41, 128, 185, 0.9)') # Azul
        elif 'Despesa:' in label:
            cores_nos.append('rgba(231, 76, 60, 0.9)') # Vermelho
        else:
            cores_nos.append('skyblue') # Fallback

        final_nodes_labels.append(f"{icon} {label}<br>R$ {node_totals.get(i, 0):,.0f}")

    # Cores para os links
    cores_links = []
    for i in range(len(sources)):
        target_node_label = nodes_labels[targets[i]]
        if 'Banco:' in target_node_label:
            cores_links.append('rgba(46, 204, 113, 0.3)') # Verde transparente (receita para banco)
        elif 'Despesa:' in target_node_label:
            cores_links.append('rgba(231, 76, 60, 0.3)') # Vermelho transparente (banco para despesa)
        else:
            cores_links.append('rgba(149, 165, 166, 0.3)') # Cinza transparente fallback

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=40,
            thickness=45,
            line=dict(color="rgba(0,0,0,0.8)", width=2),
            label=final_nodes_labels,
            color=cores_nos,
            x=node_x_positions,
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=cores_links,
            hovertemplate='%{source.label} → %{target.label}<br><b>R$ %{value:,.2f}</b><extra></extra>'
        )
    )])

    total_saidas = abs(df_final[df_final['Valor'] < 0]['Valor'].sum())
    total_entradas = df_final[df_final['Valor'] > 0]['Valor'].sum()
    saldo = total_entradas - total_saidas
    
    cor_saldo = '#27ae60' if saldo >= 0 else '#e74c3c'
    simbolo_saldo = '+' if saldo >= 0 else ''

    fig.update_layout(
        title={
            'text': f"💰 Fluxo Geral de Receitas e Despesas<br><span style='font-size:14px; color:#7f8c8d'>💸 Saídas Totais: R$ {abs(total_saidas):,.2f} | 💵 Entradas Totais: R$ {total_entradas:,.2f} | <span style='color:{cor_saldo}'>💼 Saldo: {simbolo_saldo}R$ {saldo:,.2f}</span></span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50'}
        },
        font=dict(size=13, family="Arial", color='#2c3e50'),
        height=700,
        width=1200,
        margin=dict(t=100, l=50, r=50, b=50),
        paper_bgcolor='#f8f9fa',
        plot_bgcolor='#f8f9fa'
    )

    pio.templates.default = "plotly_white"

    output_file_html = Path(output_dir) / "analise_gastos_sankey_geral.html"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fig.write_html(output_file_html, include_plotlyjs='cdn')

    print(f"Gráfico Sankey Geral gerado com sucesso em '{output_file_html}'")
    print(f"💵 Total de Entradas (Geral): R$ {total_entradas:,.2f}")
    print(f"💸 Total de Saídas (Geral): R$ {abs(total_saidas):,.2f}")
    print(f"💼 Saldo Final (Geral): {simbolo_saldo}R$ {saldo:,.2f}")


def analisar_gastos_sankey_proventos_detalhados(nome_arquivo_excel="controle_gastos.xlsx", output_dir="output"):
    """
    Lê um arquivo Excel de controle de gastos, identifica receitas e despesas,
    aplica categorizações específicas (com proventos detalhados em 3 colunas de receita),
    ignora transferências próprias, e gera arquivos HTML com gráficos Sankey:
    - Um para CADA BANCO (Banco -> Receita (geral) -> Detalhamentos -> Despesa Final).
    - Um GERAL (Receita Total -> Bancos -> Despesas).
    """
    try:
        df = pd.read_excel(nome_arquivo_excel)

        df['Valor'] = pd.to_numeric(df['Valor'].fillna(0))
        df['Banco'] = df['Banco'].astype(str)
        df['Tipo_Transacao'] = df['Tipo_Transacao'].astype(str)
        df['Descricao'] = df['Descricao'].astype(str)
        df['Categoria_Auto'] = df['Categoria_Auto'].astype(str)
        df['Categoria'] = df['Categoria'].astype(str)

        df['Tipo_Transacao_Upper'] = df['Tipo_Transacao'].str.upper().fillna('')
        df['Descricao_Upper'] = df['Descricao'].str.upper().fillna('')
        df['Categoria_Auto_Upper'] = df['Categoria_Auto'].str.upper().fillna('')
        df['Categoria_Upper'] = df['Categoria'].str.upper().fillna('')

        cond_transferencia_propria = \
            (df['Tipo_Transacao_Upper'].str.contains("TRANSFERÊNCIA PRÓPRIA")) | \
            (df['Descricao_Upper'].str.contains("TRANSFERÊNCIA PRÓPRIA")) | \
            (df['Categoria_Auto_Upper'].str.contains("TRANSFERÊNCIA PRÓPRIA")) | \
            (df['Categoria_Upper'].str.contains("TRANSFERÊNCIA PRÓPRIA"))

        df_processado = df[~cond_transferencia_propria].copy()

        if df_processado.empty:
            print("Após filtrar as transferências próprias, não há dados válidos para gerar o gráfico.")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            with open(Path(output_dir) / "nenhum_dado_valido.html", "w") as f:
                f.write("<html><body><h1>Não há dados válidos para gerar o gráfico após a filtragem de transferências próprias.</h1></body></html>")
            return

        df_processado['Tipo_Transacao_AltoNivel'] = df_processado['Tipo_Transacao']
        df_processado['Tipo_Transacao_Detalhe'] = ''
        df_processado['Categoria_Agrupada'] = df_processado['Categoria_Auto']

        # --- Regras para RECEITAS (Valor > 0) ---
        df_receitas_temp = df_processado[df_processado['Valor'] > 0].copy()
        cond_proventos = (df_receitas_temp['Descricao_Upper'].str.contains("COR RENDIMENTO|COR JSCP")) | \
                         (df_receitas_temp['Tipo_Transacao_Upper'].str.contains("COR RENDIMENTO|COR JSCP"))
        df_receitas_temp.loc[cond_proventos, 'Tipo_Transacao_AltoNivel'] = 'Proventos de Renda Variável'
        df_receitas_temp.loc[cond_proventos, 'Tipo_Transacao_Detalhe'] = \
            df_receitas_temp.loc[cond_proventos].apply(
                lambda row: row['Descricao'] if row['Descricao'] != 'nan' and row['Descricao'] != '' else row['Tipo_Transacao'],
                axis=1
            )
        cond_pix_rec = (df_receitas_temp['Descricao_Upper'].str.contains("PIX")) | \
                       (df_receitas_temp['Tipo_Transacao_Upper'].str.contains("PIX")) | \
                       (df_receitas_temp['Categoria_Auto_Upper'].str.contains("PIX"))
        df_receitas_temp.loc[cond_pix_rec & (~cond_proventos), 'Tipo_Transacao_AltoNivel'] = 'PIX (Receita)'

        # --- Regras para DESPESAS (Valor < 0) ---
        df_despesas_temp = df_processado[df_processado['Valor'] < 0].copy()
        def get_expense_category(row):
            desc_upper = row['Descricao_Upper']
            tipo_trans_upper = row['Tipo_Transacao_Upper']
            cat_auto_upper = row['Categoria_Auto_Upper']
            if "COR OPERACOES B3" in desc_upper: return 'Investimentos em Bolsa'
            if "APLICACAO CDB COFRINHOS" in desc_upper: return 'Investimentos CDB Cofrinho'
            if ("ITAU VISA" in desc_upper or "ITAU BLACK" in desc_upper) or \
               ("ITAU VISA" in tipo_trans_upper or "ITAU BLACK" in tipo_trans_upper): return 'Despesas Cartão de Crédito'
            if ("PIX" in desc_upper or "PIX" in tipo_trans_upper or "PIX" in cat_auto_upper): return 'PIX (Despesa)'
            if 'CARTAO CREDITO' in cat_auto_upper or 'CARTAO CREDITO' in desc_upper or 'CARTAO CREDITO' in tipo_trans_upper: return 'Cartão Crédito (Geral)'
            if 'CARTAO DEBITO' in cat_auto_upper or 'CARTAO DEBITO' in desc_upper or 'CARTAO DEBITO' in tipo_trans_upper: return 'Cartão Débito'
            if 'INVESTIMENTO' in cat_auto_upper or 'INVESTIMENTO' in desc_upper or 'INVESTIMENTO' in tipo_trans_upper: return 'Investimentos (Geral)'
            if row['Categoria_Auto'] != 'nan' and row['Categoria_Auto'] != '': return row['Categoria_Auto']
            return 'Outros'
        df_despesas_temp['Categoria_Agrupada'] = df_despesas_temp.apply(get_expense_category, axis=1)

        df_final = pd.concat([df_receitas_temp, df_despesas_temp]).sort_index()

        # Gerar um Sankey para cada banco
        unique_bancos = df_final['Banco'].unique()
        if len(unique_bancos) == 0:
            print("Nenhum banco encontrado nos dados processados para gerar gráficos.")
            return

        for banco in unique_bancos:
            df_banco_filtered = df_final[df_final['Banco'] == banco].copy()
            if not df_banco_filtered.empty:
                gerar_sankey_por_banco(df_banco_filtered, banco, output_dir)
            else:
                print(f"Nenhum dado válido para o banco '{banco}' após a filtragem de transferências próprias e categorização.")

        # Gerar o Sankey geral
        gerar_sankey_geral(df_final, output_dir)

        print("\nAnálise Sankey por banco e geral concluída!")
        print(f"💡 Dica: Verifique a pasta '{output_dir}' para os arquivos HTML gerados.")


    except FileNotFoundError:
        print(f"Erro: O arquivo '{nome_arquivo_excel}' não foi encontrado. Certifique-se de que ele está no mesmo diretório do script.")
        sys.exit(1)
    except KeyError as e:
        print(f"Erro: Coluna '{e}' não encontrada no arquivo Excel. Verifique a estrutura das colunas e se os nomes estão corretos.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}: {e.__class__}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gerador de Gráfico Sankey para Análise de Gastos com Proventos Detalhados por Banco e um Gráfico Geral.')
    parser.add_argument('--excel', type=str, default='controle_gastos.xlsx',
                        help='Caminho para o arquivo Excel de controle de gastos (padrão: controle_gastos.xlsx)')
    parser.add_argument('--output_dir', type=str, default='output',
                        help='Diretório de saída para os arquivos HTML gerados (padrão: output)')
    
    args = parser.parse_args()
    
    analisar_gastos_sankey_proventos_detalhados(nome_arquivo_excel=args.excel, output_dir=args.output_dir)
