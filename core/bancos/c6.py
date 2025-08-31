"""
Processador de extratos do C6 Bank.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, extrair_agencia_conta
from logger import get_logger

logger = get_logger(__name__)


def calcular_saldo_inicial_c6(df: pd.DataFrame) -> float:
    """
    Calcula o saldo inicial do C6 Bank baseado nas transações do dia mais antigo.
    O saldo inicial é calculado como: Saldo do Dia - soma das transações do dia.
    """
    if df.empty:
        return 0.0
    
    # Converter datas para datetime se ainda não foram
    df['Data Lançamento'] = pd.to_datetime(df['Data Lançamento'], dayfirst=True, errors='coerce')
    
    # Encontrar o dia mais antigo
    dia_mais_antigo = df['Data Lançamento'].min()
    
    # Filtrar transações do dia mais antigo
    transacoes_dia_antigo = df[df['Data Lançamento'] == dia_mais_antigo]
    
    if transacoes_dia_antigo.empty:
        return 0.0
    
    # Pegar o saldo do dia (assumindo que é o mesmo para todas as transações do dia)
    saldo_do_dia = pd.to_numeric(transacoes_dia_antigo['Saldo do Dia(R$)'].iloc[0], errors='coerce')
    
    # Calcular soma das transações do dia
    entradas = pd.to_numeric(transacoes_dia_antigo['Entrada(R$)'].fillna(0), errors='coerce').sum()
    saidas = pd.to_numeric(transacoes_dia_antigo['Saída(R$)'].fillna(0), errors='coerce').sum()
    total_transacoes_dia = entradas - saidas
    
    # Saldo inicial = Saldo do Dia - Transações do Dia
    saldo_inicial = saldo_do_dia - total_transacoes_dia
    return saldo_inicial


def processar(config: dict) -> pd.DataFrame:
    logger.info("📊 Processando C6 Bank...")
    
    try:
        arquivo_path = config['arquivos']['c6_bank']
        
        agencia_conta = extrair_agencia_conta(arquivo_path, 'C6 Bank')
        
        df = pd.read_csv(
            arquivo_path,
            encoding='utf-8',
            sep=',',
            skiprows=config['processamento']['skip_rows_c6']
        )
        
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        if df.empty:
            logger.warning("Arquivo vazio")
            return pd.DataFrame()
        
        # Calcular saldo inicial automaticamente
        saldo_inicial_calculado = calcular_saldo_inicial_c6(df)
        
        # Atualizar configuração com o saldo inicial calculado
        config['saldos_iniciais']['c6_bank'] = saldo_inicial_calculado
        
        df['entrada_num'] = pd.to_numeric(df['Entrada(R$)'].fillna(0), errors='coerce')
        df['saida_num'] = pd.to_numeric(df['Saída(R$)'].fillna(0), errors='coerce')
        df['valor'] = df['entrada_num'] - df['saida_num']
        
        # Ajustar pagamentos de fatura do cartão
        mask_pagto_fatura = df['Título'].astype(str).str.contains('PGTO FAT CARTAO', na=False, case=False)
        df.loc[mask_pagto_fatura, 'entrada_num'] = df.loc[mask_pagto_fatura, 'saida_num']
        df.loc[mask_pagto_fatura, 'saida_num'] = 0.0
        df.loc[mask_pagto_fatura, 'valor'] = df.loc[mask_pagto_fatura, 'entrada_num']
        
        data_dict = {
            'Data': pd.to_datetime(df['Data Lançamento'], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df['Data Contábil'], dayfirst=True, errors='coerce'),
            'Banco': 'C6 Bank',
            'Agencia_Conta': agencia_conta,
            'Tipo_Transacao': df['Título'],
            'Descricao': df['Descrição'],
            'Valor': df['valor'],
            'Valor_Entrada': df['entrada_num'],
            'Valor_Saida': df['saida_num']
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        
        resultado = resultado.dropna(subset=['Data'])
        resultado['Categoria_Auto'] = resultado.apply(
            lambda row: _categorizar_c6(
                row['Tipo_Transacao'], 
                row['Descricao'], 
                row['Valor'], 
                config['categorias']
            ), axis=1
        )
        
        logger.info(f"✅ Transações processadas")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        return pd.DataFrame()


def _categorizar_c6(tipo: str, descricao: str, valor: float, categorias: dict) -> str:
    """Categorização específica para o C6 Bank"""
    
    # Verificar se é pagamento de fatura do cartão
    texto_completo = f"{str(tipo).upper()} {str(descricao).upper()}"
    if 'PGTO FAT CARTAO' in texto_completo or 'FATURA DE CARTAO' in texto_completo:
        return 'Cartão Crédito'
    
    # Para outros casos, usar a categorização padrão
    return categorizar_transacao_auto(tipo, descricao, valor, categorias)
