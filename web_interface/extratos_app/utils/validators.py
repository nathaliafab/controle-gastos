"""
Validadores de segurança para uploads de arquivos
"""
import os
import mimetypes
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

# Tipos de arquivo permitidos
ALLOWED_EXTENSIONS = {
    '.csv': 'text/csv',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pdf': 'application/pdf',
    '.json': 'application/json',
}

# Tamanho máximo de arquivo (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

def validate_file_type(file):
    """Valida o tipo de arquivo baseado em extensão e tamanho"""
    if not file:
        return
    
    # Verificar extensão
    name = file.name.lower()
    ext = os.path.splitext(name)[1]
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f'Tipo de arquivo não permitido: {ext}')
    
    # Verificar tamanho
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB')
    
    # Verificar mime type básico
    try:
        mime_type, _ = mimetypes.guess_type(name)
        if mime_type:
            # Verificações básicas por tipo
            if ext == '.csv' and not mime_type.startswith('text/'):
                raise ValidationError('Arquivo CSV inválido')
            elif ext in ['.xls', '.xlsx'] and not mime_type.startswith('application/'):
                raise ValidationError('Arquivo Excel inválido')
            elif ext == '.pdf' and not mime_type.startswith('application/pdf'):
                raise ValidationError('Arquivo PDF inválido')
    except Exception as e:
        logger.warning(f"Erro na validação de tipo de arquivo: {e}")
    
    # Verificar nome do arquivo
    if not validate_filename(name):
        raise ValidationError('Nome de arquivo inválido')

def validate_filename(filename):
    """Valida o nome do arquivo"""
    if not filename:
        return False
    
    # Caracteres perigosos
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|', ';', '&', '$', '`']
    
    for char in dangerous_chars:
        if char in filename:
            return False
    
    # Verificar se não é um nome de arquivo reservado
    reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']
    
    name_without_ext = os.path.splitext(filename)[0].lower()
    if name_without_ext in reserved_names:
        return False
    
    return True

def sanitize_filename(filename):
    """Sanitiza o nome do arquivo"""
    if not filename:
        return 'unnamed_file'
    
    # Remove caracteres perigosos
    safe_chars = []
    for char in filename:
        if char.isalnum() or char in ['.', '_', '-']:
            safe_chars.append(char)
        else:
            safe_chars.append('_')
    
    return ''.join(safe_chars)

def validate_json_content(file):
    """Valida o conteúdo de um arquivo JSON"""
    import json
    
    if not file:
        return
    
    try:
        file.seek(0)
        content = file.read().decode('utf-8')
        data = json.loads(content)
        
        # Validar estrutura básica
        if not isinstance(data, dict):
            raise ValidationError('Arquivo JSON deve conter um objeto')
        
        # Verificar se não há scripts maliciosos
        json_str = json.dumps(data)
        dangerous_patterns = ['<script', 'javascript:', 'eval(', 'setTimeout(', 'setInterval(', 'function(', 'new Function']
        
        for pattern in dangerous_patterns:
            if pattern.lower() in json_str.lower():
                raise ValidationError('Conteúdo potencialmente malicioso no arquivo JSON')
        
        file.seek(0)
        
    except json.JSONDecodeError:
        raise ValidationError('Arquivo JSON inválido')
    except UnicodeDecodeError:
        raise ValidationError('Encoding do arquivo JSON inválido')
    except Exception as e:
        logger.error(f"Erro na validação do JSON: {e}")
        raise ValidationError('Erro ao validar arquivo JSON')

def validate_cpf(cpf):
    """Valida formato e dígitos verificadores do CPF"""
    if not cpf:
        return False
    
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if len(set(cpf)) == 1:
        return False
    
    # Validação dos dígitos verificadores
    def calculate_digit(cpf_partial):
        sum_digits = 0
        for i, digit in enumerate(cpf_partial):
            sum_digits += int(digit) * (len(cpf_partial) + 1 - i)
        remainder = sum_digits % 11
        return 0 if remainder < 2 else 11 - remainder
    
    # Validar primeiro dígito
    if int(cpf[9]) != calculate_digit(cpf[:9]):
        return False
    
    # Validar segundo dígito
    if int(cpf[10]) != calculate_digit(cpf[:10]):
        return False
    
    return True

def sanitize_text(text):
    """Sanitiza texto removendo caracteres potencialmente perigosos"""
    if not text:
        return text
    
    # Remove caracteres HTML/JS perigosos
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript:', 'eval(', 'function(']
    
    sanitized = str(text)
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()

def validate_user_input(text, max_length=200):
    """Valida entrada do usuário"""
    if not text:
        return True
    
    # Verificar tamanho
    if len(text) > max_length:
        raise ValidationError(f'Texto muito longo. Máximo: {max_length} caracteres')
    
    # Verificar caracteres perigosos
    dangerous_patterns = ['<script', 'javascript:', 'eval(', 'function(', 'setTimeout(', 'setInterval(']
    
    text_lower = text.lower()
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            raise ValidationError('Conteúdo potencialmente malicioso')
    
    return True
