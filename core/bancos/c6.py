"""
Processador de extratos do C6 Bank.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, extrair_agencia_conta


def processar(config: dict) -> pd.DataFrame:
    print("📊 Processando C6 Bank...")
    
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
            print("   ⚠️  Arquivo vazio")
            return pd.DataFrame()
        
        df['entrada_num'] = pd.to_numeric(df['Entrada(R$)'].fillna(0), errors='coerce')
        df['saida_num'] = pd.to_numeric(df['Saída(R$)'].fillna(0), errors='coerce')
        df['valor'] = df['entrada_num'] - df['saida_num']
        
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
            lambda row: categorizar_transacao_auto(
                row['Tipo_Transacao'], 
                row['Descricao'], 
                row['Valor'], 
                config['categorias']
            ), axis=1
        )
        
        print(f"   ✅ Transações processadas")
        return resultado
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return pd.DataFrame()
