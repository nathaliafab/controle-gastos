from django.db import models
import uuid
import os
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

# Importações condicionais para evitar erros de importação
try:
    from .utils.encryption import encryption
except ImportError:
    encryption = None

try:
    from .utils.validators import validate_file_type, validate_cpf, sanitize_filename
except ImportError:
    def validate_file_type(file):
        pass
    def validate_cpf(cpf):
        return True
    def sanitize_filename(filename):
        return filename or 'unnamed_file'


def _remover_arquivo_seguro(arquivo_path):
    """Remove arquivo se existir, ignora erros silenciosamente"""
    try:
        if arquivo_path and os.path.isfile(arquivo_path):
            os.remove(arquivo_path)
    except (OSError, IOError):
        # Ignorar erros de remoção (arquivo pode já ter sido removido, etc.)
        pass


def upload_to_secure_path(instance, filename):
    """Gera caminho seguro para upload de arquivos"""
    safe_filename = sanitize_filename(filename)
    return f'extratos/{instance.id}/{safe_filename}'


def upload_config_secure_path(instance, filename):
    """Gera caminho seguro para upload de configs"""
    safe_filename = sanitize_filename(filename)
    return f'configs/{instance.id}/{safe_filename}'


def upload_result_secure_path(instance, filename):
    """Gera caminho seguro para upload de resultados"""
    safe_filename = sanitize_filename(filename)
    return f'resultados/{instance.id}/{safe_filename}'


class ProcessamentoExtrato(models.Model):
    """Model para processamento de extratos bancários"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_usuario = models.CharField(max_length=200, verbose_name="Nome", blank=True, null=True)
    
    # CPF - mantém campo original para compatibilidade, mas adiciona criptografia
    cpf_usuario = models.CharField(max_length=11, verbose_name="CPF", blank=True, null=True)
    cpf_usuario_encrypted = models.TextField(verbose_name="CPF Criptografado", blank=True, null=True)
    cpf_hash = models.CharField(max_length=32, verbose_name="Hash CPF", blank=True, null=True, db_index=True)
    
    # Bancos selecionados
    usar_c6 = models.BooleanField(default=False, verbose_name="C6 Bank")
    usar_bradesco = models.BooleanField(default=False, verbose_name="Bradesco")
    usar_bb = models.BooleanField(default=False, verbose_name="Banco do Brasil")
    usar_bb_cartao = models.BooleanField(default=False, verbose_name="BB Cartão")
    usar_itau = models.BooleanField(default=False, verbose_name="Itaú")
    
    # Arquivos de extrato
    arquivo_c6 = models.FileField(upload_to=upload_to_secure_path, blank=True, null=True)
    arquivo_bradesco = models.FileField(upload_to=upload_to_secure_path, blank=True, null=True)
    
    # Arquivo de configuração personalizado (opcional)
    arquivo_config = models.FileField(
        upload_to=upload_config_secure_path, 
        blank=True, 
        null=True, 
        verbose_name="Arquivo de Configuração (opcional)"
    )
    
    # Saldos iniciais
    saldo_inicial_c6 = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Saldo inicial C6"
    )
    saldo_inicial_bradesco = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Saldo inicial Bradesco"
    )
    saldo_inicial_bb = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Saldo inicial BB"
    )
    saldo_inicial_itau = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Saldo inicial Itaú"
    )
    
    # Controle
    data_criacao = models.DateTimeField(auto_now_add=True)
    processado = models.BooleanField(default=False)
    arquivo_resultado = models.FileField(upload_to=upload_result_secure_path, blank=True, null=True)
    
    # Dados dos gráficos Sankey em JSON
    sankey_data = models.TextField(blank=True, null=True, verbose_name="Dados dos Gráficos Sankey")
    
    # Controle de acesso
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    def get_cpf_display(self):
        """Retorna CPF mascarado para exibição"""
        cpf = self.cpf_usuario
        if cpf and len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf
    
    def encrypt_cpf(self):
        """Criptografa o CPF se disponível"""
        if self.cpf_usuario and encryption:
            try:
                self.cpf_usuario_encrypted = encryption.encrypt(self.cpf_usuario)
                self.cpf_hash = encryption.hash_cpf(self.cpf_usuario)
            except Exception as e:
                logger.error(f"Erro ao criptografar CPF: {e}")
    
    def clean(self):
        """Validação do modelo"""
        super().clean()
        
        # Validar nome
        if self.nome_usuario:
            # Remover caracteres perigosos
            import re
            self.nome_usuario = re.sub(r'[<>"\']', '', self.nome_usuario.strip())
        
        # Validar CPF
        if self.cpf_usuario:
            if not validate_cpf(self.cpf_usuario):
                raise ValidationError("CPF inválido")
        
        # Validar se pelo menos um banco está selecionado (apenas quando não há arquivo de configuração)
        if not self.arquivo_config and not any([self.usar_c6, self.usar_bradesco, self.usar_bb, self.usar_bb_cartao, self.usar_itau]):
            raise ValidationError("Pelo menos um banco deve ser selecionado")
    
    def save(self, *args, **kwargs):
        """Sobrescrever save para validações adicionais"""
        # Criptografar CPF antes de salvar
        if self.cpf_usuario and not self.cpf_usuario_encrypted:
            self.encrypt_cpf()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Sobrescrever delete para remover arquivos do sistema de arquivos"""
        # Remover arquivo de resultado
        if self.arquivo_resultado:
            _remover_arquivo_seguro(self.arquivo_resultado.path)
        
        # Remover arquivos de extratos principais
        _remover_arquivo_seguro(self.arquivo_c6.path if self.arquivo_c6 else None)
        _remover_arquivo_seguro(self.arquivo_bradesco.path if self.arquivo_bradesco else None)
        _remover_arquivo_seguro(self.arquivo_config.path if self.arquivo_config else None)
        
        # Remover arquivos múltiplos
        for arquivo in self.arquivos.all():
            if arquivo.arquivo:
                _remover_arquivo_seguro(arquivo.arquivo.path)
        
        super().delete(*args, **kwargs)
    
    def __str__(self):
        """Representação string do modelo"""
        nome = self.nome_usuario or "Usuário"
        data = self.data_criacao.strftime('%d/%m/%Y %H:%M')
        return f"{nome} - {data}"
    
    class Meta:
        verbose_name = "Processamento de Extrato"
        verbose_name_plural = "Processamentos de Extratos"
        ordering = ['-data_criacao']


class ArquivoExtrato(models.Model):
    """Modelo para múltiplos arquivos - apenas para BB, BB Cartão e Itaú"""
    
    BANCO_CHOICES = [
        ('bb', 'Banco do Brasil'),
        ('bb_cartao', 'BB Cartão'),
        ('itau', 'Itaú'),
    ]
    
    processamento = models.ForeignKey(
        ProcessamentoExtrato, 
        on_delete=models.CASCADE, 
        related_name='arquivos'
    )
    banco = models.CharField(max_length=20, choices=BANCO_CHOICES)
    arquivo = models.FileField(upload_to=upload_to_secure_path)
    ordem = models.PositiveIntegerField(default=1)
    
    def clean(self):
        """Validação do modelo"""
        super().clean()
        
        # Validar banco
        if self.banco not in [choice[0] for choice in self.BANCO_CHOICES]:
            raise ValidationError("Banco inválido")
    
    class Meta:
        ordering = ['banco', 'ordem']
        verbose_name = "Arquivo de Extrato"
        verbose_name_plural = "Arquivos de Extratos"
    
    def __str__(self):
        """Representação string do modelo"""
        return f"{self.get_banco_display()} - {self.arquivo.name}"
