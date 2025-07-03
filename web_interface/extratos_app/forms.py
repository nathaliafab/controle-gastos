from django import forms
import json

from .models import ProcessamentoExtrato

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


class ProcessamentoExtratoForm(forms.ModelForm):
    """Formulário para processamento de extratos bancários"""
    
    # Campos de arquivo com configurações específicas
    arquivo_c6 = forms.FileField(required=False, widget=forms.FileInput(attrs=CSV_FILE_ATTRS))
    arquivo_bradesco = forms.FileField(required=False, widget=forms.FileInput(attrs=CSV_FILE_ATTRS))
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
            'nome_usuario', 'cpf_usuario',
            'usar_c6', 'usar_bradesco', 'usar_bb', 'usar_bb_cartao', 'usar_itau',
            'arquivo_c6', 'arquivo_bradesco', 'arquivo_config',
            'saldo_inicial_c6', 'saldo_inicial_bradesco', 'saldo_inicial_bb', 'saldo_inicial_itau'
        ]
        widgets = {
            'nome_usuario': forms.TextInput(attrs={
                'class': FORM_CONTROL_CLASS,
                'placeholder': 'Digite seu primeiro nome'
            }),
            'cpf_usuario': forms.TextInput(attrs={
                'class': FORM_CONTROL_CLASS,
                'placeholder': 'Digite apenas números (ex: 12345678901)',
                'maxlength': '11',
                'pattern': '[0-9]{11}'
            }),
            'usar_c6': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bradesco': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bb': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_bb_cartao': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
            'usar_itau': forms.CheckboxInput(attrs={'class': FORM_CHECK_CLASS}),
        }

    def clean_cpf_usuario(self):
        """Validar e limpar CPF"""
        cpf = self.cleaned_data.get('cpf_usuario')
        if cpf:
            # Remove qualquer caractere que não seja dígito
            cpf = ''.join(filter(str.isdigit, cpf))
            if len(cpf) != 11:
                raise forms.ValidationError('CPF deve ter exatamente 11 dígitos.')
        return cpf

    def _validar_config_arquivo(self, config_file):
        """Validar arquivo de configuração JSON"""
        try:
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
            if 'nome' not in config_data['usuario'] or 'cpf' not in config_data['usuario']:
                raise forms.ValidationError(
                    'Arquivo de configuração deve conter "nome" e "cpf" na seção "usuario".'
                )
            
            # Validar se há pelo menos um banco configurado
            bancos_validos = ['c6_bank', 'bradesco', 'bb', 'bb_cartao', 'itau']
            bancos_configurados = [banco for banco in bancos_validos if banco in config_data['arquivos']]
            
            if not bancos_configurados:
                raise forms.ValidationError(
                    'Arquivo de configuração deve ter pelo menos um banco configurado na seção "arquivos".'
                )
            
            # Resetar o ponteiro do arquivo
            config_file.seek(0)
            
        except json.JSONDecodeError:
            raise forms.ValidationError('Arquivo de configuração não é um JSON válido.')
        except Exception as e:
            raise forms.ValidationError(f'Erro ao processar arquivo de configuração: {str(e)}')

    def _validar_bancos_selecionados(self, cleaned_data):
        """Validar bancos selecionados e seus arquivos"""
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
        
        # Se arquivo de configuração foi fornecido, validá-lo e pular outras validações
        if cleaned_data.get('arquivo_config'):
            self._validar_config_arquivo(cleaned_data['arquivo_config'])
            return cleaned_data
        
        # Validações padrão se não há arquivo de configuração
        if not cleaned_data.get('nome_usuario'):
            self.add_error('nome_usuario', 'Nome é obrigatório quando não há arquivo de configuração.')
        
        if not cleaned_data.get('cpf_usuario'):
            self.add_error('cpf_usuario', 'CPF é obrigatório quando não há arquivo de configuração.')
        
        # Validar bancos selecionados
        self._validar_bancos_selecionados(cleaned_data)
        
        return cleaned_data

