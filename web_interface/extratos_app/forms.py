from django import forms
import json
import bleach
import os
from .models import ProcessamentoExtrato
from .utils.validators import validate_cpf, validate_json_content, sanitize_filename
import logging

logger = logging.getLogger(__name__)

# Constantes para atributos de formulário
FORM_CONTROL_CLASS = 'form-control'
FORM_CHECK_CLASS = 'form-check-input'
DECIMAL_ATTRS = {
    'class': FORM_CONTROL_CLASS,
    'step': '0.01',
    'min': '0',
    'placeholder': '0.00'
}
CSV_FILE_ATTRS = {
    'class': FORM_CONTROL_CLASS,
    'accept': '.csv'
}

# Constantes para validação de arquivos
VALID_FILE_EXTENSIONS = {
    'c6': ['.csv'],
    'bradesco': ['.csv'],
    'bb': ['.csv'],
    'bb_cartao': ['.pdf'],
    'itau': ['.xls', '.xlsx']
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB em bytes

# Atributos específicos para cada tipo de arquivo
C6_FILE_ATTRS = {
    'class': FORM_CONTROL_CLASS,
    'accept': '.csv'
}

BRADESCO_FILE_ATTRS = {
    'class': FORM_CONTROL_CLASS,
    'accept': '.csv'
}


class ProcessamentoExtratoForm(forms.ModelForm):
    """Formulário para processamento de extratos bancários"""
    
    # Campos de arquivo com configurações específicas
    arquivo_c6 = forms.FileField(required=False, widget=forms.FileInput(attrs=C6_FILE_ATTRS))
    arquivo_bradesco = forms.FileField(required=False, widget=forms.FileInput(attrs=BRADESCO_FILE_ATTRS))
    arquivo_config = forms.FileField(required=False, widget=forms.FileInput(attrs={
        'class': FORM_CONTROL_CLASS,
        'accept': '.json'
    }))
    
    # Campos de saldo inicial com configurações padronizadas
    saldo_inicial_c6 = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs=DECIMAL_ATTRS))
    saldo_inicial_bradesco = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs=DECIMAL_ATTRS))
    saldo_inicial_bb = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs=DECIMAL_ATTRS))
    saldo_inicial_itau = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs=DECIMAL_ATTRS))
    
    class Meta:
        model = ProcessamentoExtrato
        fields = [
            'nome_usuario',
            'usar_c6', 'usar_bradesco', 'usar_bb', 'usar_bb_cartao', 'usar_itau',
            'arquivo_c6', 'arquivo_bradesco', 'arquivo_config',
            'saldo_inicial_c6', 'saldo_inicial_bradesco', 'saldo_inicial_bb', 'saldo_inicial_itau'
        ]
        widgets = {
            'nome_usuario': forms.TextInput(attrs={
                'class': FORM_CONTROL_CLASS,
                'placeholder': 'Digite seu primeiro nome',
                'maxlength': '50'
            }),
            'usar_c6': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bradesco': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bb': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bb_cartao': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_itau': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Adicionar campo CPF dinamicamente para evitar problemas com a propriedade
        self.fields['cpf_usuario'] = forms.CharField(
            max_length=11,
            required=False,
            widget=forms.TextInput(attrs={
                'class': FORM_CONTROL_CLASS,
                'placeholder': 'Digite apenas números (ex: 12345678901)',
                'maxlength': '11',
                'pattern': '[0-9]{11}'
            }),
            label='CPF'
        )

    def clean_nome_usuario(self):
        """Validar e limpar nome do usuário"""
        nome = self.cleaned_data.get('nome_usuario')
        if nome:
            # Sanitizar nome usando bleach
            nome = bleach.clean(nome, tags=[], strip=True)
            # Limitar tamanho
            if len(nome) > 50:
                raise forms.ValidationError('Nome muito longo (máximo 50 caracteres).')
            # Verificar se contém apenas caracteres válidos
            if not nome.replace(' ', '').replace('-', '').replace("'", '').isalpha():
                raise forms.ValidationError('Nome contém caracteres inválidos.')
        return nome

    def clean_cpf_usuario(self):
        """Validar CPF"""
        cpf = self.cleaned_data.get('cpf_usuario')
        if cpf:
            # Remove qualquer caractere que não seja dígito
            cpf = ''.join(filter(str.isdigit, cpf))
            
            # Validar CPF usando o validador
            if not validate_cpf(cpf):
                raise forms.ValidationError('CPF inválido.')
        return cpf

    def clean_arquivo_config(self):
        """Validar arquivo de configuração"""
        config_file = self.cleaned_data.get('arquivo_config')
        if config_file:
            # Validar conteúdo JSON
            validate_json_content(config_file)
            
            # Validar estrutura específica do arquivo
            self._validar_config_arquivo(config_file)
        
        return config_file

    def _validar_config_arquivo(self, config_file):
        """Validar arquivo de configuração JSON"""
        try:
            config_file.seek(0)
            config_content = config_file.read().decode('utf-8')
            config_data = json.loads(config_content)
            
            # Validar estrutura básica do JSON
            required_sections = ['usuario', 'arquivos']
            missing_sections = [section for section in required_sections if section not in config_data]
            
            if missing_sections:
                raise forms.ValidationError(
                    f'Arquivo de configuração inválido. Seções obrigatórias ausentes: {", ".join(missing_sections)}'
                )
            
            # Validar dados do usuário
            usuario = config_data.get('usuario', {})
            if not isinstance(usuario, dict):
                raise forms.ValidationError('Seção "usuario" deve ser um objeto.')
            
            if 'nome' not in usuario or 'cpf' not in usuario:
                raise forms.ValidationError(
                    'Arquivo de configuração deve conter "nome" e "cpf" na seção "usuario".'
                )
            
            # Validar CPF do arquivo
            cpf_arquivo = usuario.get('cpf', '')
            if not validate_cpf(cpf_arquivo):
                raise forms.ValidationError('CPF no arquivo de configuração é inválido.')
            
            # Validar nome do arquivo
            nome_arquivo = usuario.get('nome', '')
            if not nome_arquivo or len(nome_arquivo) > 50:
                raise forms.ValidationError('Nome no arquivo de configuração é inválido.')
            
            # Validar se há pelo menos um banco configurado
            arquivos = config_data.get('arquivos', {})
            if not isinstance(arquivos, dict):
                raise forms.ValidationError('Seção "arquivos" deve ser um objeto.')
            
            bancos_validos = ['c6_bank', 'bradesco', 'bb', 'bb_cartao', 'itau']
            bancos_configurados = [banco for banco in bancos_validos if banco in arquivos]
            
            if not bancos_configurados:
                raise forms.ValidationError(
                    'Arquivo de configuração deve ter pelo menos um banco configurado na seção "arquivos".'
                )
            
            # Resetar o ponteiro do arquivo
            config_file.seek(0)
            
        except json.JSONDecodeError:
            raise forms.ValidationError('Arquivo de configuração não é um JSON válido.')
        except UnicodeDecodeError:
            raise forms.ValidationError('Encoding do arquivo de configuração inválido.')
        except Exception as e:
            logger.error(f"Erro na validação do arquivo de configuração: {e}")
            raise forms.ValidationError('Erro ao processar arquivo de configuração.')

    def _validar_bancos_selecionados(self, cleaned_data):
        """Validar bancos selecionados e seus arquivos"""
        # Se há arquivo de configuração, não validar seleção manual
        if cleaned_data.get('arquivo_config'):
            return
            
        # Verificar se pelo menos um banco foi selecionado
        bancos_selecionados = any([
            cleaned_data.get('usar_c6'),
            cleaned_data.get('usar_bradesco'),
            cleaned_data.get('usar_bb'),
            cleaned_data.get('usar_bb_cartao'),
            cleaned_data.get('usar_itau')
        ])
        
        if not bancos_selecionados:
            raise forms.ValidationError('Selecione pelo menos um banco.')
        
        # Validar arquivos únicos e saldos
        self._validar_banco_unico('c6', cleaned_data)
        self._validar_banco_unico('bradesco', cleaned_data)
        
        # Definir saldos padrão para bancos de múltiplos arquivos
        self._definir_saldo_padrao('bb', cleaned_data)
        self._definir_saldo_padrao('itau', cleaned_data)

    def _validar_banco_unico(self, banco, cleaned_data):
        """Validar banco que aceita apenas um arquivo"""
        if cleaned_data.get(f'usar_{banco}'):
            arquivo = cleaned_data.get(f'arquivo_{banco}')
            if not arquivo:
                self.add_error(f'arquivo_{banco}', f'Arquivo obrigatório quando {banco.title()} está selecionado.')
            
            # Definir saldo padrão se não fornecido
            saldo_key = f'saldo_inicial_{banco}'
            if cleaned_data.get(saldo_key) in [None, '']:
                cleaned_data[saldo_key] = 0

    def _definir_saldo_padrao(self, banco, cleaned_data):
        """Definir saldo padrão para bancos de múltiplos arquivos"""
        if cleaned_data.get(f'usar_{banco}'):
            saldo_key = f'saldo_inicial_{banco}'
            if cleaned_data.get(saldo_key) in [None, '']:
                cleaned_data[saldo_key] = 0

    def clean(self):
        """Validação principal do formulário"""
        cleaned_data = super().clean()
        
        # Se arquivo de configuração foi fornecido, processar e definir bancos automaticamente
        if cleaned_data.get('arquivo_config'):
            self._processar_arquivo_config(cleaned_data)
            return cleaned_data
        
        # Validações padrão se não há arquivo de configuração
        if not cleaned_data.get('nome_usuario'):
            self.add_error('nome_usuario', 'Nome é obrigatório quando não há arquivo de configuração.')
        
        if not cleaned_data.get('cpf_usuario'):
            self.add_error('cpf_usuario', 'CPF é obrigatório quando não há arquivo de configuração.')
        
        # Validar bancos selecionados
        self._validar_bancos_selecionados(cleaned_data)
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sobrescrever save para definir informações de auditoria"""
        instance = super().save(commit=False)
        
        # Definir informações de auditoria se request estiver disponível
        if self.request:
            instance.ip_address = self._get_client_ip(self.request)
            instance.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        
        # Definir CPF usando a propriedade (que criptografa automaticamente)
        cpf = self.cleaned_data.get('cpf_usuario')
        if cpf:
            instance.cpf_usuario = cpf
        
        if commit:
            instance.save()
        
        return instance
    
    def _get_client_ip(self, request):
        """Obter IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _processar_arquivo_config(self, cleaned_data):
        """Processar arquivo de configuração JSON e definir bancos automaticamente"""
        try:
            config_file = cleaned_data.get('arquivo_config')
            if not config_file:
                return
                
            # Ler e processar o arquivo JSON
            config_file.seek(0)
            config_content = config_file.read().decode('utf-8')
            config_data = json.loads(config_content)
            
            # Mapear bancos do JSON para campos do formulário
            banco_mapping = {
                'c6_bank': 'usar_c6',
                'bradesco': 'usar_bradesco', 
                'bb': 'usar_bb',
                'bb_cartao': 'usar_bb_cartao',
                'itau': 'usar_itau'
            }
            
            # Obter lista de bancos configurados no JSON
            arquivos = config_data.get('arquivos', {})
            bancos_configurados = []
            
            for banco_json, campo_form in banco_mapping.items():
                if banco_json in arquivos:
                    cleaned_data[campo_form] = True
                    bancos_configurados.append(banco_json)
            
            # Definir dados do usuário a partir do JSON
            usuario = config_data.get('usuario', {})
            if usuario.get('nome') and not cleaned_data.get('nome_usuario'):
                cleaned_data['nome_usuario'] = usuario['nome']
            if usuario.get('cpf') and not cleaned_data.get('cpf_usuario'):
                cleaned_data['cpf_usuario'] = usuario['cpf']
            
            # Definir saldos iniciais a partir do JSON
            saldos = config_data.get('saldos_iniciais', {})
            saldo_mapping = {
                'c6_bank': 'saldo_inicial_c6',
                'bradesco': 'saldo_inicial_bradesco',
                'bb': 'saldo_inicial_bb', 
                'itau': 'saldo_inicial_itau'
            }
            
            for banco_json, campo_saldo in saldo_mapping.items():
                if banco_json in saldos:
                    cleaned_data[campo_saldo] = saldos[banco_json]
            
            # Resetar o ponteiro do arquivo
            config_file.seek(0)
            
            logger.info(f"Configuração JSON processada com sucesso. Bancos configurados: {bancos_configurados}")
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo de configuração: {e}")
            raise forms.ValidationError('Erro ao processar arquivo de configuração JSON.')

    def clean_arquivo_c6(self):
        """Validar arquivo do C6 Bank"""
        arquivo = self.cleaned_data.get('arquivo_c6')
        if arquivo:
            # Validar extensão do arquivo
            ext = os.path.splitext(arquivo.name)[1].lower()
            if ext not in VALID_FILE_EXTENSIONS['c6']:
                raise forms.ValidationError(f'Arquivo inválido para o C6 Bank. Formatos aceitos: {", ".join(VALID_FILE_EXTENSIONS["c6"])}')
            
            # Validar tamanho do arquivo
            if arquivo.size > MAX_FILE_SIZE:
                raise forms.ValidationError('Tamanho do arquivo excede o limite de 10MB.')
        
        return arquivo

    def clean_arquivo_bradesco(self):
        """Validar arquivo do Bradesco"""
        arquivo = self.cleaned_data.get('arquivo_bradesco')
        if arquivo:
            # Validar extensão do arquivo
            ext = os.path.splitext(arquivo.name)[1].lower()
            if ext not in VALID_FILE_EXTENSIONS['bradesco']:
                raise forms.ValidationError(f'Arquivo inválido para o Bradesco. Formatos aceitos: {", ".join(VALID_FILE_EXTENSIONS["bradesco"])}')
            
            # Validar tamanho do arquivo
            if arquivo.size > MAX_FILE_SIZE:
                raise forms.ValidationError('Tamanho do arquivo excede o limite de 10MB.')
        
        return arquivo

    def _validar_arquivo_extension_e_tamanho(self, arquivo, banco_key, nome_banco):
        """Validar extensão e tamanho do arquivo para um banco específico"""
        if not arquivo:
            return
            
        # Validar extensão
        ext = os.path.splitext(arquivo.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS[banco_key]:
            raise forms.ValidationError(
                f'Arquivo inválido para o {nome_banco}. Formatos aceitos: {", ".join(VALID_FILE_EXTENSIONS[banco_key])}'
            )
        
        # Validar tamanho
        if arquivo.size > MAX_FILE_SIZE:
            raise forms.ValidationError(f'Tamanho do arquivo excede o limite de 10MB ({nome_banco}).')
    
    def _validar_multiplos_arquivos_por_banco(self, request, banco_key, nome_banco):
        """Validar múltiplos arquivos para um banco específico"""
        erros = []
        
        # Coletar arquivos para este banco
        arquivos = []
        for key in request.FILES.keys():
            if key.startswith(f'arquivos_{banco_key}_'):
                arquivos.append(request.FILES[key])
        
        # Validar cada arquivo
        for arquivo in arquivos:
            try:
                self._validar_arquivo_extension_e_tamanho(arquivo, banco_key, nome_banco)
            except forms.ValidationError as e:
                erros.append(str(e))
        
        return erros
