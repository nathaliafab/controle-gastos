import os
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from pathlib import Path

logger = logging.getLogger(__name__)

class PeriodicFileCleanupMiddleware(MiddlewareMixin):
    CLEANUP_INTERVAL_SECONDS = 120*5  # 10 minutos
    TARGET_FOLDER = Path("media/resultados")  # pasta onde os arquivos estão
    TIMESTAMP_FILE = TARGET_FOLDER / ".last_cleanup"

    def process_request(self, request):
        now = time.time()

        # Cria pasta e arquivo de timestamp se não existirem
        self.TARGET_FOLDER.mkdir(parents=True, exist_ok=True)
        if not self.TIMESTAMP_FILE.exists():
            self.TIMESTAMP_FILE.write_text(str(now))
            return

        # Lê o tempo da última limpeza
        try:
            last_cleanup = float(self.TIMESTAMP_FILE.read_text())
        except ValueError:
            last_cleanup = 0

        if now - last_cleanup >= self.CLEANUP_INTERVAL_SECONDS:
            self.clean_folder()
            self.TIMESTAMP_FILE.write_text(str(now))

    def clean_folder(self):
        now = time.time()
        for file in self.TARGET_FOLDER.iterdir():
            if (
                file.is_file()
                and file.name != ".gitkeep"
                and file.name != ".last_cleanup"
            ):
                # Não apaga arquivos criados nos últimos 5 minutos
                if now - file.stat().st_mtime < 5 * 60:
                    continue
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Erro ao apagar {file.name}: {e}")