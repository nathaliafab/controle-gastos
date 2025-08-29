"""
Módulo de processadores de bancos.
Cada banco tem seu próprio arquivo com a lógica específica de processamento.
"""

from .c6 import processar as processar_c6
from .c6_cartao import processar as processar_c6_cartao
from .bradesco import processar as processar_bradesco  
from .bb import processar as processar_bb
from .bb_cartao import processar as processar_bb_cartao
from .itau import processar as processar_itau

# Mapeamento dos processadores
PROCESSADORES = {
    'c6': processar_c6,
    'c6_cartao': processar_c6_cartao,
    'bradesco': processar_bradesco,
    'bb': processar_bb,
    'bb_cartao': processar_bb_cartao,
    'itau': processar_itau
}

# Mapeamento de chaves de arquivos no config
MAPEAMENTO_ARQUIVOS = {
    'c6': 'c6_bank',
    'c6_cartao': 'c6_cartao',
    'bradesco': 'bradesco',
    'bb': 'bb',
    'bb_cartao': 'bb_cartao',
    'itau': 'itau'
}

# Nomes amigáveis dos bancos
NOMES_BANCOS = {
    'c6': 'C6 Bank',
    'c6_cartao': 'C6 Cartão',
    'bradesco': 'Bradesco',
    'bb': 'BB Conta Corrente',
    'bb_cartao': 'BB Cartão',
    'itau': 'Itaú'
}
