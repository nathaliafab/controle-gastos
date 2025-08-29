"""
Gerenciador de configurações do processador de extratos bancários.
"""

import json
import argparse
from pathlib import Path
from logger import get_logger

logger = get_logger(__name__)


def carregar_configuracao(arquivo_config='config.json'):
    config_path = Path(arquivo_config)
    
    if not config_path.exists():
        logger.error(f"Arquivo de configuração não encontrado!")
        logger.info("💡 Crie o arquivo config.json com suas configurações")
        logger.info("📝 Consulte o config-exemplo.json para referência")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo de configuração: {e}")
        logger.info("💡 Verifique se o arquivo está em formato JSON válido")
        return None


def configurar_argumentos():
    parser = argparse.ArgumentParser(
        description='🏦 Processador de Extratos Bancários',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python3 main.py --all                    # Processar todos os bancos
  python3 main.py --c6                     # Apenas C6 Bank conta
  python3 main.py --c6-cartao              # Apenas C6 cartão
  python3 main.py --bradesco               # Apenas Bradesco
  python3 main.py --bb                     # Apenas Banco do Brasil
  python3 main.py --bb-cartao              # Apenas cartão BB
  python3 main.py --itau                   # Apenas Itaú
  python3 main.py --b3                     # Apenas B3 (investimentos)
  python3 main.py --c6 --c6-cartao         # C6 Bank conta + cartão
  python3 main.py --bb --bb-cartao         # BB conta corrente + cartão
  python3 main.py --itau --c6              # Itaú + C6 Bank
  python3 main.py --help                   # Mostrar esta ajuda
        """
    )
    
    parser.add_argument('--all', 
                       action='store_true',
                       help='Processar todos os bancos disponíveis')
    
    parser.add_argument('--c6', 
                       action='store_true',
                       help='Processar extrato do C6 Bank')
    
    parser.add_argument('--c6-cartao', 
                       action='store_true',
                       help='Processar fatura do cartão C6')
    
    parser.add_argument('--bradesco', 
                       action='store_true',
                       help='Processar extrato do Bradesco')
    
    parser.add_argument('--bb', 
                       action='store_true',
                       help='Processar extrato do Banco do Brasil')
    
    parser.add_argument('--bb-cartao', 
                       action='store_true',
                       help='Processar fatura do cartão BB')
    
    parser.add_argument('--itau', 
                       action='store_true',
                       help='Processar extrato do Itaú')
    
    parser.add_argument('--b3', 
                       action='store_true',
                       help='Processar relatório da B3 (investimentos)')
    
    parser.add_argument('--output', 
                       type=str,
                       help='Nome do arquivo de saída (padrão do config.json)')
    
    return parser


def validar_argumentos(args):
    if not args.all and not any([args.c6, args.c6_cartao, args.bradesco, args.bb, args.bb_cartao, args.itau, args.b3]):
        logger.error("Erro: Você deve especificar --all ou pelo menos um banco específico")
        logger.info("💡 Use --help para ver os exemplos de uso")
        return False
    return True

COLUNAS_PADRONIZADAS = [
    'Data', 'Data_Contabil', 'Banco', 'Agencia_Conta', 'Tipo_Transacao', 'Descricao', 
    'Valor', 'Valor_Entrada', 'Valor_Saida', 'Categoria_Auto', 'Categoria', 'Descricao_Manual',
    'Saldo_no_Banco', 'Saldo_Real'
]
