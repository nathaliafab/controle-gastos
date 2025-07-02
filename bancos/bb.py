"""
Processador de extratos do Banco do Brasil.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, extrair_agencia_conta


def processar(config: dict) -> pd.DataFrame:
    print("📊 Processando Banco do Brasil...")
    
    try:
        arquivo_path = config['arquivos']['bb']
        
        agencia_conta = extrair_agencia_conta(arquivo_path, 'Banco do Brasil')
        
        df = pd.read_csv(
            arquivo_path, 
            encoding='latin1',
            skiprows=config['processamento']['skip_rows_bb']
        )
        
        _extrair_saldo_anterior(df, config)
        
        filtros_exclusao = ['Saldo Anterior', 'Saldo do dia', 'S A L D O', 'BB Rende Fácil']
        for filtro in filtros_exclusao:
            df = df[~df['Lançamento'].str.contains(filtro, na=False)]
        
        df['valor_num'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        
        df['valor_final'] = df.apply(_aplicar_sinal_correto, axis=1)
        
        df[['entrada', 'saida']] = df.apply(
            lambda row: pd.Series(_calcular_valores_entrada_saida(row)), axis=1
        )
        
        data_dict = {
            'Data': pd.to_datetime(df['Data'], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df['Data'], dayfirst=True, errors='coerce'),
            'Banco': 'Banco do Brasil',
            'Agencia_Conta': agencia_conta,
            'Tipo_Transacao': df['Lançamento'],
            'Descricao': df['Detalhes'],
            'Valor': df['valor_final'],
            'Valor_Entrada': df['entrada'],
            'Valor_Saida': df['saida']
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        
        resultado['Categoria_Auto'] = resultado.apply(
            lambda row: categorizar_transacao_auto(
                row['Tipo_Transacao'], 
                row['Descricao'], 
                row['Valor'], 
                config['categorias']
            ), axis=1
        )
        
        print(f"   ✅ {len(resultado)} transações processadas")
        return resultado
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return pd.DataFrame()


def _extrair_saldo_anterior(df: pd.DataFrame, config: dict) -> None:
    try:
        saldo_anterior_linhas = df[df['Lançamento'].str.contains('Saldo Anterior', na=False)]
        if not saldo_anterior_linhas.empty:
            primeira_linha = saldo_anterior_linhas.iloc[0]
            valor_str = str(primeira_linha['Valor']).replace('.', '').replace(',', '.')
            saldo_anterior = float(valor_str)
            config['saldos_iniciais']['bb'] = saldo_anterior
    except Exception as e:
        pass


def _aplicar_sinal_correto(row):
    valor_num = abs(row['valor_num'])
    tipo = row['Tipo Lançamento'].upper()
    
    if tipo == 'ENTRADA':
        return valor_num
    elif tipo == 'SAÍDA':
        return -valor_num
    else:
        return row['valor_num']


def _calcular_valores_entrada_saida(row):
    valor_num = abs(row['valor_num'])
    tipo = row['Tipo Lançamento'].upper()
    
    if tipo == 'ENTRADA':
        return valor_num, 0
    elif tipo == 'SAÍDA':
        return 0, valor_num
    else:
        return 0, 0
