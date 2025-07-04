"""
Sistema de logging centralizado para o controle de gastos.
Utiliza o sistema de logging seguro para dados financeiros.
"""

import logging
import os
import sys
from pathlib import Path

# Configuração básica de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

def setup_logging():
    """Configura o sistema de logging"""
    # Verificar se o logging já foi configurado
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return  # Logging já foi configurado
    
    # Criar diretório de logs se não existir
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(exist_ok=True)
    
    # Configurar formatador
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Configurar logger raiz
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Silenciar loggers de bibliotecas externas
    logging.getLogger('pdfplumber').setLevel(logging.ERROR)
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('plotly').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado"""
    return logging.getLogger(name)

# Configurar logging na importação
setup_logging()
