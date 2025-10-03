#!/usr/bin/env python3
"""
Analisador de PDF de Prescrição Médica

Extrai nomes de medicamentos, quantidades e tokens de PDFs de prescrições médicas brasileiras.
Otimizado para prescrições com nomes de medicamentos em negrito e tokens de código QR.
"""

import re
import pdfplumber
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InfoMedicamento:
    """Container para informações extraídas de medicamentos."""
    nome: str
    quantidade: str
    quantidade_normalizada: int = 1


@dataclass
class DadosPrescricao:
    """Container para todos os dados extraídos da prescrição."""
    medicamentos: List[InfoMedicamento]
    token_qr: Optional[str] = None
    # Data da prescrição (apenas a data, sem hora), quando disponível
    data: Optional[str] = None


class AnalisadorPrescricaoMedica:
    """Analisador para PDFs de prescrições médicas brasileiras."""
    
    # Exclui termos comuns não-medicamentosos encontrados em prescrições
    EXCLUSOES_MEDICAMENTOS = {
        'nome', 'cpf', 'crm', 'data', 'hora', 'memed', 'ui', 'sp', 'mg', 'ml', 'un', 'und',
        'comprimido', 'cápsula', 'pomada', 'dermatológica', 'uso', 'contínuo', 'continuo',
        'embalagem', 'caixa', 'frasco', 'unidade', 'unidades', 'eurofarma', 'ems', 'medley',
        'abbott', 'novo', 'nordisk', 'roche', 'bayer', 'pfizer', 'novartis', 'sanofi',
        'ktsjte', 'ktsjte -', 'ktsjte-', 'comprimido orodispersível', 'suspensão injetável',
        'sulfato de gentamicina', 'orodispersível', 'injetável', 'suspensão'
    }
    
    # Padrões regex otimizados para prescrições médicas brasileiras
    PADROES_MEDICAMENTOS = [
        # Padrões específicos de medicamentos com dosagem (prioridade mais alta)
        r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç\s\-]{4,}(?:de\s+)?[a-záàâãéêíóôõúç\s]+\d+(?:\.\d+)?mg)',
        r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç\s\-]{4,}\s+\d+(?:\.\d+)?mg)',
        # Padrões conhecidos de compostos medicamentosos
        r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ](?:loridrato|icloridrato)\s+de\s+[a-záàâãéêíóôõúç\s]+)',
        r'(Mirtazapina(?:\s+\d+mg)?)',
        r'(Insulina\s+[a-záàâãéêíóôõúç\s]+)',
        r'(Trok-[A-Z])',
        # Padrão farmacêutico genérico (muito restritivo)
        r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç\s\-]{6,}(?=\s+(?:uso|comprimido|pomada|dermatológica)|$))',
    ]
    
    # Padrões de quantidade inline de alta prioridade (próximos aos nomes dos medicamentos)
    PADROES_QUANTIDADE_INLINE = [
        r'\((\d+)un\s+de\s+\d+g?\)',  # (1un de 30g)
        r'\((\d+)un\)',               # (1un)
        r'\((\d+)\s*unidade[s]?\)',   # (1 unidade)
        r'\((\d+)\s*embalagem\)',     # (1 embalagem)
        r'\((\d+)\s*frasco[s]?\)',    # (1 frasco)
        r'\((\d+)\s*caixa[s]?\)',     # (1 caixa)
    ]
    
    PADROES_QUANTIDADE = [
        r'(\d+)\s*(?:embalagem|caixa|frasco)',
        r'uso\s+cont[íi]nuo',
        r'(\d+)\s*(?:unidade|un|und)',
        r'(\d+)\s*(?:comprimido|comp|cp)',
    ]
    
    PADRAO_TOKEN = r'([A-Z0-9]{6,8})'  # Tokens como 'kTSJTC'
    
    def __init__(self, caminho_pdf: str):
        """Inicializa o analisador com o caminho do PDF."""
        self.caminho_pdf = Path(caminho_pdf)
        if not self.caminho_pdf.exists():
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {caminho_pdf}")
    
    def extrair_texto_primeira_pagina(self) -> Tuple[str, List[Dict]]:
        """Extrai texto e informações de caracteres da primeira página."""
        with pdfplumber.open(self.caminho_pdf) as pdf:
            primeira_pagina = pdf.pages[0]
            texto = primeira_pagina.extract_text() or ""
            caracteres = primeira_pagina.chars
            return texto, caracteres
    
    def identificar_texto_negrito(self, caracteres: List[Dict]) -> List[str]:
        """Identifica segmentos de texto em negrito a partir dos dados de caracteres."""
        segmentos_negrito = []
        segmento_atual = ""
        
        for char in caracteres:
            nome_fonte = char.get('fontname', '').lower()
            eh_negrito = 'bold' in nome_fonte or 'black' in nome_fonte
            
            if eh_negrito:
                segmento_atual += char.get('text', '')
            else:
                if segmento_atual.strip():
                    segmentos_negrito.append(segmento_atual.strip())
                    segmento_atual = ""
        
        # Adiciona segmento final se existir
        if segmento_atual.strip():
            segmentos_negrito.append(segmento_atual.strip())
        
        return [seg for seg in segmentos_negrito if len(seg) > 3]
    
    def extrair_nomes_medicamentos(self, texto: str, segmentos_negrito: List[str]) -> List[str]:
        """Extrai nomes de medicamentos do texto, priorizando entradas numeradas em negrito."""
        nomes_medicamentos = set()
        
        def eh_nome_medicamento_valido(nome: str) -> bool:
            """Valida se o texto extraído é provavelmente um nome de medicamento."""
            nome_minusculo = nome.lower().strip()
            nome_limpo = nome.strip()
            
            # Verificação de comprimento mínimo
            if len(nome_minusculo) < 4:
                return False
            
            # Verifica contra exclusões
            if nome_minusculo in self.EXCLUSOES_MEDICAMENTOS:
                return False
            
            # Exclusão direta para token problemático específico
            if 'ktsjt' in nome_minusculo or nome_limpo.startswith('kTSJT'):
                return False
            
            # Exclui se for apenas uma unidade ou medida
            if re.match(r'^(mg|ml|un|und|ui|sp|cpf|crm)$', nome_minusculo):
                return False
            
            # Exclui tokens (todas maiúsculas, 6-8 chars) ou códigos com traços/espaços
            if re.match(r'^[A-Z0-9\-\s]{6,8}$', nome_limpo.replace(' ', '').replace('-', '')):
                return False
            
            # Exclusão específica para o padrão de token
            if re.match(r'^[A-Z]{6,8}\s*-?\s*$', nome_limpo):
                return False
            
            # Exclui nomes de médicos (contém "CRM")
            if 'crm' in nome_minusculo:
                return False
            
            # Exclui frases incompletas começando com palavras comuns
            if nome_minusculo.startswith(('data ', 'nome ', 'cpf ', 'hora ')):
                return False
            
            # Exclui componentes compostos (como "Sulfato de gentamicina" de formulações compostas)
            if any(composto in nome_minusculo for composto in ['sulfato de gentamicina', 'dipropionato de betametasona']):
                return False
            
            # Exclui se contém números mas não "mg" (provavelmente não é um medicamento)
            if re.search(r'\d+', nome_limpo) and 'mg' not in nome_minusculo:
                # Exceção: permite se for um padrão de medicamento conhecido
                if not any(palavra_medicamento in nome_minusculo for palavra_medicamento in ['cloridrato', 'dicloridrato', 'mirtazapina', 'insulina', 'trok']):
                    return False
            
            # Deve conter pelo menos uma letra (não apenas números/símbolos)
            if not re.search(r'[a-záàâãéêíóôõúçA-ZÁÀÂÃÉÊÍÓÔÕÚÇ]', nome_limpo):
                return False
            
            # Deve conter pelo menos uma letra minúscula (exclui tokens em maiúsculas)
            if not re.search(r'[a-záàâãéêíóôõúç]', nome_limpo):
                return False
            
            # Exclui formas farmacêuticas que não são nomes de medicamentos
            if any(forma in nome_minusculo for forma in ['comprimido', 'suspensão', 'orodispersível', 'injetável']):
                # Só permite se contém um composto medicamentoso conhecido
                if not any(composto in nome_minusculo for composto in ['cloridrato', 'dicloridrato', 'sulfato', 'mirtazapina', 'insulina', 'trok']):
                    return False
            
            return True
        
        def consolidar_nomes_medicamentos(nomes: set) -> List[str]:
            """Consolida nomes de medicamentos, preferindo versões com dosagem."""
            consolidado = {}
            
            for nome in nomes:
                # Extrai nome base (sem dosagem)
                nome_base = re.sub(r'\s+\d+(?:\.\d+)?mg$', '', nome).strip()
                
                # Se já temos este nome base, prefere a versão com dosagem
                if nome_base in consolidado:
                    atual = consolidado[nome_base]
                    # Prefere a versão com dosagem (contém 'mg')
                    if 'mg' in nome and 'mg' not in atual:
                        consolidado[nome_base] = nome
                    elif 'mg' not in nome and 'mg' in atual:
                        # Mantém atual (tem dosagem)
                        pass
                    else:
                        # Ambos têm ou não têm dosagem, prefere nome mais longo
                        if len(nome) > len(atual):
                            consolidado[nome_base] = nome
                else:
                    consolidado[nome_base] = nome
            
            return list(consolidado.values())
        
        def extrair_medicamentos_numerados_negrito(texto: str, segmentos_negrito: List[str]) -> set:
            """Extrai medicamentos que aparecem como entradas numeradas em negrito."""
            medicamentos_numerados = set()
            linhas = texto.split('\n')
            
            for i, linha in enumerate(linhas):
                # Procura por entradas numeradas (1., 2., 3., etc.)
                if re.match(r'^\s*\d+\.\s*', linha):
                    # Verifica se esta linha ou linhas próximas contêm texto em negrito
                    texto_linha = linha.strip()
                    
                    # Extrai o nome principal do medicamento da entrada numerada
                    # Remove o prefixo numérico
                    linha_medicamento = re.sub(r'^\s*\d+\.\s*', '', texto_linha)
                    
                    # Procura pelo nome principal do medicamento (geralmente a primeira parte antes de vírgula ou descrição detalhada)
                    for padrao in self.PADROES_MEDICAMENTOS:
                        correspondencias = re.findall(padrao, linha_medicamento, re.IGNORECASE)
                        for correspondencia in correspondencias:
                            limpo = correspondencia.strip().strip(',').strip()
                            if eh_nome_medicamento_valido(limpo):
                                medicamentos_numerados.add(limpo)
                                break  # Pega a primeira correspondência válida por entrada numerada
                    
                    # Também verifica se algum segmento em negrito corresponde a esta entrada numerada
                    for segmento in segmentos_negrito:
                        if any(palavra in segmento.lower() for palavra in linha_medicamento.lower().split()[:3]):
                            for padrao in self.PADROES_MEDICAMENTOS:
                                correspondencias = re.findall(padrao, segmento, re.IGNORECASE)
                                for correspondencia in correspondencias:
                                    limpo = correspondencia.strip().strip(',').strip()
                                    if eh_nome_medicamento_valido(limpo):
                                        medicamentos_numerados.add(limpo)
            
            return medicamentos_numerados
        
        # Prioridade 1: Extrai de entradas numeradas em negrito
        medicamentos_numerados = extrair_medicamentos_numerados_negrito(texto, segmentos_negrito)
        nomes_medicamentos.update(medicamentos_numerados)
        
        # Prioridade 2: Extrai de segmentos em negrito (apenas se não foi encontrado em entradas numeradas)
        for segmento in segmentos_negrito:
            for padrao in self.PADROES_MEDICAMENTOS:
                correspondencias = re.findall(padrao, segmento, re.IGNORECASE)
                for correspondencia in correspondencias:
                    limpo = correspondencia.strip().strip(',').strip()
                    if eh_nome_medicamento_valido(limpo) and limpo not in nomes_medicamentos:
                        nomes_medicamentos.add(limpo)
        
        # Consolida duplicatas
        return consolidar_nomes_medicamentos(nomes_medicamentos)
    
    def extrair_quantidades_inline(self, texto: str) -> Dict[str, str]:
        """Extrai quantidades que aparecem inline com nomes de medicamentos (ALTA PRIORIDADE)."""
        quantidades_inline = {}
        linhas = texto.split('\n')
        
        for linha in linhas:
            # Procura por padrões de quantidade inline
            for padrao_qtd in self.PADROES_QUANTIDADE_INLINE:
                correspondencia_qtd = re.search(padrao_qtd, linha, re.IGNORECASE)
                if correspondencia_qtd:
                    # Encontra nome do medicamento na mesma linha (antes da quantidade)
                    linha_antes_qtd = linha[:correspondencia_qtd.start()]
                    
                    for padrao_medicamento in self.PADROES_MEDICAMENTOS:
                        correspondencia_medicamento = re.search(padrao_medicamento, linha_antes_qtd, re.IGNORECASE)
                        if correspondencia_medicamento:
                            nome_medicamento = correspondencia_medicamento.group(1).strip()
                            quantidade = correspondencia_qtd.group(1)
                            
                            # Limpa nome do medicamento (remove vírgulas finais, etc.)
                            nome_medicamento = re.sub(r'[,\s]+$', '', nome_medicamento)
                            
                            quantidades_inline[nome_medicamento] = f"{quantidade}un"
                            break
        
        return quantidades_inline
    
    def extrair_quantidades(self, texto: str) -> Dict[str, str]:
        """Extrai quantidades para medicamentos do texto."""
        quantidades = {}
        linhas = texto.split('\n')
        
        for linha in linhas:
            # Verifica padrões de quantidade
            for padrao in self.PADROES_QUANTIDADE:
                correspondencia = re.search(padrao, linha, re.IGNORECASE)
                if correspondencia:
                    # Encontra nome do medicamento na mesma linha ou linhas próximas
                    for padrao_medicamento in self.PADROES_MEDICAMENTOS:
                        correspondencia_medicamento = re.search(padrao_medicamento, linha, re.IGNORECASE)
                        if correspondencia_medicamento:
                            nome_medicamento = correspondencia_medicamento.group(1).strip()
                            if 'cont' in padrao:  # uso contínuo
                                quantidades[nome_medicamento] = "uso contínuo"
                            else:
                                quantidades[nome_medicamento] = correspondencia.group(1) if correspondencia.group(1) else "1"
                            break
        
        return quantidades
    
    def normalizar_quantidade(self, string_quantidade: str) -> int:
        """Normaliza string de quantidade para inteiro."""
        if not string_quantidade:
            return 1
        
        quantidade_minuscula = string_quantidade.lower()
        
        # Trata casos especiais
        if any(termo in quantidade_minuscula for termo in ['contínuo', 'continuo', 'embalagem']):
            return 1
        
        # Trata formato de quantidade inline (ex: "1un", "2un")
        if 'un' in quantidade_minuscula and not 'contínuo' in quantidade_minuscula:
            numeros = re.findall(r'\d+', string_quantidade)
            return int(numeros[0]) if numeros else 1
        
        # Extrai número de padrões gerais
        numeros = re.findall(r'\d+', string_quantidade)
        return int(numeros[0]) if numeros else 1
    
    def extrair_token_qr(self, texto: str) -> Optional[str]:
        """Extrai token do código QR do final da prescrição."""
        linhas = texto.split('\n')
        
        # Busca nas últimas 10 linhas por tokens de farmácia
        linhas_finais = linhas[-10:]
        
        for linha in linhas_finais:
            # Procura por padrões específicos de token em contexto de farmácia
            correspondencia_token_farmacia = re.search(r'Token\s*\(Farmácia\):\s*([A-Z0-9]{6,8})', linha, re.IGNORECASE)
            if correspondencia_token_farmacia:
                return correspondencia_token_farmacia.group(1)
            
            # Também procura por padrão geral de token no final do documento
            correspondencia_token_geral = re.search(r'Token:\s*([A-Z0-9]{6,8})', linha, re.IGNORECASE)
            if correspondencia_token_geral:
                return correspondencia_token_geral.group(1)
        
        # Fallback: busca por tokens nas linhas finais (excluindo endereços)
        for linha in linhas_finais:
            # Pula linhas que contêm informações de endereço
            if any(palavra_endereco in linha.lower() for palavra_endereco in ['endereço', 'rua', 'avenida', 'av.', 'r.']):
                continue
            
            tokens = re.findall(self.PADRAO_TOKEN, linha)
            if tokens:
                # Retorna o primeiro token encontrado que não está em um endereço
                return tokens[0]
        
        return None

    def extrair_data(self, texto: str) -> Optional[str]:
        """Extrai somente a data (dd/mm/aaaa) da prescrição.

        Procura padrões como:
        - "Data e hora: 19/09/2025 14:32"
        - "Data: 19/09/2025"
        Retorna apenas "19/09/2025" quando encontrado.
        """
        # Primeiro tenta o padrão completo "Data e hora: dd/mm/aaaa ..."
        m = re.search(r'Data\s+e\s+hora:\s*(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if m:
            return m.group(1)

        # Em seguida tenta apenas "Data: dd/mm/aaaa"
        m2 = re.search(r'Data:\s*(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if m2:
            return m2.group(1)

        # Fallback: procura qualquer data dd/mm/aaaa nas primeiras linhas
        todas_datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if todas_datas:
            return todas_datas[0]

        return None
    
    def analisar(self) -> DadosPrescricao:
        """Método principal de análise - extrai todos os dados da prescrição."""
        texto, caracteres = self.extrair_texto_primeira_pagina()
        segmentos_negrito = self.identificar_texto_negrito(caracteres)
        
        # Extrai nomes de medicamentos
        nomes_medicamentos = self.extrair_nomes_medicamentos(texto, segmentos_negrito)
        
        # Extrai quantidades com prioridade: inline > padrões gerais
        quantidades_inline = self.extrair_quantidades_inline(texto)  # ALTA PRIORIDADE
        quantidades_gerais = self.extrair_quantidades(texto)         # FALLBACK
        
        # Cria objetos de informação de medicamentos
        medicamentos = []
        for nome_medicamento in nomes_medicamentos:
            # Prioriza quantidades inline sobre padrões gerais
            if nome_medicamento in quantidades_inline:
                string_quantidade = quantidades_inline[nome_medicamento]
            else:
                string_quantidade = quantidades_gerais.get(nome_medicamento, "uso contínuo")
            
            qtd_normalizada = self.normalizar_quantidade(string_quantidade)
            
            medicamentos.append(InfoMedicamento(
                nome=nome_medicamento,
                quantidade=string_quantidade,
                quantidade_normalizada=qtd_normalizada
            ))
        
        # Extrai token QR
        token_qr = self.extrair_token_qr(texto)

        # Extrai somente a data (sem hora)
        data = self.extrair_data(texto)
        
        return DadosPrescricao(medicamentos=medicamentos, token_qr=token_qr, data=data)
    
    def analisar_para_dict(self) -> Dict:
        """Analisa e retorna dados como dicionário."""
        dados = self.analisar()
        return {
            'medicamentos': [
                {
                    'nome': medicamento.nome,
                    'quantidade': medicamento.quantidade,
                    'quantidade_normalizada': medicamento.quantidade_normalizada
                }
                for medicamento in dados.medicamentos
            ],
            'token_qr': dados.token_qr,
            'data': dados.data
        }


def main():
    """Exemplo de uso do analisador - processa todos os PDFs do diretório."""
    import glob
    import os
    
    # Diretório atual do script
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Busca todos os arquivos PDF no diretório
    padrao_pdf = os.path.join(diretorio_atual, "*.pdf")
    arquivos_pdf = glob.glob(padrao_pdf)
    
    if not arquivos_pdf:
        print("❌ Nenhum arquivo PDF encontrado no diretório.")
        return
    
    print(f"📁 Encontrados {len(arquivos_pdf)} arquivo(s) PDF no diretório:")
    for pdf in arquivos_pdf:
        print(f"   • {os.path.basename(pdf)}")
    print()
    
    # Processa cada PDF encontrado
    for caminho_pdf in arquivos_pdf:
        nome_arquivo = os.path.basename(caminho_pdf)
        print(f"{'='*60}")
        print(f"📄 ANALISANDO: {nome_arquivo}")
        print(f"{'='*60}")
        
        try:
            analisador = AnalisadorPrescricaoMedica(caminho_pdf)
            resultado = analisador.analisar()
            
            print(f"✅ Encontrados {len(resultado.medicamentos)} medicamento(s):")
            
            for i, medicamento in enumerate(resultado.medicamentos, 1):
                print(f"   {i}. {medicamento.nome}")
                print(f"      Quantidade: {medicamento.quantidade} (normalizada: {medicamento.quantidade_normalizada})")
            
            if resultado.token_qr:
                # Mostra a data (somente dd/mm/aaaa) antes do token, quando disponível
                if getattr(resultado, 'data', None):
                    # Linha em branco para espaçamento antes da data
                    print()
                    print(f"🗓️ Data: {resultado.data}")
                print(f"\n🔗 Token QR: {resultado.token_qr}")
            else:
                print("\n⚠️  Nenhum token QR encontrado")
                
        except Exception as e:
            print(f"❌ Erro ao analisar {nome_arquivo}: {e}")
        
        print()  # Linha em branco entre arquivos


if __name__ == "__main__":
    main()