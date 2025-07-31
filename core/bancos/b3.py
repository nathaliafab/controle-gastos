"""
Este processador lê o arquivo Excel consolidado da B3 e processa as posições de:
- Ações
- Fundos
- Renda Fixa
- Tesouro Direto

Gera uma tabela padronizada com informações de investimentos.
"""

import pandas as pd
from logger import get_logger

logger = get_logger(__name__)


def _formatar_valor(valor):
    """
    Formata valores monetários, dividindo por 100 se necessário
    
    Args:
        valor: Valor a ser formatado
        
    Returns:
        Valor formatado como float
    """
    if pd.isna(valor) or valor == 0:
        return 0
    
    try:
        valor_num = float(valor)
        # Se o valor for maior que 1000 e não tiver casas decimais, divide por 100
        if valor_num > 1000 and valor_num == int(valor_num):
            return valor_num / 100
        return valor_num
    except (ValueError, TypeError):
        return 0


def processar(config: dict) -> pd.DataFrame:
    """
    Processa relatório consolidado da B3
    
    Args:
        config: Dicionário com configurações do sistema
        
    Returns:
        DataFrame com as posições processadas no formato padronizado
    """
    logger.info("📊 Processando B3...")
    
    try:
        arquivo_b3 = config['arquivos'].get('b3', 'extratos/relatorio-consolidado-mensal-2025-junho.xlsx')
        mes_referencia = config['processamento'].get('mes_b3', 'junho/2025')
        
        # Ler arquivo Excel
        excel_file = pd.ExcelFile(arquivo_b3)
        
        # Processar cada aba
        resultados = []
        
        # Ações
        if 'Posição - Ações' in excel_file.sheet_names:
            df_acoes = _processar_acoes(pd.read_excel(arquivo_b3, sheet_name='Posição - Ações'), mes_referencia)
            resultados.append(df_acoes)
        
        # Fundos
        if 'Posição - Fundos' in excel_file.sheet_names:
            df_fundos = _processar_fundos(pd.read_excel(arquivo_b3, sheet_name='Posição - Fundos'), mes_referencia)
            resultados.append(df_fundos)
        
        # Renda Fixa
        if 'Posição - Renda Fixa' in excel_file.sheet_names:
            df_renda_fixa = _processar_renda_fixa(pd.read_excel(arquivo_b3, sheet_name='Posição - Renda Fixa'), mes_referencia)
            resultados.append(df_renda_fixa)
        
        # Tesouro Direto
        if 'Posição - Tesouro Direto' in excel_file.sheet_names:
            df_tesouro = _processar_tesouro_direto(pd.read_excel(arquivo_b3, sheet_name='Posição - Tesouro Direto'), mes_referencia)
            resultados.append(df_tesouro)
        
        # Combinar todos os resultados
        if resultados:
            resultado_final = pd.concat(resultados, ignore_index=True)
            logger.info(f"✅ {len(resultado_final)} posições processadas da B3")
            return resultado_final
        else:
            logger.warning("Nenhuma posição encontrada")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Erro ao processar B3: {e}")
        return pd.DataFrame()


def _processar_acoes(df: pd.DataFrame, mes_referencia: str) -> pd.DataFrame:
    """Processa posições de ações"""
    if df.empty:
        return pd.DataFrame()
    
    # Remover linhas vazias e totais
    df = df.dropna(subset=['Produto'])
    df = df[df['Produto'].str.contains('Total', na=False) == False]
    
    dados_processados = []
    
    for _, row in df.iterrows():
        try:
            # Extrair código da ação do produto
            codigo = row.get('Código de Negociação', '')
            if pd.isna(codigo):
                # Tentar extrair do produto
                produto = str(row.get('Produto', ''))
                if ' - ' in produto:
                    codigo = produto.split(' - ')[0]
                else:
                    codigo = produto
            
            dados_processados.append({
                'Mês': mes_referencia,
                'Produto': row.get('Produto', ''),
                'Instituição': row.get('Instituição', ''),
                'Código de Negociação': codigo,
                'Tipo': 'Ação',
                'Indexador': '-',
                'Quantidade': row.get('Quantidade Disponível', 0),
                'Preço de Fechamento': _formatar_valor(row.get('Preço de Fechamento', 0)),
                'Data de Emissão': '-',
                'Data de Vencimento': '-',
                'Valor Investido': '-',  # Não disponível nas ações
                'Valor Atual': _formatar_valor(row.get('Valor Atualizado', 0))
            })
        except Exception as e:
            logger.warning(f"Erro ao processar ação: {e}")
            continue
    
    return pd.DataFrame(dados_processados)


def _processar_fundos(df: pd.DataFrame, mes_referencia: str) -> pd.DataFrame:
    """Processa posições de fundos"""
    if df.empty:
        return pd.DataFrame()
    
    # Remover linhas vazias e totais
    df = df.dropna(subset=['Produto'])
    df = df[df['Produto'].str.contains('Total', na=False) == False]
    
    dados_processados = []
    
    for _, row in df.iterrows():
        try:
            # Extrair código do fundo
            codigo = row.get('Código de Negociação', '')
            if pd.isna(codigo):
                produto = str(row.get('Produto', ''))
                if ' - ' in produto:
                    codigo = produto.split(' - ')[0]
                else:
                    codigo = produto
            
            dados_processados.append({
                'Mês': mes_referencia,
                'Produto': row.get('Produto', ''),
                'Instituição': row.get('Instituição', ''),
                'Código de Negociação': codigo,
                'Tipo': 'Fundo',
                'Indexador': '-',
                'Quantidade': row.get('Quantidade Disponível', 0),
                'Preço de Fechamento': _formatar_valor(row.get('Preço de Fechamento', 0)),
                'Data de Emissão': '-',
                'Data de Vencimento': '-',
                'Valor Investido': '-',
                'Valor Atual': _formatar_valor(row.get('Valor Atualizado', 0))
            })
        except Exception as e:
            logger.warning(f"Erro ao processar fundo: {e}")
            continue
    
    return pd.DataFrame(dados_processados)


def _processar_renda_fixa(df: pd.DataFrame, mes_referencia: str) -> pd.DataFrame:
    """Processa posições de renda fixa"""
    if df.empty:
        return pd.DataFrame()
    
    # Remover linhas vazias e totais
    df = df.dropna(subset=['Produto'])
    df = df[df['Produto'].str.contains('Total', na=False) == False]
    
    dados_processados = []
    
    for _, row in df.iterrows():
        try:
            produto = row.get('Produto', '')
            
            # Aplicar formatação especial apenas para LCI
            if 'LCI' in produto.upper():
                valor_investido = _formatar_valor(row.get('Quantidade', 0))
                valor_atual = _formatar_valor(row.get('Valor Atualizado CURVA', 0))
            else:
                # Para CDB e outros, não dividir por 100
                valor_investido = row.get('Quantidade', 0)
                valor_atual = row.get('Valor Atualizado CURVA', 0)
            
            dados_processados.append({
                'Mês': mes_referencia,
                'Produto': produto,
                'Instituição': row.get('Instituição', ''),
                'Código de Negociação': row.get('Código', ''),
                'Tipo': 'Renda Fixa',
                'Indexador': row.get('Indexador', '-'),
                'Quantidade': '-',
                'Preço de Fechamento': '-',
                'Data de Emissão': row.get('Data de Emissão', '-'),
                'Data de Vencimento': row.get('Vencimento', '-'),
                'Valor Investido': valor_investido,
                'Valor Atual': valor_atual
            })
        except Exception as e:
            logger.warning(f"Erro ao processar renda fixa: {e}")
            continue
    
    return pd.DataFrame(dados_processados)


def _processar_tesouro_direto(df: pd.DataFrame, mes_referencia: str) -> pd.DataFrame:
    """Processa posições do Tesouro Direto"""
    if df.empty:
        return pd.DataFrame()
    
    # Remover linhas vazias e totais
    df = df.dropna(subset=['Produto'])
    df = df[df['Produto'].str.contains('Total', na=False) == False]
    
    dados_processados = []
    
    for _, row in df.iterrows():
        try:
            dados_processados.append({
                'Mês': mes_referencia,
                'Produto': row.get('Produto', ''),
                'Instituição': 'Tesouro Nacional',
                'Código de Negociação': row.get('ISIN', ''),
                'Tipo': 'Tesouro Direto',
                'Indexador': row.get('Indexador', '-'),
                'Quantidade': row.get('Quantidade Disponível', 0),
                'Preço de Fechamento': '-',
                'Data de Emissão': '-',
                'Data de Vencimento': row.get('Vencimento', '-'),
                'Valor Investido': _formatar_valor(row.get('Valor Aplicado', 0)),
                'Valor Atual': _formatar_valor(row.get('Valor Atualizado', 0))
            })
        except Exception as e:
            logger.warning(f"Erro ao processar tesouro direto: {e}")
            continue
    
    return pd.DataFrame(dados_processados)
