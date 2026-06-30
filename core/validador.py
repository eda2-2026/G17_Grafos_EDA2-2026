"""Validação do conjunto de migrations antes de calcular a ordem.

Duas verificações, ambas com mensagens claras em português:

1. **Dependência inexistente**: alguma migration aponta, em ``depends``, para
   um id que não foi carregado.
2. **Ciclo**: as dependências formam um ciclo (não é um DAG).
"""

from core.grafo import Grafo, ErroCiclo


class ErroDependenciaInexistente(Exception):
    """Alguma migration depende de um id que não existe.

    :ivar faltantes: dicionário ``{id_migration: [deps_faltantes]}``.
    """

    def __init__(self, faltantes):
        self.faltantes = faltantes
        partes = [
            "%s depende de %s" % (mig, ", ".join(deps))
            for mig, deps in sorted(faltantes.items())
        ]
        super().__init__(
            "Dependência(s) inexistente(s): " + "; ".join(partes) + "."
        )


def construir_grafo(migrations):
    """Monta o :class:`~core.grafo.Grafo` a partir das migrations.

    Para cada migration ``A`` com ``depends = [B, C]`` adiciona as arestas
    ``B -> A`` e ``C -> A`` (a dependência aponta para a dependente).
    """
    grafo = Grafo()
    for mig in migrations.values():
        grafo.adicionar_vertice(mig.id)
    for mig in migrations.values():
        for dep in mig.depends:
            grafo.adicionar_aresta(dep, mig.id)
    return grafo


def validar(migrations):
    """Valida o conjunto de migrations.

    :param migrations: dicionário ``{id: Migration}``.
    :returns: o :class:`~core.grafo.Grafo` construído (já validado).
    :raises ErroDependenciaInexistente: se houver ``depends`` para id ausente.
    :raises ErroCiclo: se as dependências formarem um ciclo.
    """
    # 1. Dependências inexistentes.
    faltantes = {}
    for mig in migrations.values():
        ausentes = [dep for dep in mig.depends if dep not in migrations]
        if ausentes:
            faltantes[mig.id] = ausentes
    if faltantes:
        raise ErroDependenciaInexistente(faltantes)

    # 2. Ciclos (delegado ao grafo, que detecta via Kahn).
    grafo = construir_grafo(migrations)
    ciclo = grafo.detectar_ciclo()
    if ciclo is not None:
        raise ErroCiclo(ciclo)

    return grafo
