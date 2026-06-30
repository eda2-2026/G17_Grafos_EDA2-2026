"""Persistência do estado das migrations em ``.estado.json``.

O arquivo fica dentro da própria pasta de migrations e guarda quais migrations
já foram aplicadas, **na ordem em que foram aplicadas** (que é a ordem
topológica até aquele ponto).

Formato::

    {
      "documento": "trabalho_final.txt",
      "aplicadas": ["001_criar_estrutura", "002_inserir_metodologia"]
    }
"""

import json
import os

NOME_ARQUIVO = ".estado.json"
DOCUMENTO_PADRAO = "trabalho_final.txt"


def caminho_estado(pasta):
    """Caminho do arquivo de estado dentro de ``pasta``."""
    return os.path.join(pasta, NOME_ARQUIVO)


def carregar_estado(pasta):
    """Lê o estado da pasta; devolve o padrão se ainda não existir.

    :returns: dicionário com as chaves ``documento`` e ``aplicadas``.
    """
    caminho = caminho_estado(pasta)
    if not os.path.isfile(caminho):
        return {"documento": DOCUMENTO_PADRAO, "aplicadas": []}
    with open(caminho, "r", encoding="utf-8") as fp:
        dados = json.load(fp)
    dados.setdefault("documento", DOCUMENTO_PADRAO)
    dados.setdefault("aplicadas", [])
    return dados


def salvar_estado(pasta, estado):
    """Grava o estado em ``.estado.json`` dentro de ``pasta``."""
    caminho = caminho_estado(pasta)
    with open(caminho, "w", encoding="utf-8") as fp:
        json.dump(estado, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
