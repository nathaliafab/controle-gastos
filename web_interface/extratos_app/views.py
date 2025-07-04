import os
import sys
import json
import shutil
import tempfile
import traceback
import importlib.util
from pathlib import Path

import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.core.files.base import ContentFile
from django.http import JsonResponse

from .models import ProcessamentoExtrato, ArquivoExtrato
from .forms import ProcessamentoExtratoForm

# Constantes
EXCEL_PREVIEW_ROWS = 100
TRANSFERENCIAS_WINDOW_DAYS = 3
TOLERANCIA_VALOR = 0.01

# Import das funções do processador original
core_dir = Path(__file__).parent.parent.parent / "core"
analise_dir = Path(__file__).parent.parent.parent / "analise"
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(analise_dir))

try:
    from processador import processar_extratos
    from graficos_sankey import analisar_gastos_sankey_proventos_detalhados
except ImportError:
    spec = importlib.util.spec_from_file_location("processador", core_dir / "processador.py")
    processador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(processador)
    processar_extratos = processador.processar_extratos
    
    # Importar Sankey
    spec_sankey = importlib.util.spec_from_file_location("graficos_sankey", analise_dir / "graficos_sankey.py")
    graficos_sankey = importlib.util.module_from_spec(spec_sankey)
    spec_sankey.loader.exec_module(graficos_sankey)
    analisar_gastos_sankey_proventos_detalhados = graficos_sankey.analisar_gastos_sankey_proventos_detalhados


def _log_error(error_msg, exception=None):
    """Helper para log de erros"""
    if exception:
        traceback.print_exc()
    print(f"ERRO: {error_msg}")


def _extract_body_content(html_content):
    """Extrai o conteúdo do body de um HTML"""
    import re
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
    return body_match.group(1) if body_match else None


def _get_config_base_dir(config_file_path):
    """Determina o diretório base para arquivos de configuração"""
    base_dir = Path(config_file_path).parent.parent.parent
    
    # Verificar se estamos no diretório correto (deve ter o arquivo config.json na raiz)
    if not (base_dir / "config.json").exists():
        # Se não encontrou, tentar o diretório pai do web_interface
        base_dir = Path(__file__).parent.parent.parent
    
    return base_dir


def _get_default_categories():
    """Retorna as categorias padrão para processamento"""
    return {
        "estornos": ["ESTORNO", "EST "],
        "investimentos": ["OUROCAP", "B3", "ATIVO", "ACOES", "FUNDO", "CDB", "LCI", "TESOURO", "APLICACAO", "RESGATE"],
        "rendimentos": ["CASHBACK", "REMUNERACAO", "RENDIMENTO", "JUROS", "DIVIDENDO", "JSCP", "SALARIO", "ORDEM BANC", "PROVENTO", "FOLHA"],
        "pix_transferencia": ["PIX", "TRANSFERENCIA", "TED", "DOC"],
        "cartao_credito": ["CARTAO CREDITO", "CREDITO CARTAO", "COMPRA CARTAO"],
        "cartao_debito": ["CARTAO DEBITO", "DEBITO CARTAO", "DEBITO DE CARTAO"],
        "debito_automatico": ["DEBITO AUTOMATICO"],
        "tarifas": ["TARIFA", "TAXA", "IOF", "ANUIDADE", "MANUTENCAO"],
        "saques": ["SAQUE", "RETIRADA"],
        "depositos": ["DEPOSITO", "CREDITO EM CONTA"]
    }


def _get_default_processing_config():
    """Retorna configurações padrão de processamento"""
    return {
        "skip_rows_c6": 8,
        "skip_rows_bradesco": 1,
        "skip_rows_bb": 0,
        "skip_rows_itau": 10,
        "janela_transferencias_dias": TRANSFERENCIAS_WINDOW_DAYS,
        "tolerancia_valor": TOLERANCIA_VALOR
    }


def index(request):
    """Página inicial com o formulário"""
    form = ProcessamentoExtratoForm()
    return render(request, 'extratos_app/index.html', {'form': form})


def processar_extratos_view(request):
    """Processar os extratos enviados"""
    if request.method != 'POST':
        return redirect('extratos:index')
    
    form = ProcessamentoExtratoForm(request.POST, request.FILES)
    
    if form.is_valid():
        # Validar múltiplos arquivos para bancos que suportam (apenas se não há config file)
        if not form.cleaned_data.get('arquivo_config'):
            erros_multiplos = validar_multiplos_arquivos(request, form.cleaned_data)
            
            if erros_multiplos:
                for erro in erros_multiplos:
                    messages.error(request, erro)
                return render(request, 'extratos_app/index.html', {'form': form})
        
        try:
            processamento = form.save()
            
            # Salvar múltiplos arquivos apenas se não há config file
            if not processamento.arquivo_config:
                salvar_multiplos_arquivos(request, processamento)
            
            # Processar os extratos
            sucesso = processar_extratos_web(processamento)
            
            if sucesso:
                processamento.processado = True
                processamento.save()
                return redirect('extratos:resultado', processamento_id=processamento.id)
            else:
                messages.error(request, 'Erro ao processar os extratos. Verifique os arquivos e tente novamente.')
                processamento.delete()
                
        except Exception as e:
            messages.error(request, f'Erro inesperado: {str(e)}')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(request, error)
                else:
                    field_obj = form.fields.get(field)
                    field_label = field_obj.label if field_obj and hasattr(field_obj, 'label') else field
                    messages.error(request, f'{field_label}: {error}')
    
    # Re-renderizar com erros
    return render(request, 'extratos_app/index.html', {'form': form})


def gerar_graficos_sankey(processamento, arquivo_excel, output_dir):
    """Gerar gráficos Sankey e retornar conteúdo HTML"""
    try:
        # Executar geração de gráficos Sankey
        analisar_gastos_sankey_proventos_detalhados(
            nome_arquivo_excel=str(arquivo_excel),
            output_dir=str(output_dir)
        )
        
        # Buscar arquivos HTML gerados
        html_files = list(output_dir.glob("*.html"))
        
        sankey_data = {
            'geral': None,
            'bancos': {}
        }
        
        for html_file in html_files:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extrair o conteúdo do body
                body_content = _extract_body_content(content)
                if body_content:
                    # Determinar tipo de arquivo
                    if 'geral' in html_file.name:
                        sankey_data['geral'] = body_content
                    else:
                        # Para gráficos de bancos específicos
                        banco_name = html_file.stem.replace('analise_gastos_sankey_', '').replace('_', ' ').title()
                        sankey_data['bancos'][banco_name] = body_content
        
        # Salvar dados Sankey no processamento para uso posterior
        processamento.sankey_data = json.dumps(sankey_data)
        processamento.save()
        
        return sankey_data
        
    except Exception as e:
        _log_error("Erro ao gerar gráficos Sankey", e)
        return {'geral': None, 'bancos': {}}


def validar_multiplos_arquivos(request, cleaned_data):
    """Validar se múltiplos arquivos foram enviados para bancos que precisam"""
    erros = []
    
    # Verificar BB
    if cleaned_data.get('usar_bb'):
        bb_files = [k for k in request.FILES.keys() if k.startswith('arquivos_bb_')]
        if not bb_files:
            erros.append("Banco do Brasil foi selecionado mas nenhum arquivo foi enviado.")
    
    # Verificar BB Cartão
    if cleaned_data.get('usar_bb_cartao'):
        bb_cartao_files = [k for k in request.FILES.keys() if k.startswith('arquivos_bb_cartao_')]
        if not bb_cartao_files:
            erros.append("BB Cartão foi selecionado mas nenhum arquivo foi enviado.")
    
    # Verificar Itaú
    if cleaned_data.get('usar_itau'):
        itau_files = [k for k in request.FILES.keys() if k.startswith('arquivos_itau_')]
        if not itau_files:
            erros.append("Itaú foi selecionado mas nenhum arquivo foi enviado.")
    
    return erros


def salvar_multiplos_arquivos(request, processamento):
    """Salvar múltiplos arquivos para bancos que suportam"""
    bancos_multiplos = {
        'bb': 'Banco do Brasil',
        'bb_cartao': 'BB Cartão',
        'itau': 'Itaú'
    }
    
    for banco_key, banco_nome in bancos_multiplos.items():
        arquivos = []
        
        # Coletar todos os arquivos deste banco com nova nomenclatura dinâmica
        for key in request.FILES.keys():
            if key.startswith(f'arquivos_{banco_key}_'):
                arquivos.append((key, request.FILES[key]))
        
        # Ordenar por índice
        arquivos.sort(key=lambda x: int(x[0].split('_')[-1]) if x[0].split('_')[-1].isdigit() else 0)
        
        # Salvar arquivos
        for ordem, (field_name, arquivo) in enumerate(arquivos, 1):
            ArquivoExtrato.objects.create(
                processamento=processamento,
                banco=banco_key,
                arquivo=arquivo,
                ordem=ordem
            )


def _criar_args_processamento(processamento, config):
    """Criar objeto args para o processador"""
    class Args:
        def __init__(self):
            # Determinar quais bancos usar com base na configuração
            if processamento.arquivo_config:
                # Se há arquivo config, usar todos os bancos que têm arquivos
                self.all = True
                self.c6 = 'c6_bank' in config.get("arquivos", {})
                self.bradesco = 'bradesco' in config.get("arquivos", {})
                self.bb = 'bb' in config.get("arquivos", {})
                self.bb_cartao = 'bb_cartao' in config.get("arquivos", {})
                self.itau = 'itau' in config.get("arquivos", {})
            else:
                # Se é configuração manual, usar bancos selecionados
                self.all = False
                self.c6 = processamento.usar_c6
                self.bradesco = processamento.usar_bradesco
                self.bb = processamento.usar_bb
                self.bb_cartao = processamento.usar_bb_cartao
                self.itau = processamento.usar_itau
            
            self.output = None  # Usar output do config.json
    
    return Args()


def processar_extratos_web(processamento):
    """Processar extratos usando o processador do core"""
    try:
        # Criar diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copiar arquivos para diretório temporário
            copiar_arquivos_para_temp(processamento, temp_path)
            
            # Preparar configuração
            config = preparar_configuracao(processamento, temp_path)
            
            if not config:
                return False
            
            # Criar objeto args para o processador
            args = _criar_args_processamento(processamento, config)
            
            # Executar processamento
            resultado = processar_extratos(args, config)
            
            # Buscar arquivo resultado
            output_dir = temp_path / "output"
            arquivos_resultado = list(output_dir.glob("*.xlsx"))
            
            if arquivos_resultado:
                arquivo_resultado = arquivos_resultado[0]
                
                # Gerar gráficos Sankey e obter dados
                sankey_data = gerar_graficos_sankey(processamento, arquivo_resultado, output_dir)
                
                # Salvar resultado
                with open(arquivo_resultado, 'rb') as f:
                    nome_usuario = processamento.nome_usuario or config.get('usuario', {}).get('nome', 'usuario')
                    nome_arquivo = f"controle_gastos_{nome_usuario}_{processamento.data_criacao.strftime('%Y%m%d_%H%M')}.xlsx"
                    processamento.arquivo_resultado.save(
                        nome_arquivo,
                        ContentFile(f.read())
                    )
                
                # Limpar arquivos de upload após processamento bem-sucedido
                limpar_arquivos_upload(processamento)
                
                return True
    
    except Exception as e:
        _log_error("Erro ao processar extratos", e)
        return False
    
    return False


def _processar_config_arquivo(processamento, temp_path):
    """Processar configuração a partir de arquivo JSON"""
    try:
        with open(processamento.arquivo_config.path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Criar diretórios de saída
        output_dir = temp_path / "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Atualizar apenas os caminhos dos arquivos para o diretório temporário
        arquivos_original = config.get("arquivos", {})
        arquivos_atualizados = {}
        
        for banco_key, arquivos_banco in arquivos_original.items():
            if banco_key == "output":
                # Atualizar caminho de saída - usar caminho absoluto
                arquivos_atualizados[banco_key] = str(output_dir / "controle_gastos.xlsx")
                continue
            
            if isinstance(arquivos_banco, str):
                # Arquivo único - converter para caminho no temp
                nome_arquivo = os.path.basename(arquivos_banco)
                arquivos_atualizados[banco_key] = str(temp_path / "extratos" / nome_arquivo)
            elif isinstance(arquivos_banco, list):
                # Lista de arquivos - converter cada um
                arquivos_temp = []
                for arquivo_path in arquivos_banco:
                    nome_arquivo = os.path.basename(arquivo_path)
                    arquivos_temp.append(str(temp_path / "extratos" / nome_arquivo))
                arquivos_atualizados[banco_key] = arquivos_temp
        
        # Atualizar configuração com novos caminhos
        config["arquivos"] = arquivos_atualizados
        
        return config
        
    except Exception as e:
        _log_error("Erro ao processar arquivo de configuração", e)
        return None


def _criar_config_manual(processamento, temp_path):
    """Criar configuração manual baseada nos campos do formulário"""
    config = {
        "usuario": {
            "nome": processamento.nome_usuario,
            "cpf": processamento.cpf_usuario
        },
        "arquivos": {
            "output": str(temp_path / "output" / "controle_gastos.xlsx")
        },
        "saldos_iniciais": {
            # Sempre incluir todos os bancos com valor 0 para evitar KeyError
            "c6_bank": 0,
            "bradesco": 0,
            "bb": 0,
            "itau": 0
        },
        "processamento": _get_default_processing_config(),
        "categorias": _get_default_categories()
    }
    
    # Criar diretórios
    os.makedirs(temp_path / "extratos", exist_ok=True)
    os.makedirs(temp_path / "output", exist_ok=True)
    
    # Configurar bancos selecionados
    _configurar_bancos_selecionados(processamento, config, temp_path)
    
    return config


def _configurar_bancos_selecionados(processamento, config, temp_path):
    """Configurar arquivos e saldos dos bancos selecionados"""
    if processamento.usar_c6:
        nome_arquivo = "c6_extrato.csv"
        config["arquivos"]["c6_bank"] = str(temp_path / "extratos" / nome_arquivo)
        config["saldos_iniciais"]["c6_bank"] = float(processamento.saldo_inicial_c6)
    
    if processamento.usar_bradesco:
        nome_arquivo = "bradesco_extrato.csv"
        config["arquivos"]["bradesco"] = str(temp_path / "extratos" / nome_arquivo)
        config["saldos_iniciais"]["bradesco"] = float(processamento.saldo_inicial_bradesco)
    
    if processamento.usar_bb:
        arquivos_bb = []
        for arquivo in processamento.arquivos.filter(banco='bb'):
            nome_arquivo = f"bb_extrato_{arquivo.ordem}.csv"
            arquivos_bb.append(str(temp_path / "extratos" / nome_arquivo))
        
        config["arquivos"]["bb"] = arquivos_bb
        config["saldos_iniciais"]["bb"] = float(processamento.saldo_inicial_bb)
    
    if processamento.usar_bb_cartao:
        arquivos_bb_cartao = []
        for arquivo in processamento.arquivos.filter(banco='bb_cartao'):
            nome_arquivo = f"bb_cartao_extrato_{arquivo.ordem}.pdf"
            caminho_completo = str(temp_path / "extratos" / nome_arquivo)
            arquivos_bb_cartao.append(caminho_completo)
        
        config["arquivos"]["bb_cartao"] = arquivos_bb_cartao
    
    if processamento.usar_itau:
        arquivos_itau = []
        for arquivo in processamento.arquivos.filter(banco='itau'):
            # Detectar extensão do arquivo original
            extensao_original = Path(arquivo.arquivo.name).suffix
            nome_arquivo = f"itau_extrato_{arquivo.ordem}{extensao_original}"
            arquivos_itau.append(str(temp_path / "extratos" / nome_arquivo))
        
        config["arquivos"]["itau"] = arquivos_itau
        config["saldos_iniciais"]["itau"] = float(processamento.saldo_inicial_itau)


def preparar_configuracao(processamento, temp_path):
    """Preparar configuração para processamento"""
    
    # Se há arquivo de configuração, usar ele
    if processamento.arquivo_config:
        return _processar_config_arquivo(processamento, temp_path)
    
    # Configuração manual baseada nos campos do formulário
    return _criar_config_manual(processamento, temp_path)


def _copiar_arquivos_config(processamento, extratos_dir):
    """Copiar arquivos baseado em configuração JSON"""
    try:
        with open(processamento.arquivo_config.path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        arquivos = config.get("arquivos", {})
        
        # O diretório base é determinado usando a função helper
        base_dir = _get_config_base_dir(processamento.arquivo_config.path)
        
        # Copiar arquivos baseado na configuração JSON
        for banco, arquivo_paths in arquivos.items():
            if banco == "output":  # Ignorar entrada de output
                continue
                
            if isinstance(arquivo_paths, str):
                arquivo_paths = [arquivo_paths]
            
            for arquivo_path in arquivo_paths:
                # Arquivo_path é relativo ao diretório raiz do projeto
                arquivo_completo = base_dir / arquivo_path
                nome_arquivo = os.path.basename(arquivo_path)
                
                if arquivo_completo.exists():
                    shutil.copy2(arquivo_completo, extratos_dir / nome_arquivo)
                # Se arquivo não encontrado, continuar silenciosamente
                        
    except Exception as e:
        _log_error("Erro ao copiar arquivos de configuração", e)


def _copiar_arquivos_manuais(processamento, extratos_dir):
    """Copiar arquivos da configuração manual"""
    # Copiar arquivos únicos
    if processamento.arquivo_c6:
        shutil.copy2(processamento.arquivo_c6.path, extratos_dir / "c6_extrato.csv")
    
    if processamento.arquivo_bradesco:
        shutil.copy2(processamento.arquivo_bradesco.path, extratos_dir / "bradesco_extrato.csv")
    
    # Copiar múltiplos arquivos
    for arquivo in processamento.arquivos.all():
        if arquivo.banco == 'bb':
            nome_destino = f"bb_extrato_{arquivo.ordem}.csv"
        elif arquivo.banco == 'bb_cartao':
            nome_destino = f"bb_cartao_extrato_{arquivo.ordem}.pdf"
        elif arquivo.banco == 'itau':
            # Usar a extensão original do arquivo (.xls para conta corrente, .xlsx para cartão)
            extensao_original = Path(arquivo.arquivo.name).suffix
            nome_destino = f"itau_extrato_{arquivo.ordem}{extensao_original}"
        
        shutil.copy2(arquivo.arquivo.path, extratos_dir / nome_destino)


def copiar_arquivos_para_temp(processamento, temp_path):
    """Copiar arquivos para diretório temporário"""
    extratos_dir = temp_path / "extratos"
    
    # Criar diretório de extratos se não existir
    os.makedirs(extratos_dir, exist_ok=True)
    
    # Se há arquivo de configuração, os arquivos estão especificados no JSON
    if processamento.arquivo_config:
        _copiar_arquivos_config(processamento, extratos_dir)
    else:
        _copiar_arquivos_manuais(processamento, extratos_dir)


def _carregar_dados_excel(arquivo_resultado):
    """Carregar dados do Excel para exibir na página"""
    try:
        df = pd.read_excel(arquivo_resultado.path)
        # Limitar a X linhas para não sobrecarregar a página
        return df.head(EXCEL_PREVIEW_ROWS).to_html(classes='table table-striped table-sm', escape=False)
    except Exception as e:
        _log_error("Erro ao carregar dados do Excel", e)
        return None


def _carregar_graficos_sankey(processamento):
    """Carregar gráficos Sankey dos dados salvos no processamento"""
    try:
        if hasattr(processamento, 'sankey_data') and processamento.sankey_data:
            sankey_data = json.loads(processamento.sankey_data)
            return sankey_data.get('geral'), sankey_data.get('bancos', {})
    except Exception as e:
        _log_error("Erro ao carregar gráficos Sankey", e)
    
    return None, {}


def resultado(request, processamento_id):
    """Exibir resultado do processamento"""
    processamento = get_object_or_404(ProcessamentoExtrato, id=processamento_id)
    
    # Carregar dados do Excel para exibir na página
    dados_excel = None
    if processamento.arquivo_resultado:
        dados_excel = _carregar_dados_excel(processamento.arquivo_resultado)
    
    # Carregar gráficos Sankey dos dados salvos no processamento
    sankey_geral, sankey_bancos = _carregar_graficos_sankey(processamento)
    
    return render(request, 'extratos_app/resultado.html', {
        'processamento': processamento,
        'dados_excel': dados_excel,
        'sankey_geral': sankey_geral,
        'sankey_bancos': sankey_bancos
    })


def download_resultado(request, processamento_id):
    """Download do arquivo resultado"""
    processamento = get_object_or_404(ProcessamentoExtrato, id=processamento_id)
    
    if not processamento.arquivo_resultado:
        raise Http404("Arquivo não encontrado")
    
    response = FileResponse(
        open(processamento.arquivo_resultado.path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(processamento.arquivo_resultado.name)
    )
    limpar_arquivo_resultado(processamento)
    return response


def _remover_arquivo_seguro(arquivo_path):
    """Remove arquivo se existir, ignora erros"""
    try:
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)
    except Exception:
        pass  # Ignorar erros de remoção individual


def limpar_arquivos_upload(processamento):
    """Remove os arquivos de upload após processamento bem-sucedido"""
    try:
        # Remover arquivo de configuração se existir
        if processamento.arquivo_config:
            _remover_arquivo_seguro(processamento.arquivo_config.path)
        
        # Remover arquivos únicos de bancos
        if processamento.arquivo_c6:
            _remover_arquivo_seguro(processamento.arquivo_c6.path)
        
        if processamento.arquivo_bradesco:
            _remover_arquivo_seguro(processamento.arquivo_bradesco.path)
        
        # Remover múltiplos arquivos
        for arquivo in processamento.arquivos.all():
            _remover_arquivo_seguro(arquivo.arquivo.path)
        
    except Exception as e:
        # Se houver erro na limpeza, apenas registrar mas não falhar o processamento
        _log_error("Erro ao limpar arquivos de upload", e)


def limpar_arquivo_resultado(processamento):
    """Remove o arquivo resultado após o usuário sair da página"""
    try:
        if processamento.arquivo_resultado:
            _remover_arquivo_seguro(processamento.arquivo_resultado.path)
            processamento.arquivo_resultado = None
            processamento.save()
    except Exception as e:
        _log_error("Erro ao limpar arquivo resultado", e)



