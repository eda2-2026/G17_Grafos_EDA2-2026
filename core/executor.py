"""Motor de texto: aplica os comandos da mini-linguagem sobre o documento.

O documento é representado como uma ``str`` em memória. O estado "arquivo
inexistente" (antes de ``CRIAR_ARQUIVO`` / depois de ``REMOVER_ARQUIVO``) é
representado por ``None``.

Comandos disponíveis (um por linha, argumentos sempre entre aspas duplas):

==========================  ===============================================
Comando                     Efeito
==========================  ===============================================
CRIAR_ARQUIVO "<txt>"       Cria o documento com o conteúdo inicial.
REMOVER_ARQUIVO             Apaga o documento.
INSERIR_APOS "<anc>" "<t>"  Insere <t> após a primeira linha igual a <anc>.
INSERIR_FIM "<t>"           Acrescenta <t> ao final.
REMOVER_TEXTO "<t>"         Remove a 1ª ocorrência de <t> (e a quebra de
                            linha adjacente — inverso de INSERIR_*).
SUBSTITUIR "<a>" "<b>"      Troca a primeira ocorrência de <a> por <b>.
==========================  ===============================================

Escapes dentro das aspas: ``\\n`` = quebra de linha, ``\\"`` = aspas
literais, ``\\\\`` = barra invertida.
"""

import re


class ErroExecutor(Exception):
    """Erro ao executar um comando (comando inválido ou alvo não encontrado)."""


# Captura uma sequência de argumentos entre aspas duplas, respeitando escapes.
_ARG = re.compile(r'"((?:\\.|[^"\\])*)"')


def _desescapar(texto):
    """Converte os escapes ``\\n``, ``\\"`` e ``\\\\`` nos caracteres reais."""
    resultado = []
    i = 0
    while i < len(texto):
        c = texto[i]
        if c == "\\" and i + 1 < len(texto):
            prox = texto[i + 1]
            if prox == "n":
                resultado.append("\n")
            elif prox == '"':
                resultado.append('"')
            elif prox == "\\":
                resultado.append("\\")
            else:
                # Escape desconhecido: mantém literal (barra + caractere).
                resultado.append(c)
                resultado.append(prox)
            i += 2
        else:
            resultado.append(c)
            i += 1
    return "".join(resultado)


def _parse_comando(comando):
    """Separa o nome do comando e seus argumentos já desescapados.

    :returns: tupla ``(nome, [args])``.
    """
    comando = comando.strip()
    if not comando:
        raise ErroExecutor("Comando vazio.")
    nome = comando.split()[0].upper()
    args = [_desescapar(m.group(1)) for m in _ARG.finditer(comando)]
    return nome, args


def _exigir_arquivo(conteudo, comando):
    if conteudo is None:
        raise ErroExecutor(
            "Não há documento para executar %r (use CRIAR_ARQUIVO antes)." % comando
        )


def aplicar_comando(conteudo, comando):
    """Aplica um único comando e devolve o novo conteúdo do documento.

    :param conteudo: conteúdo atual (``str``) ou ``None`` se o arquivo não existe.
    :param comando: linha de comando crua (ex.: ``INSERIR_FIM "fim"``).
    :returns: novo conteúdo (``str`` ou ``None``).
    :raises ErroExecutor: comando desconhecido, argumentos errados ou alvo ausente.
    """
    nome, args = _parse_comando(comando)

    if nome == "CRIAR_ARQUIVO":
        if len(args) != 1:
            raise ErroExecutor('CRIAR_ARQUIVO exige 1 argumento: "<conteúdo>".')
        return args[0]

    if nome == "REMOVER_ARQUIVO":
        return None

    if nome == "INSERIR_APOS":
        if len(args) != 2:
            raise ErroExecutor('INSERIR_APOS exige 2 argumentos: "<âncora>" "<texto>".')
        _exigir_arquivo(conteudo, comando)
        ancora, texto = args
        linhas = conteudo.split("\n")
        for i, linha in enumerate(linhas):
            if linha == ancora:
                linhas.insert(i + 1, texto)
                return "\n".join(linhas)
        raise ErroExecutor("Âncora não encontrada para INSERIR_APOS: %r." % ancora)

    if nome == "INSERIR_FIM":
        if len(args) != 1:
            raise ErroExecutor('INSERIR_FIM exige 1 argumento: "<texto>".')
        _exigir_arquivo(conteudo, comando)
        if conteudo == "":
            return args[0]
        return conteudo + "\n" + args[0]

    if nome == "REMOVER_TEXTO":
        if len(args) != 1:
            raise ErroExecutor('REMOVER_TEXTO exige 1 argumento: "<texto>".')
        _exigir_arquivo(conteudo, comando)
        alvo = args[0]
        ini = conteudo.find(alvo)
        if ini < 0:
            raise ErroExecutor("Texto não encontrado para REMOVER_TEXTO: %r." % alvo)
        fim = ini + len(alvo)
        # Consome um único '\n' adjacente para que a remoção seja o inverso
        # exato de um INSERIR_APOS/INSERIR_FIM (que adicionam o bloco como
        # uma linha). Preferência pela quebra de linha posterior; senão, a
        # anterior. Assim "remover o bloco" não deixa linha em branco órfã.
        if fim < len(conteudo) and conteudo[fim] == "\n":
            fim += 1
        elif ini > 0 and conteudo[ini - 1] == "\n":
            ini -= 1
        return conteudo[:ini] + conteudo[fim:]

    if nome == "SUBSTITUIR":
        if len(args) != 2:
            raise ErroExecutor('SUBSTITUIR exige 2 argumentos: "<antigo>" "<novo>".')
        _exigir_arquivo(conteudo, comando)
        antigo, novo = args
        if antigo not in conteudo:
            raise ErroExecutor("Texto não encontrado para SUBSTITUIR: %r." % antigo)
        return conteudo.replace(antigo, novo, 1)

    raise ErroExecutor("Comando desconhecido: %r." % nome)


def aplicar_bloco(conteudo, comandos):
    """Aplica uma lista de comandos em sequência sobre o documento.

    :param conteudo: conteúdo inicial (``str`` ou ``None``).
    :param comandos: lista de linhas de comando.
    :returns: conteúdo resultante (``str`` ou ``None``).
    """
    for comando in comandos:
        conteudo = aplicar_comando(conteudo, comando)
    return conteudo
