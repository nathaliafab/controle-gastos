from django.db import models
import uuid
import os


def _remover_arquivo_seguro(arquivo_path):
    """Remove arquivo se existir, ignora erros silenciosamente"""
    try:
        if arquivo_path and os.path.isfile(arquivo_path):
            os.remove(arquivo_path)
    except (OSError, IOError):
        # Ignorar erros de remoção (arquivo pode já ter sido removido, etc.)
        pass


class ProcessamentoExtrato(models.Model):
    """Model para processamento de extratos bancários"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_usuario = models.CharField(max_length=200, verbose_name="Nome", blank=True, null=True)
    cpf_usuario = models.CharField(max_length=11, verbose_name="CPF", blank=True, null=True)
    
    # Bancos selecionados
    usar_c6 = models.BooleanField(default=False, verbose_name="C6 Bank")
    usar_bradesco = models.BooleanField(default=False, verbose_name="Bradesco")
    usar_bb = models.BooleanField(default=False, verbose_name="Banco do Brasil")
    usar_bb_cartao = models.BooleanField(default=False, verbose_name="BB Cartão")
    usar_itau = models.BooleanField(default=False, verbose_name="Itaú")
    
    # Arquivos de extrato (um arquivo por banco simples - apenas C6 e Bradesco)
    arquivo_c6 = models.FileField(upload_to='extratos/', blank=True, null=True)
    arquivo_bradesco = models.FileField(upload_to='extratos/', blank=True, null=True)
    
    # Arquivo de configuração personalizado (opcional)
    arquivo_config = models.FileField(
        upload_to='configs/', 
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
    arquivo_resultado = models.FileField(upload_to='resultados/', blank=True, null=True)
    
    # Dados dos gráficos Sankey em JSON
    sankey_data = models.TextField(blank=True, null=True, verbose_name="Dados dos Gráficos Sankey")
    
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
    arquivo = models.FileField(upload_to='extratos/')
    ordem = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['banco', 'ordem']
        verbose_name = "Arquivo de Extrato"
        verbose_name_plural = "Arquivos de Extratos"
    
    def __str__(self):
        """Representação string do modelo"""
        return f"{self.get_banco_display()} - {self.arquivo.name}"
