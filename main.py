#!/usr/bin/env python3
"""
Sistema de Controle de Gastos
Launcher principal que detecta automaticamente se deve usar interface web ou terminal.
"""

import sys
import os
from pathlib import Path

# Adicionar diretórios ao path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir / "core"))
sys.path.insert(0, str(root_dir / "web_interface"))

# Configurar logging
from core.logger import get_logger
logger = get_logger(__name__)


def setup_django_environment():
    """Configurar ambiente Django para desenvolvimento"""
    web_dir = root_dir / "web_interface"
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_extratos.settings')
    sys.path.insert(0, str(web_dir))
    return web_dir


def main():
    # Se não houver argumentos, usar interface web
    if len(sys.argv) == 1:
        try:
            from django.core.management import execute_from_command_line
            
            logger.info("🌐 Iniciando interface web...")
            logger.info("⚡ Para usar via terminal: python3 core/main_terminal.py --help")
            
            # Configurar ambiente Django
            web_dir = setup_django_environment()
            manage_py = str(web_dir / "manage.py")
            
            # Executar migrações
            logger.info("Verificando migrações...")
            try:
                execute_from_command_line([manage_py, 'migrate', '--verbosity=0'])
            except Exception as e:
                logger.warning(f"Erro ao executar migrações: {e}")
            
            # Iniciar servidor HTTP simples
            logger.info("🌐 Iniciando servidor HTTP...")
            logger.info("📝 Acesse: http://127.0.0.1:8000/")
            execute_from_command_line([manage_py, 'runserver', '127.0.0.1:8000'])
            
            return
            
        except ImportError as e:
            logger.warning(f"Django não encontrado: {e}")
            logger.info("📋 Para instalar: pip install -r web_interface/requirements-web.txt")
        except Exception as e:
            logger.error(f"Erro ao iniciar interface web: {e}")
    
    # Usar interface de terminal
    logger.info("💻 Usando interface de terminal...")
    try:
        from core.main_terminal import main as terminal_main
        terminal_main()
    except Exception as e:
        logger.error(f"Erro ao iniciar interface de terminal: {e}")
        logger.info("📋 Verifique as dependências: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
