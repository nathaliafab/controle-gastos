"""
Processador de extratos do Bradesco.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, converter_valor_br, extrair_agencia_conta


def processar(config: dict) -> pd.DataFrame:
    print("📊 Processando Bradesco...")
    
    try:
        arquivo_path = config['arquivos']['bradesco']
        
        agencia_conta = extrair_agencia_conta(arquivo_path, 'Bradesco')
        
        df = pd.read_csv(
            arquivo_path,
            encoding='utf-8-sig',
            sep=';',
            skiprows=config['processamento']['skip_rows_bradesco'],
            on_bad_lines='skip'
        )
        
        df = df.dropna(subset=['Data'])
        df = df[df['Data'].astype(str).str.contains(r'\d{2}/\d{2}/\d{4}', na=False)]
        
        # Extrair saldo anterior antes de filtrar
        _extrair_saldo_anterior(df, config)
        
        # Filtrar removendo saldo anterior
        df = df[~df['Histórico'].astype(str).str.contains('SALDO ANTERIOR', na=False)]
        
        # Processar valores
        df['credito'] = df['Crédito (R$)'].apply(converter_valor_br).fillna(0)
        df['debito'] = df['Débito (R$)'].apply(converter_valor_br).fillna(0)
        df['valor'] = df['credito'] - df['debito']
        
        # Criar DataFrame padronizado
        data_dict = {
            'Data': pd.to_datetime(df['Data'], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df['Data'], dayfirst=True, errors='coerce'),
            'Banco': 'Bradesco',
            'Agencia_Conta': agencia_conta,
            'Tipo_Transacao': df['Histórico'],
            'Descricao': df['Histórico'],
            'Valor': df['valor'],
            'Valor_Entrada': df['credito'],
            'Valor_Saida': df['debito']
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        
        # Categorizar
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
        saldo_anterior_linhas = df[df['Histórico'].astype(str).str.contains('SALDO ANTERIOR', na=False)]
        if not saldo_anterior_linhas.empty:
            primeira_linha = saldo_anterior_linhas.iloc[0]
            saldo_anterior_bradesco = converter_valor_br(primeira_linha['Saldo (R$)']) or 0
            config['saldos_iniciais']['bradesco'] = saldo_anterior_bradesco
    except Exception as e:
        pass
