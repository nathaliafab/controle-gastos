#!/usr/bin/env python3
"""
Script para gerar gráfico Sankey de fluxo de movimentações bancárias.
Mostra o fluxo de dinheiro entre diferentes tipos de transações e categorias.
"""

import pandas as pd
import plotly.graph_objects as go
import argparse
import sys
from pathlib import Path


def carregar_dados(arquivo_excel):
    """Carrega os dados do arquivo Excel de extratos processados."""
    try:
        df = pd.read_excel(arquivo_excel)
        print(f"✅ Carregados {len(df)} registros de {arquivo_excel}")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return None


def preparar_dados_sankey(df):
    """Prepara os dados para o gráfico Sankey otimizado baseado na estrutura real dos dados."""
    # Filtrar apenas saídas (valores negativos) para focar nos gastos
    df_saidas = df[df['Valor'] < 0].copy()
    df_saidas['Valor_Abs'] = abs(df_saidas['Valor'])
    
    # Agrupar bancos de forma inteligente (Top 3 + Outros)
    total_por_banco = df_saidas.groupby('Banco')['Valor_Abs'].sum().sort_values(ascending=False)
    top_bancos = total_por_banco.head(3).index.tolist()
    df_saidas['Banco_Agrupado'] = df_saidas['Banco'].apply(
        lambda x: x if x in top_bancos else 'Outros Bancos'
    )
    
    # Agrupar categorias - incluindo "Outros" para categorias não especificadas
    def agrupar_categoria(cat):
        if pd.isna(cat) or cat == '':
            return 'Outros'  # Sem categoria vira "Outros"
        
        cat_lower = str(cat).lower()
        
        # Categorias principais solicitadas
        if 'cartão crédito' in cat_lower:
            return 'Cartão Crédito'
        elif 'cartão débito' in cat_lower:
            return 'Cartão Débito'
        elif 'pix enviado' in cat_lower:
            return 'PIX Enviado'
        elif 'investimento' in cat_lower:
            return 'Investimentos'
        else:
            return 'Outros'  # Todas as outras categorias viram "Outros"
    
    df_saidas['Categoria_Agrupada'] = df_saidas['Categoria_Auto'].apply(agrupar_categoria)
    
    # Filtrar apenas gastos significativos (acima de R$ 20 para reduzir ruído)
    df_saidas_significativas = df_saidas[df_saidas['Valor_Abs'] >= 20.0].copy()
    
    # Criar estrutura simplificada: Banco -> Categoria (pulando tipo intermediário para menos poluição)
    nodes = []
    node_map = {}
    
    # Adicionar bancos (Nível 1)
    bancos_unicos = sorted(df_saidas_significativas['Banco_Agrupado'].unique())
    for banco in bancos_unicos:
        node_map[f"banco_{banco}"] = len(nodes)
        if banco == 'Outros Bancos':
            nodes.append(f"🏦 {banco}")
        else:
            nodes.append(f"🏦 {banco}")
    
    # Adicionar categorias (Nível 2) - incluindo "Outros"
    categorias_permitidas = ['Cartão Crédito', 'Cartão Débito', 'PIX Enviado', 'Investimentos', 'Outros']
    categorias_unicas = [cat for cat in sorted(df_saidas_significativas['Categoria_Agrupada'].unique()) 
                        if cat in categorias_permitidas]
    
    for categoria in categorias_unicas:
        node_map[f"cat_{categoria}"] = len(nodes)
        
        # Ícones específicos para cada categoria
        if categoria == 'Cartão Crédito':
            icon = "💳"
        elif categoria == 'Cartão Débito':
            icon = "💰"
        elif categoria == 'PIX Enviado':
            icon = "📱"
        elif categoria == 'Investimentos':
            icon = "📈"
        elif categoria == 'Outros':
            icon = "🏷️"
        
        nodes.append(f"{icon} {categoria}")
    
    # Criar fluxos diretos: Banco -> Categoria
    links = {'source': [], 'target': [], 'value': []}
    
    fluxo_banco_categoria = df_saidas_significativas.groupby(['Banco_Agrupado', 'Categoria_Agrupada'])['Valor_Abs'].sum().reset_index()
    
    for _, row in fluxo_banco_categoria.iterrows():
        if row['Valor_Abs'] >= 50:  # Apenas fluxos >= R$ 50 para máxima clareza
            source = node_map[f"banco_{row['Banco_Agrupado']}"]
            target = node_map[f"cat_{row['Categoria_Agrupada']}"]
            links['source'].append(source)
            links['target'].append(target)
            links['value'].append(row['Valor_Abs'])
    
    return nodes, links


def gerar_sankey(df, arquivo_output):
    """Gera o gráfico Sankey ultra-otimizado e limpo."""
    nodes, links = preparar_dados_sankey(df)
    
    if not links['source']:  # Se não há fluxos, criar um mínimo
        print("⚠️ Poucos fluxos significativos encontrados. Reduzindo filtros...")
        # Tentar com filtro menor
        df_saidas = df[df['Valor'] < 0].copy()
        df_saidas['Valor_Abs'] = abs(df_saidas['Valor'])
        df_saidas_min = df_saidas[df_saidas['Valor_Abs'] >= 10.0]  # Mínimo R$ 10
        
        # Reprocessar com filtro menor
        nodes = []
        node_map = {}
        
        # Bancos principais
        bancos_principais = ['Itaú', 'C6 Bank', 'Bradesco']
        outros_bancos = [b for b in df_saidas_min['Banco'].unique() if b not in bancos_principais]
        
        for banco in bancos_principais:
            if banco in df_saidas_min['Banco'].values:
                node_map[f"banco_{banco}"] = len(nodes)
                nodes.append(f"🏦 {banco}")
        
        if outros_bancos:
            node_map["banco_Outros"] = len(nodes)
            nodes.append("🏦 Outros Bancos")
        
        # Categorias simplificadas - incluindo "Outros"
        cat_mapping = {
            'Cartão Crédito': '💳 Cartão Crédito',
            'Cartão Débito': '💰 Cartão Débito',
            'PIX Enviado': '📱 PIX Enviado', 
            'Investimentos': '📈 Investimentos',
            'Outros': '🏷️ Outros'
        }
        
        for cat_orig, cat_display in cat_mapping.items():
            node_map[f"cat_{cat_orig}"] = len(nodes)
            nodes.append(cat_display)
        
        # Fluxos simplificados baseados apenas em Categoria_Auto
        links = {'source': [], 'target': [], 'value': []}
        
        # Agrupar dados por banco e categoria
        fluxo_agrupado = df_saidas_min.groupby(['Banco', 'Categoria_Auto'])['Valor_Abs'].sum().reset_index()
        
        for _, row in fluxo_agrupado.iterrows():
            # Determinar banco
            if row['Banco'] in bancos_principais:
                banco_key = f"banco_{row['Banco']}"
            else:
                banco_key = "banco_Outros"
            
            # Determinar categoria - incluindo "Outros"
            cat_auto = row['Categoria_Auto']
            
            # Aplicar a mesma lógica de agrupamento
            if pd.isna(cat_auto) or cat_auto == '':
                categoria_final = 'Outros'
            else:
                cat_lower = str(cat_auto).lower()
                if 'cartão crédito' in cat_lower:
                    categoria_final = 'Cartão Crédito'
                elif 'cartão débito' in cat_lower:
                    categoria_final = 'Cartão Débito'
                elif 'pix enviado' in cat_lower:
                    categoria_final = 'PIX Enviado'
                elif 'investimento' in cat_lower:
                    categoria_final = 'Investimentos'
                else:
                    categoria_final = 'Outros'
            
            if categoria_final in cat_mapping:
                cat_key = f"cat_{categoria_final}"
            else:
                continue  # Pular se não está no mapeamento
            
            # Verificar se ambos os nós existem
            if banco_key in node_map and cat_key in node_map:
                source = node_map[banco_key]
                target = node_map[cat_key]
                links['source'].append(source)
                links['target'].append(target)
                links['value'].append(row['Valor_Abs'])
    
    # Criar cores mais harmoniosas com distinção clara para cada categoria
    cores_nos = []
    for node in nodes:
        if node.startswith('🏦'):  # Bancos
            cores_nos.append('rgba(41, 128, 185, 0.9)')  # Azul elegante
        elif node.startswith('💳'):  # Cartão crédito
            cores_nos.append('rgba(231, 76, 60, 0.9)')   # Vermelho vibrante
        elif node.startswith('💰'):  # Cartão débito
            cores_nos.append('rgba(52, 152, 219, 0.9)')  # Azul claro
        elif node.startswith('📱'):  # PIX
            cores_nos.append('rgba(46, 204, 113, 0.9)')  # Verde vibrante
        elif node.startswith('📈'):  # Investimentos
            cores_nos.append('rgba(155, 89, 182, 0.9)')  # Roxo elegante
        elif node.startswith('🏷️'):  # Outros
            cores_nos.append('rgba(241, 196, 15, 0.9)')  # Amarelo/dourado
        else:  # Fallback
            cores_nos.append('rgba(149, 165, 166, 0.9)')  # Cinza
    
    # Criar cores para os links baseadas na categoria de destino
    cores_links = []
    for i in range(len(links['source'])):
        target_node = nodes[links['target'][i]]
        if target_node.startswith('💳'):  # Cartão crédito
            cores_links.append('rgba(231, 76, 60, 0.3)')   # Vermelho transparente
        elif target_node.startswith('💰'):  # Cartão débito
            cores_links.append('rgba(52, 152, 219, 0.3)')  # Azul transparente
        elif target_node.startswith('📱'):  # PIX
            cores_links.append('rgba(46, 204, 113, 0.3)')  # Verde transparente
        elif target_node.startswith('📈'):  # Investimentos
            cores_links.append('rgba(155, 89, 182, 0.3)')  # Roxo transparente
        elif target_node.startswith('🏷️'):  # Outros
            cores_links.append('rgba(241, 196, 15, 0.3)')  # Amarelo transparente
        else:
            cores_links.append('rgba(149, 165, 166, 0.3)')  # Cinza transparente
    
    # Calcular totais para cada nó
    node_totals = {}
    for i in range(len(nodes)):
        total = sum([links['value'][j] for j in range(len(links['value'])) 
                    if links['source'][j] == i or links['target'][j] == i])
        node_totals[i] = total
    
    # Criar o gráfico Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=25,
            thickness=30,
            line=dict(color="rgba(0,0,0,0.8)", width=2),
            label=[f"{node}<br>R$ {node_totals.get(i, 0):,.0f}" for i, node in enumerate(nodes)],
            color=cores_nos,
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            color=cores_links,
            hovertemplate='%{source.label} → %{target.label}<br><b>R$ %{value:,.2f}</b><extra></extra>'
        )
    )])
    
    total_saidas = abs(df[df['Valor'] < 0]['Valor'].sum())
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    saldo = total_entradas - total_saidas
    total_fluxos = sum(links['value']) if links['value'] else 0
    cobertura = (total_fluxos / total_saidas * 100) if total_saidas > 0 else 0
    
    # Determinar cor do saldo
    cor_saldo = '#27ae60' if saldo >= 0 else '#e74c3c'  # Verde se positivo, vermelho se negativo
    simbolo_saldo = '+' if saldo >= 0 else ''  # Adicionar '+' se positivo
    
    fig.update_layout(
        title={
            'text': f"💰 Fluxo de Gastos<br><span style='font-size:14px; color:#7f8c8d'>💸 Saídas: R$ {total_saidas:,.2f} | 💵 Entradas: R$ {total_entradas:,.2f} | <span style='color:{cor_saldo}'>💼 Saldo: {simbolo_saldo}R$ {saldo:,.2f}</span></span><br><span style='font-size:12px; color:#95a5a6'>Visualizado: R$ {total_fluxos:,.2f} ({cobertura:.1f}% dos gastos)</span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50'}
        },
        font=dict(size=13, family="Arial", color='#2c3e50'),
        height=600,
        width=1200,
        margin=dict(t=100, l=50, r=50, b=50),
        paper_bgcolor='#f8f9fa',
        plot_bgcolor='#f8f9fa'
    )
    
    # Salvar como HTML
    arquivo_html = arquivo_output.replace('.xlsx', '_sankey.html')
    fig.write_html(arquivo_html, include_plotlyjs='cdn')
    print(f"🌊 Gráfico Sankey ultra-otimizado salvo em: {arquivo_html}")
    print(f"� Entradas: R$ {total_entradas:,.2f}")
    print(f"💸 Saídas: R$ {total_saidas:,.2f}")
    print(f"💼 Saldo: {simbolo_saldo}R$ {saldo:,.2f}")
    print(f"�📊 Cobertura: {cobertura:.1f}% dos gastos visualizados")
    print(f"💡 Dica: Abra o arquivo {arquivo_html} no navegador para interação completa")


def main():
    parser = argparse.ArgumentParser(description='Gerador de Gráfico Sankey para Análise de Gastos')
    parser.add_argument('arquivo_excel', help='Caminho para o arquivo Excel de saída do processador')
    parser.add_argument('--output', '-o', help='Nome do arquivo de saída (opcional)')
    
    args = parser.parse_args()
    
    if not Path(args.arquivo_excel).exists():
        print(f"Arquivo não encontrado: {args.arquivo_excel}")
        sys.exit(1)
    
    df = carregar_dados(args.arquivo_excel)
    if df is None:
        sys.exit(1)
    
    arquivo_output = args.output if args.output else args.arquivo_excel
    gerar_sankey(df, arquivo_output)
    
    print("Análise Sankey concluída!")


if __name__ == "__main__":
    main()
