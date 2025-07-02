import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import sys
from pathlib import Path
import argparse

def criar_descricao_completa(row):
    """Une Tipo_Transacao e Descricao em uma única string para análise."""
    tipo = str(row['Tipo_Transacao']).strip() if pd.notna(row['Tipo_Transacao']) else ''
    desc = str(row['Descricao']).strip() if pd.notna(row['Descricao']) else ''
    
    # Remove valores 'nan' como string
    if tipo.lower() == 'nan':
        tipo = ''
    if desc.lower() == 'nan':
        desc = ''
    
    # Une com separador se ambos existirem
    if tipo and desc:
        return f"{tipo} | {desc}"
    elif tipo:
        return tipo
    elif desc:
        return desc
    else:
        return ''

def categorizar_receitas_por_palavras_chave(texto_completo):
    """Categoriza receitas baseado em palavras-chave na descrição completa."""
    if not texto_completo:
        return 'Receita Não Categorizada', ''
    
    texto_upper = texto_completo.upper()
    
    # Categorização de receitas por ordem de prioridade
    categorias_receitas = {
        # Salário e Proventos
        '💼 Salário e Proventos': ['REMUNERACAO', 'SALARIO', 'PROVENTO', 'VENCIMENTO', 'FOLHA'],
        '🔄 Estornos e Devoluções': ['ESTORNO', 'EST ', 'DEVOLUCAO', 'REEMBOLSO'],
        '💳 Cashback e Créditos': ['PAGAMENTO/CRÉDITO', 'CARTAO CREDITO', 'CREDITO CARTAO', 'COMPRA CARTAO', 'CASHBACK', 'RECOMPENSA'],
        
        # Investimentos - Resgates
        '🥇 Resgate - Ourocap': ['OUROCAP', 'RESGATE OUROCAP'],
        '📈 Resgate - Ações B3': ['B3', 'ACAO', 'ACOES', 'VENDA ACAO', 'LIQUIDACAO VENDA'],
        '🏦 Resgate - CDB': ['RESGATE DE CDB', 'RESGATE CDB', 'CDB'],
        '🏠 Resgate - LCI/LCA': ['RESGATE LCI', 'RESGATE LCA', 'LCI', 'LCA'],
        '🏛️ Resgate - Tesouro': ['RESGATE TESOURO', 'TESOURO'],
        '📊 Resgate - Fundos': ['RESGATE FUNDO', 'FUNDO'],
        '💎 Resgate - Outros Ativos': ['RESGATE ATIVO', 'ATIVO'],
        '💰 Resgates Diversos': ['RESGATE'],
        
        # Rendimentos
        '💶 Juros sobre Capital': ['JSCP', 'JCP', 'JUROS'],
        '💷 Rendimentos': ['RENDIMENTO', 'DIVIDENDO', 'DIV'],
        
        # Transferências Recebidas
        '📱 PIX Recebido': ['PIX'],
        '📥 Transferências Recebidas': ['TRANSFERENCIA', 'TED', 'DOC'],
        
        # Outros
        '💳 Depósitos em Conta': ['DEPOSITO', 'CREDITO EM CONTA'],
        '💰 Outros Créditos': ['CREDITO', 'APORTE']
    }
    
    # Verifica cada categoria mantendo ordem de prioridade
    for categoria, palavras in categorias_receitas.items():
        for palavra in palavras:
            if palavra in texto_upper:
                return categoria, texto_completo
    
    return 'Receita Não Categorizada', ''

def categorizar_despesas_por_palavras_chave(texto_completo, categoria_auto=''):
    """Categoriza despesas baseado em palavras-chave na descrição completa."""
    if not texto_completo:
        return 'Despesa Não Categorizada'
    
    texto_upper = texto_completo.upper()
    cat_auto_upper = str(categoria_auto).upper() if categoria_auto else ''
    
    # Categorização de despesas por ordem de prioridade
    categorias_despesas = {
        # Investimentos - Aplicações
        '🏦 Investimento - CDB': ['APLICACAO CDB', 'CDB'],
        '🏠 Investimento - LCI/LCA': ['APLICACAO LCI', 'APLICACAO LCA', 'LCI', 'LCA'],
        '🏛️ Investimento - Tesouro': ['APLICACAO TESOURO', 'TESOURO'],
        '📊 Investimento - Fundos': ['APLICACAO FUNDO', 'FUNDO'],
        '🥇 Investimento - Ourocap': ['OUROCAP', 'APLICACAO OUROCAP'],
        '💰 Investimentos Diversos': ['APLICACAO'],
        '📈 Investimento - Ações B3': ['B3', 'ACAO', 'ACOES', 'COMPRA ACAO', 'LIQUIDACAO COMPRA'],
        '💎 Investimento - Outros': ['ATIVO'],
        
        # Cartões e Débitos
        '💳 Cartão de Crédito': ['CARTAO CREDITO', 'CREDITO CARTAO', 'COMPRA CARTAO'],
        '💳 Cartão de Débito': ['CARTAO DEBITO', 'DEBITO CARTAO', 'DEBITO DE CARTAO'],
        '⚡ Débito Automático': ['DEBITO AUTOMATICO'],
        
        # Transferências e PIX
        '📱 PIX Enviado': ['PIX'],
        '📤 Transferências Enviadas': ['TRANSFERENCIA', 'TED', 'DOC'],
        
        # Tarifas e Saques
        '🏦 Tarifas Bancárias': ['TARIFA', 'TAXA', 'IOF', 'ANUIDADE', 'MANUTENCAO'],
        '💸 Saques': ['SAQUE', 'RETIRADA'],
        
        # Categorias de Vida
        '🍽️ Alimentação': ['SUPERMERCADO', 'RESTAURANTE', 'LANCHONETE', 'PADARIA', 'IFOOD', 'DELIVERY', 'MERCADO'],
        '🚗 Transporte': ['COMBUSTIVEL', 'POSTO', 'UBER', '99', 'GASOLINA', 'ALCOOL', 'TAXI'],
        '🏥 Saúde': ['FARMACIA', 'HOSPITAL', 'CLINICA', 'MEDICO', 'MEDICAMENTO'],
        '📚 Educação': ['ESCOLA', 'FACULDADE', 'CURSO', 'MENSALIDADE'],
        '🎬 Lazer': ['CINEMA', 'TEATRO', 'STREAMING', 'NETFLIX', 'SPOTIFY'],
        '⚡ Utilidades': ['LUZ', 'AGUA', 'GAS', 'INTERNET', 'TELEFONE', 'CELULAR'],
        '👕 Vestuário': ['ROUPA', 'CALCADO', 'VESTUARIO'],
        '🏠 Casa': ['CASA', 'DECORACAO', 'ELETRODOMESTICO', 'MOBILIA']
    }
    
    # Verifica cada categoria mantendo ordem de prioridade
    for categoria, palavras in categorias_despesas.items():
        for palavra in palavras:
            if palavra in texto_upper:
                return categoria
    
    # Se tem categoria automática válida, usa ela
    if cat_auto_upper and cat_auto_upper not in ['NAN', '']:
        categoria_limpa = categoria_auto.replace('_', ' ').title()
        return categoria_limpa
    
    return 'Outras Despesas'

def filtrar_transacoes_validas(df):
    """Filtra transações removendo valores zerados e dados inválidos."""
    df_filtrado = df[abs(df['Valor']) > 1.0].copy()
    df_filtrado = df_filtrado.dropna(subset=['Banco', 'Valor'])
    
    return df_filtrado

def limpar_nome_no(nome_completo):
    """Remove prefixos dos nomes dos nós para menor poluição visual."""
    prefixos = ["Banco: ", "Receita Detalhada: ", "Despesa Detalhada: ", "Detalhe Provento: ", "Despesa: "]
    
    nome_limpo = nome_completo
    for prefixo in prefixos:
        if nome_limpo.startswith(prefixo):
            nome_limpo = nome_limpo[len(prefixo):]
            break
    
    # Caso especial para nome muito longo
    if nome_limpo.startswith("Dinheiro Disponível (no "):
        return "Disponível"
    
    return nome_limpo

def configurar_nos_e_cores(nodes_labels, sources, targets, values):
    """Configura cores, ícones e labels dos nós."""
    node_icons = {
        'Banco:': '🏦',
        'Receita Detalhada:': '💵',
        'Detalhe Provento:': '📈',
        'Dinheiro Disponível (no ': '💼',
        'Despesa Detalhada:': '💸',
        'Receita Total': '💰',
        'Despesa:': '💸'
    }
    
    cores_nos = []
    node_totals = {}
    
    # Calcular totais para cada nó
    for i, label in enumerate(nodes_labels):
        total_incoming = sum(values[j] for j, target_id in enumerate(targets) if target_id == i)
        total_outgoing = sum(values[j] for j, source_id in enumerate(sources) if source_id == i)
        
        if label == 'Receita Total':
            # Receita Total: mostra o que sai (total de receitas)
            node_totals[i] = total_outgoing
        elif label.startswith('Banco:'):
            # Bancos no gráfico individual: sempre mostra outgoing (total de receitas geradas)
            # Bancos no gráfico geral: armazena tanto incoming quanto outgoing
            # Detecta se é gráfico geral pela presença de "Receita Total"
            is_geral = any('Receita Total' in l for l in nodes_labels)
            if is_geral:
                # No gráfico geral, armazenamos ambos os valores
                node_totals[i] = {'incoming': total_incoming, 'outgoing': total_outgoing}
            else:
                node_totals[i] = total_outgoing  # Gráfico individual: mostra receitas geradas
        elif label.startswith('Dinheiro Disponível (no '):
            # Dinheiro Disponível: mostra o que entra (receitas)
            node_totals[i] = total_incoming
        else:
            # Receitas Detalhadas e Despesas: mostra o que entra
            node_totals[i] = total_incoming
    
    # Configurar cores e labels finais
    final_nodes_labels = []
    for i, label in enumerate(nodes_labels):
        nome_limpo = limpar_nome_no(label)
        
        # Encontrar ícone
        icon = ''
        for key, val in node_icons.items():
            if label.startswith(key):
                icon = val
                break
        
        # Definir cor
        if 'Banco:' in label:
            cores_nos.append('rgba(41, 128, 185, 0.9)')  # Azul
        elif 'Receita Total' in label or 'Receita Detalhada:' in label:
            cores_nos.append('rgba(46, 204, 113, 0.9)')  # Verde
        elif 'Detalhe Provento:' in label:
            cores_nos.append('rgba(39, 174, 96, 0.7)')  # Verde claro
        elif label.startswith('Dinheiro Disponível (no '):
            cores_nos.append('rgba(52, 73, 94, 0.9)')  # Cinza escuro
        elif 'Despesa' in label:
            cores_nos.append('rgba(231, 76, 60, 0.9)')  # Vermelho
        else:
            cores_nos.append('skyblue')  # Fallback
        
        # Criar o label final do nó
        if label.startswith('Banco:') and isinstance(node_totals.get(i), dict):
            # Banco no gráfico geral - mostra entrada e saída
            incoming = node_totals[i]['incoming']
            outgoing = node_totals[i]['outgoing']
            final_nodes_labels.append(f"{icon} {nome_limpo}<br>Entrou: R$ {incoming:,.0f}<br>Saiu: R$ {outgoing:,.0f}")
        else:
            # Outros nós ou banco individual - mostra apenas um valor
            valor = node_totals.get(i, 0)
            if isinstance(valor, dict):
                valor = valor['incoming']  # Fallback se algo der errado
            final_nodes_labels.append(f"{icon} {nome_limpo}<br>R$ {valor:,.0f}")
    
    return final_nodes_labels, cores_nos

def configurar_cores_links(sources, targets, nodes_labels):
    """Configura cores dos links baseado no destino."""
    cores_links = []
    for i in range(len(sources)):
        target_label = nodes_labels[targets[i]]
        
        if 'Receita' in target_label or 'Detalhe Provento:' in target_label:
            cores_links.append('rgba(46, 204, 113, 0.3)')  # Verde transparente
        elif 'Banco:' in target_label:
            cores_links.append('rgba(41, 128, 185, 0.3)')  # Azul transparente
        elif 'Dinheiro Disponível' in target_label:
            cores_links.append('rgba(46, 204, 113, 0.3)')  # Verde transparente
        elif 'Despesa' in target_label:
            cores_links.append('rgba(231, 76, 60, 0.3)')  # Vermelho transparente
        else:
            cores_links.append('rgba(149, 165, 166, 0.3)')  # Cinza transparente
    
    return cores_links

def criar_grafico_sankey(sources, targets, values, nodes_labels, node_x_positions, titulo):
    """Cria o gráfico Sankey com configurações padronizadas."""
    final_nodes_labels, cores_nos = configurar_nos_e_cores(nodes_labels, sources, targets, values)
    cores_links = configurar_cores_links(sources, targets, nodes_labels)
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=50,
            thickness=55,
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
    
    fig.update_layout(
        title={
            'text': titulo,
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
    return fig

def gerar_sankey_por_banco(df_banco, nome_banco, output_dir):
    """Gera gráfico Sankey para um banco específico."""
    df_banco = filtrar_transacoes_validas(df_banco)
    
    # Configuração de posições das colunas
    X_COL1, X_COL2, X_COL3, X_COL4 = 0.02, 0.28, 0.54, 0.80
    
    # Inicialização
    nodes_labels = []
    node_map = {}
    current_node_id = 0
    node_x_positions = []
    sources, targets, values = [], [], []
    
    def add_node_with_pos(label, x_pos):
        nonlocal current_node_id
        if label not in node_map:
            node_map[label] = current_node_id
            nodes_labels.append(label)
            node_x_positions.append(x_pos)
            current_node_id += 1
        return node_map[label]
    
    # Nós principais
    banco_node_id = add_node_with_pos(f'Banco: {nome_banco}', X_COL1)
    dinheiro_node_id = add_node_with_pos(f'Dinheiro Disponível (no {nome_banco})', X_COL3)
    
    # Pré-popular nós de receitas e despesas
    for tipo_receita in df_banco[df_banco['Valor'] > 0]['Tipo_Transacao_AltoNivel'].unique():
        add_node_with_pos(f"Receita Detalhada: {tipo_receita}", X_COL2)
    
    for detalhe in df_banco[df_banco['Valor'] > 0]['Tipo_Transacao_Detalhe'].unique():
        if detalhe and detalhe != 'nan':
            add_node_with_pos(f"Detalhe Provento: {detalhe}", X_COL2)
    
    for categoria in df_banco[df_banco['Valor'] < 0]['Categoria_Agrupada'].unique():
        add_node_with_pos(f"Despesa Detalhada: {categoria}", X_COL4)
    
    # Processar fluxos
    for _, row in df_banco.iterrows():
        if abs(row['Valor']) <= 1.0:
            continue
        
        if row['Valor'] > 0:  # Receita
            receita_label = f"Receita Detalhada: {row['Tipo_Transacao_AltoNivel']}"
            receita_node_id = node_map[receita_label]
            
            # Banco -> Receita Detalhada
            sources.append(banco_node_id)
            targets.append(receita_node_id)
            values.append(row['Valor'])
            
            # Tratamento especial para Proventos de Renda Variável
            if (row['Tipo_Transacao_AltoNivel'] == 'Proventos de Renda Variável' and 
                row['Tipo_Transacao_Detalhe'] and row['Tipo_Transacao_Detalhe'] != 'nan'):
                
                detalhe_label = f"Detalhe Provento: {row['Tipo_Transacao_Detalhe']}"
                detalhe_node_id = node_map[detalhe_label]
                
                # Receita -> Detalhe
                sources.append(receita_node_id)
                targets.append(detalhe_node_id)
                values.append(row['Valor'])
                
                # Detalhe -> Dinheiro Disponível
                sources.append(detalhe_node_id)
                targets.append(dinheiro_node_id)
                values.append(row['Valor'])
            else:
                # Receita -> Dinheiro Disponível
                sources.append(receita_node_id)
                targets.append(dinheiro_node_id)
                values.append(row['Valor'])
        
        else:  # Despesa
            despesa_label = f"Despesa Detalhada: {row['Categoria_Agrupada']}"
            despesa_node_id = node_map[despesa_label]
            
            # Dinheiro Disponível -> Despesa
            sources.append(dinheiro_node_id)
            targets.append(despesa_node_id)
            values.append(abs(row['Valor']))
    
    if not sources:
        print(f"⚠️ Nenhum fluxo válido para '{nome_banco}'")
        return
    
    # Calcular totais
    total_entradas = df_banco[df_banco['Valor'] > 0]['Valor'].sum()
    total_saidas = abs(df_banco[df_banco['Valor'] < 0]['Valor'].sum())
    saldo = total_entradas - total_saidas
    
    cor_saldo = '#27ae60' if saldo >= 0 else '#e74c3c'
    simbolo_saldo = '+' if saldo >= 0 else ''
    
    titulo = (f"💰 Fluxo de Receitas e Despesas - {nome_banco}<br>"
              f"<span style='font-size:14px; color:#7f8c8d'>"
              f"💸 Saídas: R$ {total_saidas:,.2f} | 💵 Entradas: R$ {total_entradas:,.2f} | "
              f"<span style='color:{cor_saldo}'>💼 Saldo: {simbolo_saldo}R$ {saldo:,.2f}</span></span>")
    
    # Criar gráfico
    fig = criar_grafico_sankey(sources, targets, values, nodes_labels, node_x_positions, titulo)
    
    # Salvar arquivo
    output_file = Path(output_dir) / f"analise_gastos_sankey_{nome_banco.replace(' ', '_').lower()}.html"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fig.write_html(output_file, include_plotlyjs='cdn')
    
    print(f"✅ {nome_banco}: R$ {saldo:,.2f} ({output_file.name})")

def gerar_sankey_geral(df_final, output_dir):
    """Gera gráfico Sankey geral consolidado."""
    df_final = filtrar_transacoes_validas(df_final)
    
    # Configuração de posições das colunas
    X_COL1, X_COL2, X_COL3, X_COL4 = 0.02, 0.28, 0.54, 0.80
    
    # Inicialização
    nodes_labels = []
    node_map = {}
    current_node_id = 0
    node_x_positions = []
    sources, targets, values = [], [], []
    
    def add_node_with_pos(label, x_pos):
        nonlocal current_node_id
        if label not in node_map:
            node_map[label] = current_node_id
            nodes_labels.append(label)
            node_x_positions.append(x_pos)
            current_node_id += 1
        return node_map[label]
    
    # Nó principal de receita total
    receita_total_id = add_node_with_pos('Receita Total', X_COL1)
    
    # 1. Receita Total -> Receita Detalhada
    df_receitas = df_final[df_final['Valor'] > 0].copy()
    df_receitas['Detail_Label'] = df_receitas.apply(
        lambda row: (f"Detalhe Provento: {row['Tipo_Transacao_Detalhe']}" 
                    if (row['Tipo_Transacao_AltoNivel'] == 'Proventos de Renda Variável' and 
                        row['Tipo_Transacao_Detalhe'] and row['Tipo_Transacao_Detalhe'] != 'nan')
                    else f"Receita Detalhada: {row['Tipo_Transacao_AltoNivel']}"), axis=1
    )
    
    receita_agg = df_receitas.groupby('Detail_Label')['Valor'].sum().reset_index()
    receita_agg = receita_agg[receita_agg['Valor'] > 1.0]
    
    for _, row in receita_agg.iterrows():
        detalhe_id = add_node_with_pos(row['Detail_Label'], X_COL2)
        sources.append(receita_total_id)
        targets.append(detalhe_id)
        values.append(row['Valor'])
    
    # 2. Receita Detalhada -> Bancos
    banco_agg = df_receitas.groupby(['Detail_Label', 'Banco'])['Valor'].sum().reset_index()
    banco_agg = banco_agg[banco_agg['Valor'] > 1.0]
    
    for _, row in banco_agg.iterrows():
        source_id = add_node_with_pos(row['Detail_Label'], X_COL2)
        target_id = add_node_with_pos(f"Banco: {row['Banco']}", X_COL3)
        sources.append(source_id)
        targets.append(target_id)
        values.append(row['Valor'])
    
    # 3. Bancos -> Despesas
    df_despesas = df_final[df_final['Valor'] < 0].copy()
    despesa_agg = df_despesas.groupby(['Banco', 'Categoria_Agrupada'])['Valor'].sum().reset_index()
    despesa_agg = despesa_agg[abs(despesa_agg['Valor']) > 1.0]
    
    for _, row in despesa_agg.iterrows():
        banco_id = add_node_with_pos(f"Banco: {row['Banco']}", X_COL3)
        despesa_id = add_node_with_pos(f"Despesa: {row['Categoria_Agrupada']}", X_COL4)
        sources.append(banco_id)
        targets.append(despesa_id)
        values.append(abs(row['Valor']))
    
    if not sources:
        print("⚠️ Nenhum fluxo válido para o gráfico geral")
        return
    
    # Calcular totais
    total_entradas = df_final[df_final['Valor'] > 0]['Valor'].sum()
    total_saidas = abs(df_final[df_final['Valor'] < 0]['Valor'].sum())
    saldo = total_entradas - total_saidas
    
    cor_saldo = '#27ae60' if saldo >= 0 else '#e74c3c'
    simbolo_saldo = '+' if saldo >= 0 else ''
    
    titulo = (f"💰 Fluxo Geral de Receitas e Despesas<br>"
              f"<span style='font-size:14px; color:#7f8c8d'>"
              f"💸 Saídas: R$ {total_saidas:,.2f} | 💵 Entradas: R$ {total_entradas:,.2f} | "
              f"<span style='color:{cor_saldo}'>💼 Saldo: {simbolo_saldo}R$ {saldo:,.2f}</span></span>")
    
    # Criar gráfico
    fig = criar_grafico_sankey(sources, targets, values, nodes_labels, node_x_positions, titulo)
    
    # Salvar arquivo
    output_file = Path(output_dir) / "analise_gastos_sankey_geral.html"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fig.write_html(output_file, include_plotlyjs='cdn')
    
    print(f"✅ Geral: R$ {saldo:,.2f} ({output_file.name})")

def analisar_gastos_sankey_proventos_detalhados(nome_arquivo_excel="controle_gastos.xlsx", output_dir="output"):
    """
    Função principal que processa dados e gera gráficos Sankey.
    
    Gera:
    - Um gráfico para cada banco
    - Um gráfico geral consolidado
    """
    try:
        df = pd.read_excel(nome_arquivo_excel)
        
        # Conversão de tipos
        df['Valor'] = pd.to_numeric(df['Valor'].fillna(0))
        for col in ['Banco', 'Tipo_Transacao', 'Descricao', 'Categoria_Auto', 'Categoria']:
            df[col] = df[col].astype(str)
        
        # Criar descrição completa
        df['Descricao_Completa'] = df.apply(criar_descricao_completa, axis=1)
        
        # Filtrar transferências próprias usando Categoria_Auto
        transferencias_proprias = ['TRANSFERENCIA_PROPRIA', 'TRANSFERÊNCIA_PRÓPRIA', 'TRANSFERENCIA PROPRIA', 'TRANSFERÊNCIA PRÓPRIA']
        mask_transferencia = df['Categoria_Auto'].str.upper().str.contains('|'.join(transferencias_proprias), na=False)
        df_processado = df[~mask_transferencia].copy()
        
        if df_processado.empty:
            print("❌ Nenhum dado válido após filtrar transferências próprias")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            with open(Path(output_dir) / "nenhum_dado_valido.html", "w") as f:
                f.write("<html><body><h1>Nenhum dado válido encontrado.</h1></body></html>")
            return
        
        # Inicializar colunas de categorização
        df_processado['Tipo_Transacao_AltoNivel'] = ''
        df_processado['Tipo_Transacao_Detalhe'] = ''
        df_processado['Categoria_Agrupada'] = ''
        
        # Categorizar receitas
        receitas_mask = df_processado['Valor'] > 0
        if receitas_mask.any():
            df_receitas = df_processado[receitas_mask].copy()
            categoria_resultado = df_receitas['Descricao_Completa'].apply(categorizar_receitas_por_palavras_chave)
            df_receitas['Tipo_Transacao_AltoNivel'] = categoria_resultado.apply(lambda x: x[0])
            df_receitas['Tipo_Transacao_Detalhe'] = categoria_resultado.apply(lambda x: x[1])
            df_processado.loc[receitas_mask, 'Tipo_Transacao_AltoNivel'] = df_receitas['Tipo_Transacao_AltoNivel']
            df_processado.loc[receitas_mask, 'Tipo_Transacao_Detalhe'] = df_receitas['Tipo_Transacao_Detalhe']
        
        # Categorizar despesas
        despesas_mask = df_processado['Valor'] < 0
        if despesas_mask.any():
            df_despesas = df_processado[despesas_mask].copy()
            df_despesas['Categoria_Agrupada'] = df_despesas.apply(
                lambda row: categorizar_despesas_por_palavras_chave(row['Descricao_Completa'], row['Categoria_Auto']), 
                axis=1
            )
            df_processado.loc[despesas_mask, 'Categoria_Agrupada'] = df_despesas['Categoria_Agrupada']
        
        # Validar dados finais
        if df_processado.empty:
            print("❌ Nenhum dado válido após categorização")
            return
        
        # Obter bancos únicos
        bancos_unicos = df_processado['Banco'].unique()
        if len(bancos_unicos) == 0:
            print("❌ Nenhum banco encontrado")
            return
        
        print(f"📊 Processando {len(df_processado)} transações de {len(bancos_unicos)} banco(s)")
        
        # Gerar gráficos por banco
        for banco in bancos_unicos:
            df_banco = df_processado[df_processado['Banco'] == banco].copy()
            if not df_banco.empty:
                gerar_sankey_por_banco(df_banco, banco, output_dir)
        
        # Gerar gráfico geral
        gerar_sankey_geral(df_processado, output_dir)
        
        print(f"✅ Análise concluída! Arquivos salvos em '{output_dir}'")
        
    except FileNotFoundError:
        print(f"❌ Arquivo '{nome_arquivo_excel}' não encontrado")
        sys.exit(1)
    except KeyError as e:
        print(f"❌ Coluna '{e}' não encontrada no Excel")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gerador de Gráficos Sankey para Análise de Gastos')
    parser.add_argument('--excel', type=str, default='controle_gastos.xlsx',
                        help='Arquivo Excel com dados (padrão: controle_gastos.xlsx)')
    parser.add_argument('--output_dir', type=str, default='output',
                        help='Diretório de saída (padrão: output)')
    
    args = parser.parse_args()
    analisar_gastos_sankey_proventos_detalhados(nome_arquivo_excel=args.excel, output_dir=args.output_dir)
