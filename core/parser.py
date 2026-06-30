"""Leitura dos arquivos de migration (``.mig``).

Cada arquivo descreve uma migration: um cabeçalho com o id e as dependências,
seguido dos blocos ``[up]`` (aplicar) e ``[down]`` (reverter). Cada bloco é
uma lista de comandos da mini-linguagem (ver :mod:`core.executor`), um por
linha.

Exemplo de arquivo::

    -- migration: 003_inserir_introducao
    -- depends: 001_criar_estrutura

    [up]
    INSERIR_APOS "## Sumário" "## Introdução\\nTexto..."

    [down]
    REMOVER_TEXTO "## Introdução\\nTexto..."
"""

import os


class ErroParser(Exception):
    """Erro de formato ao ler um arquivo de migration."""


class Migration:
    """Uma unidade de alteração do documento.

    :param id: identificador único (ex.: ``003_inserir_introducao``).
    :param depends: ids das migrations que precisam ser aplicadas antes desta.
    :param up: lista de comandos (linhas cruas) que aplicam a alteração.
    :param down: lista de comandos (linhas cruas) que revertem a alteração.
    """

    def __init__(self, id, depends, up, down):
        self.id = id
        self.depends = depends
        self.up = up
        self.down = down

    def __repr__(self):
        return "Migration(id=%r, depends=%r)" % (self.id, self.depends)


def parse_migration(texto, origem=None):
    """Converte o conteúdo textual de um ``.mig`` em uma :class:`Migration`.

    :param texto: conteúdo completo do arquivo.
    :param origem: nome do arquivo (apenas para mensagens de erro).
    :raises ErroParser: se faltar o id, ou se o bloco ``[up]`` estiver ausente.
    """
    de = " (em %s)" % origem if origem else ""

    id_migration = None
    depends = []
    # secao_atual: None (cabeçalho), "up" ou "down".
    secao_atual = None
    blocos = {"up": [], "down": []}

    for linha in texto.splitlines():
        crua = linha.strip()
        if not crua:
            continue

        if crua.startswith("--"):
            # Linha de cabeçalho: "-- chave: valor".
            corpo = crua[2:].strip()
            if ":" not in corpo:
                continue
            chave, valor = corpo.split(":", 1)
            chave = chave.strip().lower()
            valor = valor.strip()
            if chave == "migration":
                id_migration = valor
            elif chave == "depends":
                depends = [d.strip() for d in valor.split(",") if d.strip()]
            continue

        if crua.lower() == "[up]":
            secao_atual = "up"
            continue
        if crua.lower() == "[down]":
            secao_atual = "down"
            continue

        # Linha de comando dentro de um bloco.
        if secao_atual is None:
            raise ErroParser(
                "Comando fora de um bloco [up]/[down]%s: %r" % (de, crua)
            )
        blocos[secao_atual].append(crua)

    if not id_migration:
        raise ErroParser("Arquivo de migration sem '-- migration: <id>'%s." % de)
    if not blocos["up"]:
        raise ErroParser(
            "Migration %r não tem bloco [up] com comandos%s." % (id_migration, de)
        )

    return Migration(id_migration, depends, blocos["up"], blocos["down"])


def carregar_migrations(pasta):
    """Lê todos os arquivos ``*.mig`` de ``pasta``.

    :returns: dicionário ``{id: Migration}``.
    :raises ErroParser: em arquivo malformado ou id duplicado.
    :raises FileNotFoundError: se a pasta não existir.
    """
    if not os.path.isdir(pasta):
        raise FileNotFoundError("Pasta de migrations não encontrada: %s" % pasta)

    migrations = {}
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith(".mig") or nome.startswith("."):
            continue
        caminho = os.path.join(pasta, nome)
        with open(caminho, "r", encoding="utf-8") as fp:
            texto = fp.read()
        migration = parse_migration(texto, origem=nome)
        if migration.id in migrations:
            raise ErroParser(
                "Id de migration duplicado: %r (arquivo %s)." % (migration.id, nome)
            )
        migrations[migration.id] = migration

    return migrations
