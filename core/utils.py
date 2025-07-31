"""
Utilitários compartilhados para processamento de extratos bancários.
"""

import pandas as pd
import re
from datetime import datetime
from logger import get_logger

logger = get_logger(__name__)


def extrair_agencia_conta(arquivo_path: str, banco: str) -> str:
    try:
        if banco == 'C6 Bank':
            with open(arquivo_path, 'r', encoding='utf-8') as f:
                primeiras_linhas = f.read(500)
                match = re.search(r'Agência:\s*(\d+)\s*/\s*Conta:\s*(\d+)', primeiras_linhas)
                if match:
                    return f"Ag: {match.group(1)} / Conta: {match.group(2)}"
                
        elif banco == 'Bradesco':
            with open(arquivo_path, 'r', encoding='utf-8') as f:
                primeira_linha = f.readline()
                match = re.search(r'Ag:\s*(\d+)\s*\|\s*Conta:\s*([\d-]+)', primeira_linha)
                if match:
                    return f"Ag: {match.group(1)} / Conta: {match.group(2)}"
                    
        elif banco == 'Banco do Brasil':
            return "BB Principal"
            
        elif banco == 'BB Cartão':
            return "BB Cartão de Crédito"
            
        elif banco == 'Itaú':
            if arquivo_path.endswith('.xls') or arquivo_path.endswith('.xlsx'):
                try:
                    df = pd.read_excel(arquivo_path, engine='xlrd' if arquivo_path.endswith('.xls') else None, header=None)
                    
                    agencia = None
                    conta = None
                    nome_cartao = None
                    
                    for i in range(min(15, len(df))):
                        linha = df.iloc[i]
                        linha_str = ' '.join([str(x) for x in linha.dropna()])
                        
                        if 'Agência:' in linha_str:
                            match = re.search(r'Agência:\s*(\d+)', linha_str)
                            if match:
                                agencia = match.group(1)
                        
                        if 'Conta:' in linha_str:
                            match = re.search(r'Conta:\s*([\d-]+)', linha_str)
                            if match:
                                conta = match.group(1)
                        
                        # Para cartão de crédito, buscar o nome/final do cartão
                        if 'final' in linha_str.lower() and any(x in linha_str.lower() for x in ['cartão', 'card']):
                            nome_cartao = linha_str.strip()
                    
                    # Se encontrou agência e conta (conta corrente)
                    if agencia and conta:
                        return f"Ag: {agencia} / Conta: {conta}"
                    
                    # Se é cartão de crédito
                    if nome_cartao:
                        return f"Itaú {nome_cartao}"
                    
                    # Fallback baseado no nome do arquivo
                    if 'cartao' in arquivo_path.lower() or arquivo_path.endswith('.xlsx'):
                        return "Itaú Cartão de Crédito"
                    else:
                        return "Itaú Conta Corrente"
                        
                except Exception as e:
                    return "Itaú"
            
    except Exception as e:
        pass
    
    return banco


def gerar_nome_arquivo_timestamped(base_path: str) -> str:
    """Gerar nome de arquivo com timestamp baseado no caminho base fornecido"""
    from pathlib import Path
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    # Se base_path já contém um nome de arquivo, usar o diretório
    base_path = Path(base_path)
    if base_path.suffix:  # Se tem extensão, é um arquivo
        diretorio = base_path.parent
        nome_base = base_path.stem
    else:  # Se não tem extensão, é um diretório
        diretorio = base_path
        nome_base = "controle_gastos"
    
    arquivo_final = diretorio / f"{nome_base}_{timestamp}.xlsx"
    return str(arquivo_final)


def categorizar_transacao_auto(tipo: str, descricao: str, valor: float, categorias: dict, agencia_conta: str = "") -> str:
    
    if agencia_conta and ' - ' in agencia_conta and agencia_conta.split(' - ')[0].isdigit():
        return 'Cartão Crédito'
    
    texto = f"{str(tipo).upper()} {str(descricao).upper()}"
    
    # Verificar se é estorno primeiro
    if any(palavra in texto for palavra in categorias['estornos']):
        # Se é estorno, verificar do que é estorno
        if any(palavra in texto for palavra in categorias['investimentos']):
            return 'Investimentos'
        elif any(palavra in texto for palavra in categorias['cartao_credito']):
            return 'Cartão Crédito'
        elif any(palavra in texto for palavra in categorias['cartao_debito']):
            return 'Cartão Débito'
        elif any(palavra in texto for palavra in categorias['debito_automatico']):
            return 'Débito Automático'
        else:
            return 'Estornos'
    
    # Verificar categorias específicas
    for categoria, palavras in categorias.items():
        if any(palavra in texto for palavra in palavras):
            if categoria == 'investimentos':
                return 'Investimentos'
            elif categoria == 'rendimentos':
                return 'Rendimentos'
            elif categoria == 'pix_transferencia':
                return 'PIX Recebido' if valor > 0 else 'PIX Enviado'
            elif categoria == 'cartao_credito':
                return 'Cartão Crédito'
            elif categoria == 'cartao_debito':
                return 'Cartão Débito'
            elif categoria == 'debito_automatico':
                return 'Débito Automático'
            elif categoria == 'tarifas':
                return 'Tarifas'
            elif categoria == 'saques':
                return 'Saques'
            elif categoria == 'depositos':
                return 'Depósitos'
    
    return 'Outros'


def converter_valor_br(valor):
    """Converte valores brasileiros (1.234,56 → 1234.56)"""
    return pd.to_numeric(str(valor).replace('.', '').replace(',', '.'), errors='coerce')


def criar_dataframe_padronizado(data_dict: dict) -> pd.DataFrame:
    """Cria um DataFrame com a estrutura padronizada"""
    return pd.DataFrame({
        'Data': data_dict.get('Data'),
        'Data_Contabil': data_dict.get('Data_Contabil'),
        'Banco': data_dict.get('Banco'),
        'Agencia_Conta': data_dict.get('Agencia_Conta'),
        'Tipo_Transacao': data_dict.get('Tipo_Transacao'),
        'Descricao': data_dict.get('Descricao'),
        'Valor': data_dict.get('Valor'),
        'Valor_Entrada': data_dict.get('Valor_Entrada'),
        'Valor_Saida': data_dict.get('Valor_Saida')
    })


def calcular_saldos(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Calcula as colunas Saldo_Real e Saldo_no_Banco"""
    if df.empty:
        return df
    
    # Ordenar por data para cálculo sequencial
    df = df.sort_values(['Data_Contabil', 'Data']).reset_index(drop=True)
    
    # Inicializar saldos
    saldos_iniciais = config['saldos_iniciais']
    saldo_bb = saldos_iniciais['bb']
    saldo_bradesco = saldos_iniciais['bradesco']
    saldo_c6 = saldos_iniciais['c6_bank']
    saldo_itau = saldos_iniciais.get('itau', 0.0)
    
    # Saldo real inicial é a soma dos saldos iniciais dos bancos
    saldo_real = saldo_bb + saldo_bradesco + saldo_c6 + saldo_itau
    
    # Listas para armazenar os saldos
    saldos_no_banco = []
    saldos_reais = []
    
    for _, transacao in df.iterrows():
        banco = transacao['Banco']
        valor = transacao['Valor']
        categoria = transacao['Categoria_Auto']
        
        eh_cartao_credito = categoria == 'Cartão Crédito'
        eh_transferencia_propria = categoria == 'Transferência Própria'
        
        # Não alterar saldos para transferências próprias
        if not eh_cartao_credito and not eh_transferencia_propria:
            if banco == 'Banco do Brasil':
                saldo_bb += valor
            elif banco == 'Bradesco':
                saldo_bradesco += valor
            elif banco == 'C6 Bank':
                saldo_c6 += valor
            elif banco == 'Itaú':
                saldo_itau += valor
        
        saldo_no_banco_atual = saldo_bb + saldo_bradesco + saldo_c6 + saldo_itau
        saldos_no_banco.append(saldo_no_banco_atual)
        
        # Saldo real: considera TODAS as transações (incluindo cartão de crédito), exceto transferências próprias
        if not eh_transferencia_propria:
            saldo_real += valor
        saldos_reais.append(saldo_real)
    
    # Adicionar as colunas ao DataFrame
    df['Saldo_no_Banco'] = saldos_no_banco
    df['Saldo_Real'] = saldos_reais
    
    return df


def detectar_transferencias_proprias(df: pd.DataFrame, config: dict) -> int:
    transferencias_detectadas = 0
    usuario_config = config['usuario']
    nome = usuario_config['nome']
    cpf = usuario_config['cpf']
    processamento_config = config['processamento']
    
    mask_propria = (
        df['Categoria_Auto'].isin(['PIX Enviado', 'PIX Recebido']) &
        (df['Descricao'].str.contains(f'{nome}|{cpf}', case=False, na=False) |
         df['Tipo_Transacao'].str.contains(f'{nome}|{cpf}', case=False, na=False))
    )
    
    df.loc[mask_propria, 'Categoria_Auto'] = 'Transferência Própria'
    transferencias_detectadas += mask_propria.sum()
    
    tolerancia_valor = processamento_config['tolerancia_valor']
    janela_dias = processamento_config['janela_transferencias_dias']
    
    pix_todos = df[df['Categoria_Auto'].isin(['PIX Enviado', 'PIX Recebido', 'Transferência Própria'])].copy()
    
    pix_enviados = pix_todos[pix_todos['Valor'] < 0].copy()
    pix_recebidos = pix_todos[pix_todos['Valor'] > 0].copy()
    
    indices_processados = set()
    pares_detectados = 0
    for idx_enviado, pix_env in pix_enviados.iterrows():
        if idx_enviado in indices_processados:
            continue
            
        valor_env = abs(pix_env['Valor'])
        data_env = pix_env['Data_Contabil']
        banco_env = pix_env['Banco']
        desc_env = str(pix_env['Descricao']).upper()
        tipo_env = str(pix_env['Tipo_Transacao']).upper()
        texto_completo_env = f"{desc_env} {tipo_env}"
        
        # Procurar PIX recebidos correspondentes
        for idx_recebido, pix_rec in pix_recebidos.iterrows():
            if idx_recebido in indices_processados:
                continue
                
            valor_rec = pix_rec['Valor']
            data_rec = pix_rec['Data_Contabil']
            banco_rec = pix_rec['Banco']
            desc_rec = str(pix_rec['Descricao']).upper()
            tipo_rec = str(pix_rec['Tipo_Transacao']).upper()
            texto_completo_rec = f"{desc_rec} {tipo_rec}"
            
            # CRITÉRIO 1: Deve ser entre bancos diferentes
            if banco_env == banco_rec:
                continue
                
            # CRITÉRIO 2: Tolerância de valor
            if abs(valor_env - valor_rec) > tolerancia_valor:
                continue
                
            # CRITÉRIO 3: Janela de tempo
            diferenca_dias = abs((data_rec - data_env).days)
            if diferenca_dias > janela_dias:
                continue
            
            # CRITÉRIO 4: Verificar se contém dados do usuário (descrição + tipo_transacao)
            contem_dados_env = (nome.upper() in texto_completo_env or cpf in texto_completo_env)
            contem_dados_rec = (nome.upper() in texto_completo_rec or cpf in texto_completo_rec)
            
            # CRITÉRIO 5: Detectar se são transferências genéricas do banco
            padroes_genericos = ['TRANSFERENCIA PIX', 'TRANSF ENVIADA PIX']
            eh_generica_env = any(padrao in texto_completo_env for padrao in padroes_genericos)
            eh_generica_rec = any(padrao in texto_completo_rec for padrao in padroes_genericos)
            
            # DECISÃO: É transferência própria se pelo menos uma das partes tem meus dados 
            # E a outra é genérica ou também tem meus dados
            eh_transferencia_propria = (
                (contem_dados_env and (eh_generica_rec or contem_dados_rec)) or
                (contem_dados_rec and (eh_generica_env or contem_dados_env))
            )
            
            if eh_transferencia_propria:
                df.at[idx_enviado, 'Categoria_Auto'] = 'Transferência Própria'
                df.at[idx_recebido, 'Categoria_Auto'] = 'Transferência Própria'
                
                indices_processados.add(idx_enviado)
                indices_processados.add(idx_recebido)
                
                transferencias_detectadas += 2
                pares_detectados += 1
                break
    
    transferencias_proprias = df[df['Categoria_Auto'] == 'Transferência Própria'].copy()
    recategorizadas = 0
    
    if not transferencias_proprias.empty:
        
        indices_com_par = set()
        
        # Primeiro, identificar quais transferências têm par
        for idx1, transf1 in transferencias_proprias.iterrows():
            if idx1 in indices_com_par:
                continue
                
            valor1 = transf1['Valor']
            data1 = transf1['Data_Contabil']
            banco1 = transf1['Banco']
            
            # Procurar par correspondente
            for idx2, transf2 in transferencias_proprias.iterrows():
                if idx2 == idx1 or idx2 in indices_com_par:
                    continue
                    
                valor2 = transf2['Valor']
                data2 = transf2['Data_Contabil']
                banco2 = transf2['Banco']
                
                # Verificar se formam um par válido:
                # - Valores opostos (entrada/saída) com tolerância
                # - Bancos diferentes
                # - Datas próximas
                valores_opostos = ((valor1 > 0 and valor2 < 0) or (valor1 < 0 and valor2 > 0))
                valores_similares = abs(abs(valor1) - abs(valor2)) <= tolerancia_valor
                bancos_diferentes = banco1 != banco2
                datas_proximas = abs((data2 - data1).days) <= janela_dias
                
                if valores_opostos and valores_similares and bancos_diferentes and datas_proximas:
                    indices_com_par.add(idx1)
                    indices_com_par.add(idx2)
                    break
        
        # Agora recategorizar as transferências sem par
        for idx, transf in transferencias_proprias.iterrows():
            if idx not in indices_com_par:  # Não tem par
                valor = transf['Valor']
                banco = transf['Banco']
                data = transf['Data_Contabil']
                
                if valor > 0:
                    df.at[idx, 'Categoria_Auto'] = 'PIX Recebido'
                else:
                    df.at[idx, 'Categoria_Auto'] = 'PIX Enviado'
                
                recategorizadas += 1
    
    pix_sem_par = df[df['Categoria_Auto'].isin(['PIX Enviado', 'PIX Recebido'])]
    
    return transferencias_detectadas


def gerar_relatorio(df: pd.DataFrame):
    logger.info(f"📊 RELATÓRIO CONSOLIDADO")
    
    total_transacoes = len(df)
    periodo_inicio = df['Data'].min().strftime('%d/%m/%Y')
    periodo_fim = df['Data'].max().strftime('%d/%m/%Y')
    
    logger.info(f"📅 Período: {periodo_inicio} a {periodo_fim}")
    logger.info(f"📈 Relatório processado")
    

