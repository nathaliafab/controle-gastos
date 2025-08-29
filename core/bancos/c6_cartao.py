"""
Processador de fatura do cartão de crédito do C6 Bank.
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado
from logger import get_logger

logger = get_logger(__name__)


def processar(config: dict) -> pd.DataFrame:
    logger.info("📊 Processando fatura do cartão C6...")
    
    try:
        arquivos_c6_cartao = config['arquivos']['c6_cartao']
        
        # Suportar tanto string (arquivo único) quanto lista (múltiplos arquivos)
        if isinstance(arquivos_c6_cartao, str):
            arquivos_c6_cartao = [arquivos_c6_cartao]
        
        todas_transacoes = []
        
        for arquivo_path in arquivos_c6_cartao:
            if not arquivo_path:
                continue
                
            try:
                # Ler o CSV da fatura do C6
                df = pd.read_csv(
                    arquivo_path,
                    encoding='utf-8',
                    sep=';',  # Arquivo usa ponto e vírgula como separador
                    header=0
                )
                
                df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
                
                if df.empty:
                    logger.warning(f"Arquivo vazio: {arquivo_path}")
                    continue
                
                # Processar cada transação
                for _, row in df.iterrows():
                    try:
                        # Extrair dados da linha
                        data_compra = pd.to_datetime(row['Data de Compra'], dayfirst=True, errors='coerce')
                        nome_cartao = str(row['Nome no Cartão']).strip()
                        final_cartao = str(row['Final do Cartão']).strip()
                        categoria = str(row['Categoria']).strip()
                        descricao = str(row['Descrição']).strip()
                        parcela = str(row['Parcela']).strip()
                        valor_usd = pd.to_numeric(row['Valor (em US$)'], errors='coerce')
                        cotacao = pd.to_numeric(row['Cotação (em R$)'], errors='coerce')
                        valor_brl = pd.to_numeric(row['Valor (em R$)'], errors='coerce')
                        
                        # Pular linhas com dados inválidos
                        if pd.isna(data_compra) or pd.isna(valor_brl) or valor_brl == 0:
                            continue
                        
                        # Criar identificação do cartão
                        agencia_conta = f"{final_cartao} - {nome_cartao}"
                        
                        # Criar descrição completa
                        descricao_completa = descricao
                        if valor_usd > 0:
                            descricao_completa += f" (US$ {valor_usd:.2f})"
                        if parcela != "Única":
                            descricao_completa += f" - {parcela}"
                        
                        # Para cartão de crédito:
                        # - Gastos são negativos (saídas)
                        # - Pagamentos/estornos seriam positivos (entradas)
                        valor_final = -abs(valor_brl)  # Gasto sempre negativo
                        entrada = 0.0
                        saida = abs(valor_brl)
                        
                        # Se o valor original fosse negativo (estorno), inverter
                        if valor_brl < 0:
                            valor_final = abs(valor_brl)
                            entrada = abs(valor_brl)
                            saida = 0.0
                        
                        transacao = {
                            'Data': data_compra,
                            'Data_Contabil': data_compra,
                            'Banco': 'C6 Bank',
                            'Agencia_Conta': agencia_conta,
                            'Tipo_Transacao': categoria,
                            'Descricao': descricao_completa,
                            'Valor': valor_final,
                            'Valor_Entrada': entrada,
                            'Valor_Saida': saida
                        }
                        
                        todas_transacoes.append(transacao)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao processar linha: {e}")
                        continue
                
                logger.info(f"✅ Transações processadas do arquivo: {arquivo_path}")
                
            except Exception as e:
                logger.error(f"Erro ao processar arquivo {arquivo_path}: {e}")
                continue
        
        if not todas_transacoes:
            logger.warning("Nenhuma transação encontrada nos arquivos")
            return pd.DataFrame()
        
        # Criar DataFrame padronizado
        data_dict = {
            'Data': [t['Data'] for t in todas_transacoes],
            'Data_Contabil': [t['Data_Contabil'] for t in todas_transacoes],
            'Banco': [t['Banco'] for t in todas_transacoes],
            'Agencia_Conta': [t['Agencia_Conta'] for t in todas_transacoes],
            'Tipo_Transacao': [t['Tipo_Transacao'] for t in todas_transacoes],
            'Descricao': [t['Descricao'] for t in todas_transacoes],
            'Valor': [t['Valor'] for t in todas_transacoes],
            'Valor_Entrada': [t['Valor_Entrada'] for t in todas_transacoes],
            'Valor_Saida': [t['Valor_Saida'] for t in todas_transacoes]
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        
        # Aplicar categorização automática
        resultado['Categoria_Auto'] = resultado.apply(
            lambda row: _categorizar_c6_cartao(row, config), axis=1
        )
        
        logger.info(f"✅ {len(resultado)} transações processadas do cartão C6")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar cartão C6: {e}")
        import traceback
        logger.debug(f"📝 Detalhes do erro: {traceback.format_exc()}")
        return pd.DataFrame()


def _categorizar_c6_cartao(row, config):
    """Categorização específica para cartão C6"""
    # Para cartões de crédito, usar categoria padrão
    return "Cartão Crédito"
