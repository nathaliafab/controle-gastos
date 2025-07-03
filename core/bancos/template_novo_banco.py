"""
Template para criar processador de novo banco.

Para adicionar um novo banco ao sistema:

1. Copie este arquivo e renomeie para 'nome_do_banco.py'
2. Implemente a função processar() com a lógica específica do banco
3. Adicione o processador no arquivo bancos/__init__.py
4. Atualize o config.json com as configurações do novo banco

Exemplo de uso:
from bancos.novo_banco import processar
"""

import pandas as pd
from utils import categorizar_transacao_auto, criar_dataframe_padronizado


def processar(config: dict) -> pd.DataFrame:
    """
    Processa extrato do [NOME DO BANCO]
    
    Args:
        config: Dicionário com configurações do sistema
        
    Returns:
        DataFrame com as transações processadas no formato padronizado
    """
    print("📊 Processando [NOME DO BANCO]...")
    
    try:
        # ETAPA 1: Ler arquivo do banco
        # Adapte os parâmetros para o formato específico do seu banco
        df = pd.read_csv(
            config['arquivos']['nome_do_banco'],  # Chave no config.json
            encoding='utf-8',  # ou 'latin1', 'utf-8-sig', etc.
            sep=',',  # ou ';', '\t', etc.
            skiprows=config['processamento']['skip_rows_nome_banco']  # Linhas a pular
        )
        
        # ETAPA 2: Limpar dados
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        if df.empty:
            print("   ⚠️  Arquivo vazio")
            return pd.DataFrame()
        
        # ETAPA 3: Extrair saldo anterior (se aplicável)
        # _extrair_saldo_anterior(df, config)
        
        # ETAPA 4: Processar valores
        # Adapte para as colunas específicas do seu banco
        # Exemplo:
        # df['entrada_num'] = pd.to_numeric(df['Coluna_Entrada'], errors='coerce')
        # df['saida_num'] = pd.to_numeric(df['Coluna_Saida'], errors='coerce')
        # df['valor'] = df['entrada_num'] - df['saida_num']
        
        # ETAPA 5: Criar DataFrame padronizado
        data_dict = {
            'Data': pd.to_datetime(df['Coluna_Data'], dayfirst=True, errors='coerce'),
            'Data_Contabil': pd.to_datetime(df['Coluna_Data_Contabil'], dayfirst=True, errors='coerce'),
            'Banco': 'Nome do Banco',
            'Tipo_Transacao': df['Coluna_Tipo'],
            'Descricao': df['Coluna_Descricao'],
            'Valor': df['valor_calculado'],
            'Valor_Entrada': df['entrada_calculada'],
            'Valor_Saida': df['saida_calculada']
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        
        # ETAPA 6: Remover linhas inválidas e categorizar
        resultado = resultado.dropna(subset=['Data'])
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
    """
    Extrai o saldo anterior do banco e atualiza config
    
    Args:
        df: DataFrame com dados do extrato
        config: Configurações do sistema para atualizar
    """
    try:
        # Adapte a lógica para encontrar o saldo anterior
        # Exemplo:
        # saldo_anterior_linhas = df[df['Coluna'].str.contains('SALDO ANTERIOR', na=False)]
        # if not saldo_anterior_linhas.empty:
        #     saldo_anterior = float(saldo_anterior_linhas.iloc[0]['Valor'])
        #     print(f"   💰 Saldo anterior extraído: R$ {saldo_anterior:.2f}")
        #     config['saldos_iniciais']['nome_do_banco'] = saldo_anterior
        pass
    except Exception as e:
        print(f"   ⚠️  Erro ao extrair saldo anterior: {e}")


# Funções auxiliares específicas do banco (se necessário)
# def _funcao_auxiliar_especifica():
#     """Função auxiliar específica para este banco"""
#     pass
