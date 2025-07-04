"""
Processador principal de extratos bancários - orquestração do processamento.
"""

import pandas as pd
from pathlib import Path
from bancos import PROCESSADORES, MAPEAMENTO_ARQUIVOS, NOMES_BANCOS
from utils import calcular_saldos, detectar_transferencias_proprias, gerar_relatorio, gerar_nome_arquivo_timestamped
from config_manager import COLUNAS_PADRONIZADAS
from logger import get_logger

logger = get_logger(__name__)


def verificar_e_filtrar_bancos(bancos_para_processar, config):
    """Verifica arquivos e retorna lista de bancos válidos e lista de avisos."""
    bancos_validos = []
    avisos = []
    
    for banco in bancos_para_processar:
        arquivo_key = MAPEAMENTO_ARQUIVOS[banco]
        
        # Verificar se a chave existe na configuração
        if arquivo_key not in config.get('arquivos', {}):
            avisos.append(f"{banco.upper()}: Configuração não encontrada para '{arquivo_key}'")
            continue
            
        arquivos = config['arquivos'][arquivo_key]
        
        banco_tem_arquivos = False
        arquivos_faltando_banco = []
        
        if isinstance(arquivos, str):
            if arquivos and Path(arquivos).exists():
                banco_tem_arquivos = True
            elif arquivos:
                arquivos_faltando_banco.append(arquivos)
        elif isinstance(arquivos, list):
            for arquivo in arquivos:
                if arquivo and Path(arquivo).exists():
                    banco_tem_arquivos = True
                elif arquivo:
                    arquivos_faltando_banco.append(arquivo)
        
        if banco_tem_arquivos:
            bancos_validos.append(banco)
        else:
            # Adicionar aviso sobre arquivos faltando
            if arquivos_faltando_banco:
                for arquivo in arquivos_faltando_banco:
                    avisos.append(f"{banco.upper()}: {arquivo}")
            else:
                avisos.append(f"{banco.upper()}: Nenhum arquivo configurado")
    
    return bancos_validos, avisos


def determinar_bancos_processar(args):
    if args.all:
        bancos_para_processar = ['c6', 'bradesco', 'bb', 'bb_cartao', 'itau']
        logger.info("Modo: TODOS OS BANCOS")
    else:
        bancos_para_processar = []
        if args.c6:
            bancos_para_processar.append('c6')
        if args.bradesco:
            bancos_para_processar.append('bradesco')
        if args.bb:
            bancos_para_processar.append('bb')
        if args.bb_cartao:
            bancos_para_processar.append('bb_cartao')
        if args.itau:
            bancos_para_processar.append('itau')
        
        bancos_selecionados = [NOMES_BANCOS[b] for b in bancos_para_processar]
        logger.info(f"Modo: BANCOS SELECIONADOS - {', '.join(bancos_selecionados)}")
    
    return bancos_para_processar


def processar_bancos(bancos_para_processar, config):
    logger.info(f"Processando extratos dos bancos selecionados...")
    dfs = []
    
    for banco in bancos_para_processar:
        arquivo_key = MAPEAMENTO_ARQUIVOS[banco]
        
        # Verificar se a chave existe na configuração
        if arquivo_key not in config.get('arquivos', {}):
            logger.warning(f"{banco.upper()}: Configuração não encontrada para '{arquivo_key}' - ignorando")
            continue
            
        arquivos = config['arquivos'][arquivo_key]
        
        tem_arquivos = False
        if isinstance(arquivos, str):
            tem_arquivos = arquivos and Path(arquivos).exists()
        elif isinstance(arquivos, list):
            tem_arquivos = any(arquivo and Path(arquivo).exists() for arquivo in arquivos)
        
        if tem_arquivos:
            try:
                df_resultado = PROCESSADORES[banco](config)
                if not df_resultado.empty:
                    dfs.append(df_resultado)
                    logger.info(f"✅ {banco.upper()}: Processado com sucesso")
                else:
                    logger.warning(f"{banco.upper()}: Nenhum dado encontrado")
            except Exception as e:
                logger.error(f"{banco.upper()}: Erro ao processar - {str(e)}")
        else:
            logger.warning(f"{banco.upper()}: Arquivos não encontrados - ignorando")
    
    return dfs


def consolidar_dados(dfs):
    if not dfs:
        logger.error("Nenhum extrato foi processado com sucesso!")
        return None
    
    logger.info(f"🔗 Consolidando dados...")
    df_consolidado = pd.concat(dfs, ignore_index=True)
    
    transacoes_antes = len(df_consolidado)
    df_consolidado = df_consolidado[df_consolidado['Valor'] != 0]
    transacoes_removidas = transacoes_antes - len(df_consolidado)
    
    if transacoes_removidas > 0:
        logger.info(f"Removidas transação(ões) com valor zerado")
    
    df_consolidado = df_consolidado.sort_values('Data').reset_index(drop=True)
    
    df_consolidado['Categoria'] = ''
    df_consolidado['Descricao_Manual'] = ''
    
    return df_consolidado




def exportar_excel(df_consolidado, arquivo_output):
    logger.info(f"📄 Gerando planilha Excel...")
    try:
        df_consolidado.to_excel(arquivo_output, index=False)
        logger.info(f"✅ Arquivo criado com sucesso!")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar Excel: {e}")
        return False


def processar_extratos(args, config):
    bancos_para_processar = determinar_bancos_processar(args)
    
    logger.info("🏦 PROCESSADOR DE EXTRATOS BANCÁRIOS")
    
    # Verificar e filtrar bancos com arquivos válidos
    bancos_validos, avisos = verificar_e_filtrar_bancos(bancos_para_processar, config)
    
    # Mostrar avisos sobre arquivos faltando, mas continuar processamento
    if avisos:
        logger.warning("Arquivos não encontrados (bancos serão ignorados):")
        for aviso in avisos:
            logger.warning(f"• {aviso}")
        logger.info("💡 Dica: Verifique os caminhos no arquivo config.json")
    
    # Verificar se há pelo menos um banco válido
    if not bancos_validos:
        logger.error("Nenhum banco tem arquivos válidos para processar!")
        logger.info("💡 Verifique se os caminhos dos arquivos estão corretos no config.json")
        return False
    
    # Mostrar bancos que serão processados
    bancos_validos_nomes = [NOMES_BANCOS[b] for b in bancos_validos]
    logger.info(f"✅ Processando bancos: {', '.join(bancos_validos_nomes)}")
    
    dfs = processar_bancos(bancos_validos, config)
    
    df_consolidado = consolidar_dados(dfs)
    if df_consolidado is None:
        return False
    
    logger.info(f"🧮 Calculando saldos...")
    df_consolidado = calcular_saldos(df_consolidado, config)
    detectar_transferencias_proprias(df_consolidado, config)
    
    df_consolidado = df_consolidado[COLUNAS_PADRONIZADAS]
    
    arquivo_output = args.output if args.output else gerar_nome_arquivo_timestamped(config['arquivos']['output'])
    exportar_excel(df_consolidado, arquivo_output)
    
    gerar_relatorio(df_consolidado)
    
    logger.info("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    
    return True