# 🥇 Medalista - Extrator de Medicamentos e Token de Prescrições Médicas

## O que faz
- Lê arquivos PDF de receitas médicas
- Encontra nomes de medicamentos
- Abre pesquisas no site Qualidoc
- Copia códigos QR token da receita

## Como instalar
1. Baixe o Python (versão 3.8 ou mais nova)
2. Abra o terminal e digite:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Arquivos do programa

```
medalista.py      - Programa principal
qualidoc.py       - Abre pesquisas no Qualidoc
requirements.txt  - Lista de dependências
```

## Como usar

### Modo simples
Coloque seus PDFs na pasta e digite:

```bash
python medalista.py
```

### Modo automático
Para abrir pesquisas no Qualidoc automaticamente:

```bash
python qualidoc.py
```

## Exemplo de uso no código

```python
from medalista import AnalisadorPrescricaoMedica

# Analisa uma receita
analisador = AnalisadorPrescricaoMedica("receita.pdf")
resultado = analisador.analisar()

# Mostra os medicamentos encontrados
for medicamento in resultado.medicamentos:
    print(f"Medicamento: {medicamento.nome}")
    print(f"Quantidade: {medicamento.quantidade}")
```

## Problemas comuns

**Erro: Arquivo não encontrado**
- Verifique se o PDF está na pasta correta

**Erro: Nenhum medicamento encontrado**
- Verifique se o PDF tem texto (não é só imagem)

**Erro: Módulo não encontrado**
- Execute: `pip install -r requirements.txt`
