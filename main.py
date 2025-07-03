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


def main():
    print("🎯 Sistema de Controle de Gastos")
    print("=" * 40)
    
    # Se não houver argumentos, usar interface web
    if len(sys.argv) == 1:
        try:
            import django
            print("🌐 Iniciando interface web...")
            print("📝 Acesse: http://localhost:8000")
            print("⚡ Para usar via terminal: python3 core/main_terminal.py --help")
            print()
            
            # Mudar para o diretório da interface web
            web_dir = root_dir / "web_interface"
            os.chdir(web_dir)
            
            # Executar migrações se necessário
            os.system("python3 manage.py migrate --verbosity=0")
            
            # Iniciar servidor
            os.system("python3 manage.py runserver")
            return
            
        except ImportError:
            print("⚠️  Django não encontrado. Usando interface de terminal.")
            print("📋 Para instalar: pip install -r web_interface/requirements-web.txt")
    
    # Usar interface de terminal
    print("💻 Usando interface de terminal...")
    from core.main_terminal import main as terminal_main
    terminal_main()


if __name__ == "__main__":
    main()
