"""
Processador de extratos do Itaú.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado, extrair_agencia_conta
from logger import get_logger
import re

logger = get_logger(__name__)


def processar(config: dict) -> pd.DataFrame:
    """Processa extrato do Itaú - suporta conta corrente (.xls) e cartão de crédito (.xlsx)"""
    logger.info("📊 Processando Itaú...")
    
    try:
        arquivos_itau = config['arquivos']['itau']
        
        # Suportar tanto string (arquivo único) quanto lista (múltiplos arquivos)
        if isinstance(arquivos_itau, str):
            if not arquivos_itau:
                logger.warning("Caminho do arquivo Itaú não configurado")
                return pd.DataFrame()
            lista_arquivos = [arquivos_itau]
        else:
            lista_arquivos = arquivos_itau
        
        # Processar todos os arquivos
        dataframes = []
        for arquivo_path in lista_arquivos:
            if not arquivo_path:
                continue
                
            if arquivo_path.endswith('.xls'):
                df = _processar_conta_corrente(arquivo_path, config)
            elif arquivo_path.endswith('.xlsx'):
                df = _processar_cartao_credito(arquivo_path, config)
            else:
                continue
            
            if not df.empty:
                dataframes.append(df)
        
        if dataframes:
            resultado_final = pd.concat(dataframes, ignore_index=True)
            logger.info(f"✅ Transações processadas")
            return resultado_final
        else:
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Erro: {e}")
        return pd.DataFrame()


def _processar_conta_corrente(arquivo_path: str, config: dict) -> pd.DataFrame:
    try:
        agencia_conta = extrair_agencia_conta(arquivo_path, 'Itaú')
        
        df = pd.read_excel(
            arquivo_path,
            engine='xlrd',
            header=None,
            skiprows=config['processamento']['skip_rows_itau']
        )
        
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        if df.empty:
            logger.warning("Arquivo vazio")
            return pd.DataFrame()
        
        _extrair_saldo_anterior(df, config)
        
        df_filtrado = df[
            (~df.iloc[:, 1].astype(str).str.contains('SALDO ANTERIOR', na=False)) &
            (~df.iloc[:, 1].astype(str).str.contains('SALDO TOTAL', na=False)) &
            (~df.iloc[:, 1].astype(str).str.contains('lançamentos futuros', na=False)) &
            (~df.iloc[:, 1].astype(str).str.contains('saídas futuras', na=False))
        ].copy()
        
        df_filtrado['valor_num'] = pd.to_numeric(df_filtrado.iloc[:, 2], errors='coerce')

        # Se for pagamento de fatura (ITAU NOME NUM-NUM), valor deve ser positivo
        mask_pagamento_fatura = df_filtrado.iloc[:, 1].astype(str).str.match(r'ITAU .+ \d+-\d+')
        df_filtrado.loc[mask_pagamento_fatura, 'valor_num'] = df_filtrado.loc[mask_pagamento_fatura, 'valor_num'].abs()
        
        df_filtrado[['entrada', 'saida']] = df_filtrado.apply(
            lambda row: pd.Series(_calcular_valores_entrada_saida(row)), axis=1
        )
        
        data_dict = {
            'Data': pd.to_datetime(df_filtrado.iloc[:, 0], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df_filtrado.iloc[:, 0], dayfirst=True, errors='coerce'),
            'Banco': 'Itaú',
            'Agencia_Conta': agencia_conta,
            'Tipo_Transacao': df_filtrado.iloc[:, 1].astype(str),
            'Descricao': df_filtrado.iloc[:, 1].astype(str),
            'Valor': df_filtrado['valor_num'],
            'Valor_Entrada': df_filtrado['entrada'],
            'Valor_Saida': df_filtrado['saida']
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        resultado = resultado.dropna(subset=['Data', 'Valor'])
        resultado = resultado[resultado['Valor'] != 0]
        
        resultado['Categoria_Auto'] = resultado.apply(lambda row: categorizar_itau(row, config), axis=1)
        
        logger.info(f"✅ Transações processadas")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar conta corrente: {e}")
        return pd.DataFrame()


def _processar_cartao_credito(arquivo_path: str, config: dict) -> pd.DataFrame:
    try:
        df = pd.read_excel(arquivo_path, sheet_name='Lançamentos', header=None)
        
        if df.empty:
            logger.warning("Arquivo vazio")
            return pd.DataFrame()
        
        # Encontrar todos os cartões e suas seções
        cartoes = []
        for i in range(len(df)):
            linha = df.iloc[i]
            linha_str = ' '.join([str(x) for x in linha.dropna()])
            
            # Identificar cartões (não os totais)
            if '- final' in linha_str and 'total nacional' not in linha_str.lower():
                # Extrair informações do cartão
                import re
                match = re.search(r'(.*) - final (\d+) \((.*?)\)', linha_str)
                if match:
                    nome_titular = match.group(1).strip()
                    final_cartao = match.group(2)
                    tipo_cartao = match.group(3)  # titular ou adicional
                    
                    cartoes.append({
                        'linha': i,
                        'nome': nome_titular,
                        'final': final_cartao,
                        'tipo': tipo_cartao,
                        'identificacao': f"{nome_titular} - {final_cartao}"
                    })
        
        todas_transacoes = []
        
        for idx, cartao in enumerate(cartoes):
            linha_inicio = cartao['linha']
            
            # Encontrar onde termina esta seção (próximo cartão ou final)
            if idx + 1 < len(cartoes):
                linha_fim = cartoes[idx + 1]['linha']
            else:
                linha_fim = len(df)
            
            # Extrair transações desta seção
            transacoes_cartao = []
            
            for i in range(linha_inicio, linha_fim):
                linha = df.iloc[i]
                primeira_col = str(linha.iloc[0])
                
                # Verificar se é uma transação (tem data)
                if '/' in primeira_col and len(primeira_col) <= 12:
                    try:
                        data_convertida = pd.to_datetime(primeira_col, dayfirst=True)
                        
                        # Verificar se tem valor na coluna 3
                        valor = linha.iloc[3]
                        if pd.notna(valor) and valor != 0:
                            descricao = str(linha.iloc[1]) if pd.notna(linha.iloc[1]) else ""
                            
                            # Processar valor (gastos são positivos, pagamentos negativos)
                            valor_num = pd.to_numeric(valor, errors='coerce')
                            if pd.notna(valor_num):
                                # Para cartão, gastos são saídas (negativos), pagamentos são entradas (positivos)
                                if valor_num > 0:
                                    # Gasto
                                    entrada = 0.0
                                    saida = valor_num
                                    valor_final = -valor_num
                                else:
                                    # Pagamento/estorno
                                    entrada = abs(valor_num)
                                    saida = 0.0
                                    valor_final = abs(valor_num)
                                
                                transacao = {
                                    'Data': data_convertida,
                                    'Data_Contabil': data_convertida,
                                    'Banco': 'Itaú',
                                    'Agencia_Conta': f"{cartao['final']} - {cartao['nome']}",
                                    'Tipo_Transacao': descricao,
                                    'Descricao': descricao,
                                    'Valor': valor_final,
                                    'Valor_Entrada': entrada,
                                    'Valor_Saida': saida
                                }
                                
                                transacoes_cartao.append(transacao)
                    except:
                        continue
            
            if transacoes_cartao:
                todas_transacoes.extend(transacoes_cartao)
        
        if not todas_transacoes:
            return pd.DataFrame()
        
        # Criar DataFrame
        resultado = pd.DataFrame(todas_transacoes)
        
        # Aplicar padrão de colunas
        resultado = resultado.reindex(columns=[
            'Data', 'Data_Contabil', 'Banco', 'Agencia_Conta', 
            'Tipo_Transacao', 'Descricao', 'Valor', 'Valor_Entrada', 'Valor_Saida'
        ])
        
        resultado['Categoria_Auto'] = resultado.apply(lambda row: categorizar_itau(row, config), axis=1)
        
        logger.info(f"✅ Transações processadas")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar cartão de crédito: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return pd.DataFrame()


# Categorização automática - com lógica especial para cartões
def categorizar_itau(row, config):
    agencia_conta = row['Agencia_Conta']
    tipo_tran = row['Tipo_Transacao']

    if re.match(r'^\d{4} - .+', agencia_conta) or re.match(r'^ITAU\s+.+\s+\d+-\d+$', tipo_tran):
        return "Cartão Crédito"
    return categorizar_transacao_auto(
        row['Tipo_Transacao'],
        row['Descricao'],
        row['Valor'],
        config['categorias']
    )


def _extrair_saldo_anterior(df: pd.DataFrame, config: dict) -> None:
    """Extrai o saldo anterior do Itaú e atualiza config"""
    try:
        saldo_anterior_linhas = df[df.iloc[:, 1].astype(str).str.contains('SALDO ANTERIOR', na=False)]
        if not saldo_anterior_linhas.empty:
            primeira_linha = saldo_anterior_linhas.iloc[0]
            if len(primeira_linha) > 3:
                try:
                    saldo_valor = primeira_linha.iloc[3]
                    if pd.notna(saldo_valor):
                        saldo_anterior = float(str(saldo_valor).replace(',', '.'))
                        config['saldos_iniciais']['itau'] = saldo_anterior
                        return
                except:
                    pass
    except Exception as e:
        pass


def _calcular_valores_entrada_saida(row):
    """Calcula valores de entrada e saída baseado no valor"""
    valor = row['valor_num']
    if pd.isna(valor):
        return 0.0, 0.0
    
    if valor > 0:
        return valor, 0.0
    else:
        return 0.0, abs(valor)