#!/usr/bin/env python3
"""
Script de Automação do Navegador Qualidoc

Este script extrai nomes de medicamentos de um PDF de prescrição médica e abre
abas de pesquisa do Qualidoc para cada medicamento usando o navegador padrão do sistema.
Em seguida, extrai e copia o token único do PDF para a área de transferência.

Funcionalidades:
- Usa o navegador padrão do sistema (não precisa do ChromeDriver)
- Extrai nomes de medicamentos do PDF usando MedicalPrescriptionParser
- Abre novas abas para cada pesquisa de medicamento diretamente no Qualidoc
- Extrai token único do PDF e copia para a área de transferência
- Busca automática por todos os arquivos PDF no diretório

Requisitos:
- pyperclip (para operações da área de transferência)
- Arquivo PDF de prescrição médica
"""

import webbrowser
import time
import urllib.parse
import pyperclip
import glob
import os
from pathlib import Path
from medalista import AnalisadorPrescricaoMedica


class AutomacaoNavegadorQualidoc:
    """
    Automatiza pesquisas de medicamentos no Qualidoc usando o navegador padrão do sistema.
    """
    
    def __init__(self, caminho_pdf: str):
        """
        Inicializa a automação com o caminho do PDF.
        
        Args:
            caminho_pdf (str): Caminho para o PDF de prescrição médica
        """
        self.caminho_pdf = Path(caminho_pdf)
        self.url_base = "https://www.qualidoc.com.br/search?Ntt="
        
        # Valida se o PDF existe
        if not self.caminho_pdf.exists():
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {caminho_pdf}")
        
        # Inicializa o parser com o caminho do PDF
        self.parser = AnalisadorPrescricaoMedica(str(self.caminho_pdf))
    
    def extrair_nomes_medicamentos(self) -> list[str]:
        """
        Extrai nomes de medicamentos do PDF usando o parser.
        
        Returns:
            list[str]: Lista de nomes de medicamentos encontrados na prescrição
        """
        print(f"📄 Extraindo nomes de medicamentos de: {self.caminho_pdf.name}")
        
        try:
            # Analisa o PDF e extrai nomes de medicamentos
            dados_analisados = self.parser.analisar()
            nomes_medicamentos = [medicamento.nome for medicamento in dados_analisados.medicamentos]
            
            print(f"✅ Encontrados {len(nomes_medicamentos)} medicamentos:")
            for i, medicamento in enumerate(nomes_medicamentos, 1):
                print(f"   {i}. {medicamento}")
            
            return nomes_medicamentos
            
        except Exception as e:
            print(f"❌ Erro ao extrair nomes de medicamentos: {e}")
            return []
    
    def construir_url_pesquisa(self, nome_medicamento: str) -> str:
        """
        Constrói URL de pesquisa do Qualidoc para um nome de medicamento
        
        Args:
            nome_medicamento (str): Nome do medicamento para pesquisar
            
        Returns:
            str: URL completa de pesquisa do Qualidoc
        """
        # Codifica o nome do medicamento para construção segura da URL
        medicamento_codificado = urllib.parse.quote_plus(nome_medicamento)
        
        # Constrói URL de pesquisa do Qualidoc
        return f"{self.url_base}{medicamento_codificado}"
    
    def abrir_pesquisa_medicamento(self, nome_medicamento: str) -> bool:
        """
        Abre uma nova aba do navegador com pesquisa do Qualidoc para o medicamento
        
        Args:
            nome_medicamento (str): Nome do medicamento para pesquisar
            
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            url_pesquisa = self.construir_url_pesquisa(nome_medicamento)
            print(f"🔍 Pesquisando por: {nome_medicamento} no Qualidoc")
            print(f"   URL do Qualidoc: {url_pesquisa}")
            
            # Abre nova aba com a URL de pesquisa
            webbrowser.open_new_tab(url_pesquisa)
            
            # Pequeno atraso para não sobrecarregar o navegador
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao abrir pesquisa para {nome_medicamento}: {e}")
            return False
    
    def processar_todos_medicamentos(self, nomes_medicamentos: list[str]) -> dict[str, str]:
        """
        Abre abas do navegador para todas as pesquisas de medicamentos no Qualidoc.
        
        Args:
            nomes_medicamentos (list[str]): Lista de nomes de medicamentos para pesquisar
            
        Returns:
            dict[str, str]: Resultados mapeando nomes de medicamentos para status
        """
        resultados = {}
        total_medicamentos = len(nomes_medicamentos)
        
        print(f"\n🚀 Abrindo {total_medicamentos} pesquisas do Qualidoc...")
        
        for i, nome_medicamento in enumerate(nomes_medicamentos, 1):
            print(f"\n📋 Processando medicamento {i}/{total_medicamentos}: {nome_medicamento}")
            
            sucesso = self.abrir_pesquisa_medicamento(nome_medicamento)
            resultados[nome_medicamento] = "aberto" if sucesso else "falhou"
            
            # Breve pausa entre pesquisas
            if i < total_medicamentos:
                time.sleep(0.5)
        
        print(f"\n✅ Concluído abertura de todas as pesquisas do Qualidoc!")
        return resultados
    
    def extrair_token_pdf(self) -> str:
        """
        Extrai o token único do PDF.
        
        Returns:
            str: O token extraído ou string vazia se não encontrado
        """
        try:
            # Analisa o PDF para extrair o token
            dados_analisados = self.parser.analisar()
            
            if dados_analisados.token_qr:
                print(f"🎯 Token do PDF encontrado: {dados_analisados.token_qr}")
                return dados_analisados.token_qr
            else:
                print("⚠ Nenhum token encontrado no PDF")
                return ""
                
        except Exception as e:
            print(f"❌ Erro ao extrair token do PDF: {e}")
            return ""
    
    def executar_automacao(self) -> dict[str, str]:
        """
        Executa o processo completo de automação.
        
        Returns:
            dict[str, str]: Resultados da automação
        """
        print("🚀 Iniciando Automação do Navegador Qualidoc...")
        print("=" * 60)
        
        try:
            # Extrai nomes de medicamentos do PDF
            nomes_medicamentos = self.extrair_nomes_medicamentos()
            
            if not nomes_medicamentos:
                print("❌ Nenhum nome de medicamento encontrado. Automação interrompida.")
                return {}
            
            # Abre abas do navegador para todos os medicamentos
            resultados = self.processar_todos_medicamentos(nomes_medicamentos)
            
            # Extrai e copia token do PDF no final
            print(f"\n🎯 Extraindo token do PDF...")
            token_pdf = self.extrair_token_pdf()
            
            # Imprime resumo
            print("\n📊 RESUMO DA AUTOMAÇÃO:")
            print("=" * 50)
            for medicamento, status in resultados.items():
                icone_status = "✓" if status == "aberto" else "✗"
                print(f"{icone_status} {medicamento}: {status}")
            
            # Copia token do PDF para área de transferência
            if token_pdf:
                pyperclip.copy(token_pdf)
                print(f"\n📋 Token do PDF copiado para área de transferência: {token_pdf}")
            else:
                print(f"\n⚠ Nenhum token do PDF encontrado para copiar")
            
            print(f"\n🎉 Automação concluída! Verifique as abas do seu navegador.")
            
            return resultados
            
        except Exception as e:
            print(f"❌ Automação falhou: {e}")
            return {}


def buscar_arquivos_pdf() -> list[str]:
    """
    Busca automaticamente todos os arquivos PDF no diretório atual.
    
    Returns:
        list[str]: Lista de caminhos dos arquivos PDF encontrados
   """
    # Diretório atual do script
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Busca todos os arquivos PDF
    arquivos_pdf = glob.glob(os.path.join(diretorio_atual, "*.pdf"))
    
    if arquivos_pdf:
        print(f"📁 Encontrados {len(arquivos_pdf)} arquivo(s) PDF:")
        for i, arquivo in enumerate(arquivos_pdf, 1):
            nome_arquivo = os.path.basename(arquivo)
            print(f"  {i}. {nome_arquivo}")
    else:
        print("⚠ Nenhum arquivo PDF encontrado no diretório.")
    
    return arquivos_pdf


def main():
    """
    Função principal para executar a automação em todos os PDFs encontrados.
    """
    try:
        # Busca arquivos PDF automaticamente
        arquivos_pdf = buscar_arquivos_pdf()
        
        if not arquivos_pdf:
            print("❌ Nenhum arquivo PDF encontrado. Encerrando automação.")
            return
        
        print(f"\n🚀 Iniciando processamento de {len(arquivos_pdf)} arquivo(s) PDF...")
        
        # Processa cada PDF encontrado
        for i, caminho_pdf in enumerate(arquivos_pdf, 1):
            nome_arquivo = os.path.basename(caminho_pdf)
            
            print(f"\n{'='*70}")
            print(f"📄 PROCESSANDO [{i}/{len(arquivos_pdf)}]: {nome_arquivo}")
            print(f"{'='*70}")
            
            try:
                # Cria instância da automação
                automacao = AutomacaoNavegadorQualidoc(caminho_pdf)
                
                # Executa automação
                resultados = automacao.executar_automacao()
                
                # Imprime resultados
                print(f"\n✅ Processamento concluído para {nome_arquivo}")
                print(f"📊 Resultados: {resultados}")
                
            except Exception as e:
                print(f"❌ Erro ao processar {nome_arquivo}: {e}")
            
            # Pausa entre arquivos (exceto no último)
            if i < len(arquivos_pdf):
                print(f"\n⏳ Aguardando 2 segundos antes do próximo arquivo...")
                time.sleep(2)
        
        print(f"\n🎉 Processamento completo! {len(arquivos_pdf)} arquivo(s) processado(s).")
        
    except Exception as e:
        print(f"❌ Erro na função principal: {e}")


if __name__ == "__main__":
    main()