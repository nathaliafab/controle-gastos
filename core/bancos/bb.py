"""
Processador de extratos do Banco do Brasil.
"""

import pandas as pd
import re
from pathlib import Path
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, extrair_agencia_conta


def processar(config: dict) -> pd.DataFrame:
    print("📊 Processando Banco do Brasil...")
    try:
        arquivos_bb = config['arquivos']['bb']
        if isinstance(arquivos_bb, str):
            arquivos_bb = [arquivos_bb]
        arquivos_ordenados = _ordenar_arquivos_por_data(arquivos_bb)
        agencia_conta = None
        dfs = []
        saldo_inicial_detectado = False
        for idx, arquivo_path in enumerate(arquivos_ordenados):
            if not Path(arquivo_path).exists():
                continue
            if agencia_conta is None:
                from utils import extrair_agencia_conta
                agencia_conta = extrair_agencia_conta(arquivo_path, 'Banco do Brasil')
            import pandas as pd
            df = pd.read_csv(
                arquivo_path,
                encoding='latin1',
                skiprows=config['processamento']['skip_rows_bb']
            )
            if not saldo_inicial_detectado:
                _extrair_saldo_anterior(df, config)
                saldo_inicial_detectado = True
            filtros_exclusao = ['Saldo Anterior', 'Saldo do dia', 'S A L D O', 'BB Rende Fácil']
            for filtro in filtros_exclusao:
                df = df[~df['Lançamento'].str.contains(filtro, na=False)]
            if not df.empty:
                df['valor_num'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
                df['valor_final'] = df.apply(_aplicar_sinal_correto, axis=1)
                df[['entrada', 'saida']] = df.apply(
                    lambda row: pd.Series(_calcular_valores_entrada_saida(row)), axis=1
                )
                dfs.append(df)
        if not dfs:
            print("   ⚠️  Nenhum arquivo válido encontrado")
            return pd.DataFrame()
        df_final = pd.concat(dfs, ignore_index=True)
        # Remove transações de pagamento de cartão de crédito para evitar duplicidade
        df_final = df_final[~df_final['Lançamento'].str.upper().str.contains('PAGTO CARTÃO', na=False)]
        data_dict = {
            'Data': pd.to_datetime(df_final['Data'], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df_final['Data'], dayfirst=True, errors='coerce'),
            'Banco': 'Banco do Brasil',
            'Agencia_Conta': agencia_conta,
            'Tipo_Transacao': df_final['Lançamento'],
            'Descricao': df_final['Detalhes'],
            'Valor': df_final['valor_final'],
            'Valor_Entrada': df_final['entrada'],
            'Valor_Saida': df_final['saida']
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
        print(f"   ✅ Transações processadas de arquivo(s)")
        return resultado
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return pd.DataFrame()


def _ordenar_arquivos_por_data(arquivos: list) -> list:
    def extrair_data_nome(arquivo):
        nome = Path(arquivo).name
        match = re.search(r'(\\d{2})(\\d{4})', nome)
        if match:
            mes, ano = match.groups()
            return f"{ano}-{mes.zfill(2)}"
        match = re.search(r'(\\d{1,2})-(\\d{4})', nome)
        if match:
            mes, ano = match.groups()
            return f"{ano}-{mes.zfill(2)}"
        return nome
    try:
        return sorted(arquivos, key=extrair_data_nome)
    except:
        return arquivos


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
