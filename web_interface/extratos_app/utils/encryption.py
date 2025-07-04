"""
Utilitários para criptografia de dados sensíveis
Sistema simplificado para funcionar sem dependências externas
"""
import os
import base64
import hashlib
import hmac
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DataEncryption:
    """Classe para criptografia e descriptografia de dados sensíveis"""
    
    def __init__(self):
        self.key = self._get_encryption_key()
    
    def _get_encryption_key(self):
        """Gera ou recupera a chave de criptografia"""
        # Usar variável de ambiente se disponível
        env_key = os.environ.get('ENCRYPTION_KEY')
        if env_key:
            return env_key.encode('utf-8')
        
        # Fallback para SECRET_KEY do Django
        return settings.SECRET_KEY.encode('utf-8')
    
    def encrypt(self, data):
        """Criptografa dados usando XOR simples com hash"""
        if not data:
            return data
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Gerar hash da chave para usar como cipher
            key_hash = hashlib.sha256(self.key).digest()
            
            # XOR simples
            encrypted = bytearray()
            for i, byte in enumerate(data):
                encrypted.append(byte ^ key_hash[i % len(key_hash)])
            
            # Codificar em base64
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao criptografar dados: {e}")
            raise
    
    def decrypt(self, encrypted_data):
        """Descriptografa dados"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Decodificar base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # Gerar hash da chave para usar como cipher
            key_hash = hashlib.sha256(self.key).digest()
            
            # XOR reverso
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ key_hash[i % len(key_hash)])
            
            return decrypted.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao descriptografar dados: {e}")
            raise
    
    def hash_cpf(self, cpf):
        """Gera hash irreversível do CPF para identificação"""
        if not cpf:
            return None
        
        # Remove caracteres não numéricos
        clean_cpf = ''.join(filter(str.isdigit, cpf))
        
        # Gera hash SHA-256 com salt
        salt = self.key + b'cpf_salt'
        hash_obj = hashlib.sha256()
        hash_obj.update(clean_cpf.encode('utf-8'))
        hash_obj.update(salt)
        
        return hash_obj.hexdigest()[:16]  # Retorna primeiros 16 caracteres
    
    def generate_secure_token(self, length=32):
        """Gera token seguro para sessões"""
        return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8')
    
    def validate_integrity(self, data, signature):
        """Valida integridade dos dados usando HMAC"""
        if not data or not signature:
            return False
        
        try:
            expected_sig = hmac.new(
                self.key, 
                data.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_sig)
        
        except Exception as e:
            logger.error(f"Erro na validação de integridade: {e}")
            return False
    
    def sign_data(self, data):
        """Assina dados para garantir integridade"""
        if not data:
            return None
        
        try:
            signature = hmac.new(
                self.key, 
                data.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            
            return signature
        
        except Exception as e:
            logger.error(f"Erro ao assinar dados: {e}")
            raise

# Instância global
encryption = DataEncryption()
