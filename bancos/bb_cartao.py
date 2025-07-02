"""
Processador de fatura do cartão de crédito do Banco do Brasil (PDF).
"""

import pandas as pd
import pdfplumber
import re
import warnings
import logging
from pathlib import Path
from datetime import datetime
from utils import criar_dataframe_padronizado


def processar(config: dict) -> pd.DataFrame:
    print("📊 Processando fatura do cartão BB...")
    
    try:
        pdf_path = config['arquivos']['bb_cartao']
        
        if not Path(pdf_path).exists():
            print(f"   ⚠️  Arquivo {pdf_path} não encontrado")
            return pd.DataFrame()
        
        senha_pdf = config['usuario']['cpf'][:5]
        
        warnings.filterwarnings("ignore")
        logging.getLogger("pdfplumber").setLevel(logging.ERROR)
        logging.getLogger("pdfminer").setLevel(logging.ERROR)
        
        transacoes = []
        nome_cartao = None
        ano_fatura = str(datetime.now().year)
        
        try:
            with pdfplumber.open(pdf_path, password=senha_pdf) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text += page_text + "\n"
                
                nome_cartao = _extrair_nome_cartao(all_text)
                
                ano_fatura = _extrair_ano_fatura(all_text)
                
                transacoes = _extrair_transacoes(all_text, ano_fatura)
                
        except Exception as e_senha:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    all_text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            all_text += page_text + "\n"
                    
                    nome_cartao = _extrair_nome_cartao(all_text)
                    
                    ano_fatura = _extrair_ano_fatura(all_text)
                    
                    # Extrair transações
                    transacoes = _extrair_transacoes(all_text, ano_fatura)
                    
            except Exception as e_sem_senha:
                raise Exception(f"Não foi possível abrir o PDF nem com senha nem sem senha: {e_sem_senha}")
        
        if not transacoes:
            print("   ⚠️  Nenhuma transação encontrada no PDF")
            return pd.DataFrame()
        
        # Criar DataFrame padronizado
        data_dict = {
            'Data': [t['Data'] for t in transacoes],
            'Data_Contabil': [t['Data'] for t in transacoes],
            'Banco': 'Banco do Brasil',
            'Agencia_Conta': nome_cartao or 'BB Cartão de Crédito',
            'Tipo_Transacao': [t['Tipo'] for t in transacoes],
            'Descricao': [t['Descricao'] for t in transacoes],
            'Valor': [-t['Valor'] for t in transacoes],
            'Valor_Entrada': [abs(t['Valor']) if t['Valor'] < 0 else 0 for t in transacoes],
            'Valor_Saida': [t['Valor'] if t['Valor'] > 0 else 0 for t in transacoes]
        }
        
        resultado = criar_dataframe_padronizado(data_dict)
        resultado['Categoria_Auto'] = 'Cartão Crédito'
        
        print(f"   ✅ {len(resultado)} transações processadas")
        return resultado
        
    except Exception as e:
        print(f"   ❌ Erro ao processar PDF: {e}")
        import traceback
        print(f"   📝 Detalhes do erro: {traceback.format_exc()}")
        return pd.DataFrame()


def _extrair_nome_cartao(text: str) -> str:
    match = re.search(r'(OUROCARD.*?Final\s*\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    match = re.search(r'Final\s*(\d{4})', text, re.IGNORECASE)
    if match:
        return f"BB Cartão Final {match.group(1)}"
    
    return "BB Cartão de Crédito"


def _extrair_ano_fatura(text: str) -> str:
    match = re.search(r'\d{2}/\d{2}/(20\d{2})', text)
    if match:
        return match.group(1)
    
    match = re.search(r'\b(20\d{2})\b', text)
    if match:
        return match.group(1)
    
    return str(datetime.now().year)


def _extrair_transacoes(text: str, ano_fatura: str) -> list:
    transacoes = []
    lines = text.split('\n')
    
    inicio_lancamentos = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if 'Data' in line and 'Descrição' in line and 'Valor' in line:
            inicio_lancamentos = True
            continue
        
        if not inicio_lancamentos:
            continue
        
        if any(palavra in line for palavra in ['Subtotal', 'Total da Fatura', 'Página', 'Fale conosco']):
            break
        
        if not re.search(r'\d{2}/\d{2}', line):
            continue
        
        match = re.search(r'(\d{2}/\d{2})\s+(.+?)\s+(BR|[A-Z]{2})\s+R\$\s*([-]?\d+[.,]\d{2})', line)
        if match:
            dia_mes = match.group(1)
            descricao = match.group(2).strip()
            pais = match.group(3)
            valor_str = match.group(4)
            
            valor = float(valor_str.replace('.', '').replace(',', '.'))
            if valor_str.startswith('-'):
                valor = -abs(valor)
            
            try:
                data_completa = pd.to_datetime(f"{dia_mes}/{ano_fatura}", dayfirst=True)
            except:
                continue
            
            tipo = "Pagamento/Crédito" if valor < 0 else "Compra"
            
            transacao = {
                'Data': data_completa,
                'Tipo': tipo,
                'Descricao': f"{descricao} ({pais})",
                'Valor': valor
            }
            
            transacoes.append(transacao)
    
    return transacoes
