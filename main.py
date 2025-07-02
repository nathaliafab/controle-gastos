#!/usr/bin/env python3

import sys
from config_manager import carregar_configuracao, configurar_argumentos, validar_argumentos
from processador import processar_extratos


def main():
    parser = configurar_argumentos()
    args = parser.parse_args()
    
    if not validar_argumentos(args):
        sys.exit(1)
    
    config = carregar_configuracao()
    if config is None:
        sys.exit(1)
    
    sucesso = processar_extratos(args, config)
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    main()
