"""
Sistema de logging seguro para dados financeiros
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional

class SecureLogger:
    """Logger que remove dados sensíveis automaticamente"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.sensitive_patterns = [
            r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b',  # CPF formatado
            r'\b\d{11}\b',  # CPF sem formatação
            r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Cartão de crédito
            r'\b\d{5}-\d{1}\b',  # Conta bancária
            r'\b\d{1,5}-\d{1}\b',  # Agência
            r'valor["\']?\s*:\s*["\']?[\d,.]+'  # Valores monetários
        ]
    
    def _sanitize_message(self, message: str) -> str:
        """Remove dados sensíveis da mensagem"""
        sanitized = message
        
        # Remover CPF
        sanitized = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', 'XXX.XXX.XXX-XX', sanitized)
        sanitized = re.sub(r'\b\d{11}\b', 'XXXXXXXXXXX', sanitized)
        
        # Remover cartões
        sanitized = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b', 'XXXX XXXX XXXX XXXX', sanitized)
        
        # Remover contas
        sanitized = re.sub(r'\b\d{5}-\d{1}\b', 'XXXXX-X', sanitized)
        sanitized = re.sub(r'\b\d{1,5}-\d{1}\b', 'XXXXX-X', sanitized)
        
        # Remover valores (manter apenas estrutura)
        sanitized = re.sub(r'(valor["\']?\s*:\s*["\']?)[\d,.]+', r'\1XXX.XX', sanitized)
        
        return sanitized
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitiza dados recursivamente"""
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_message(data)
        else:
            return data
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info com sanitização"""
        clean_message = self._sanitize_message(message)
        clean_extra = self._sanitize_data(extra) if extra else None
        self.logger.info(clean_message, extra=clean_extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning com sanitização"""
        clean_message = self._sanitize_message(message)
        clean_extra = self._sanitize_data(extra) if extra else None
        self.logger.warning(clean_message, extra=clean_extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error com sanitização"""
        clean_message = self._sanitize_message(message)
        clean_extra = self._sanitize_data(extra) if extra else None
        self.logger.error(clean_message, extra=clean_extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug com sanitização"""
        clean_message = self._sanitize_message(message)
        clean_extra = self._sanitize_data(extra) if extra else None
        self.logger.debug(clean_message, extra=clean_extra)

def get_secure_logger(name: str) -> SecureLogger:
    """Retorna um logger seguro"""
    return SecureLogger(name)

# Exemplo de uso
if __name__ == "__main__":
    logger = get_secure_logger(__name__)
    
    # Teste com dados sensíveis
    logger.info("Processando CPF: 123.456.789-01")
    logger.info("Valor da transação: R$ 1.234,56")
    logger.info("Conta: 12345-6, Agência: 1234-5")
    
    # Teste com dados estruturados
    data = {
        "usuario": {
            "cpf": "12345678901",
            "nome": "João Silva"
        },
        "transacao": {
            "valor": "1234.56",
            "conta": "12345-6"
        }
    }
    
    logger.info("Dados do processamento", extra=data)
