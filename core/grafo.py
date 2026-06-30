"""Grafo direcionado e seus algoritmos, **implementados à mão**.

Este é o conteúdo avaliado da disciplina (Estrutura de Dados 2 — grafos).
Nada aqui usa biblioteca de grafos. A única importação da biblioteca padrão
é ``heapq``, usada apenas como fila de prioridade para tornar a saída da
ordenação topológica determinística — a lógica de Kahn em si é manual.

Representação:
    - lista de adjacência: ``self.adjacencia[v]`` = lista dos vértices que
      dependem de ``v`` (ou seja, as arestas ``v -> w``);
    - grau de entrada: ``self.grau_entrada[w]`` = quantas arestas chegam em ``w``.
"""

import heapq


class ErroCiclo(Exception):
    """Levantado quando o grafo contém um ciclo (não é um DAG).

    :ivar vertices: lista (ordenada) dos vértices que fazem parte do ciclo,
        ou seja, os que nunca chegaram a grau de entrada zero.
    """

    def __init__(self, vertices):
        self.vertices = sorted(vertices)
        super().__init__(
            "Ciclo de dependências detectado envolvendo: %s"
            % ", ".join(self.vertices)
        )


class Grafo:
    """Grafo direcionado com lista de adjacência e grau de entrada próprios."""

    def __init__(self):
        # id -> lista de vértices destino (arestas v -> w).
        self.adjacencia = {}
        # id -> número de arestas que chegam.
        self.grau_entrada = {}

    def adicionar_vertice(self, v):
        """Registra um vértice (idempotente)."""
        if v not in self.adjacencia:
            self.adjacencia[v] = []
            self.grau_entrada[v] = 0

    def adicionar_aresta(self, origem, destino):
        """Adiciona a aresta ``origem -> destino``.

        Semântica de dependência: ``origem`` deve ser aplicada **antes** de
        ``destino``. Incrementa o grau de entrada de ``destino``.
        """
        self.adicionar_vertice(origem)
        self.adicionar_vertice(destino)
        self.adjacencia[origem].append(destino)
        self.grau_entrada[destino] += 1

    @property
    def vertices(self):
        """Lista de todos os vértices do grafo."""
        return list(self.adjacencia.keys())

    def _kahn(self):
        """Roda o algoritmo de Kahn.

        :returns: tupla ``(ordem, grau_restante)`` onde ``ordem`` é a lista de
            vértices em ordem topológica obtida e ``grau_restante`` é o grau de
            entrada que sobrou em cada vértice (qualquer valor > 0 indica ciclo).
        """
        # Cópia do grau de entrada para não mutar o estado do grafo.
        grau = dict(self.grau_entrada)

        # Fila de prioridade por id: garante saída determinística — entre os
        # vértices prontos (grau 0), processa-se sempre o de menor id.
        fila = [v for v in grau if grau[v] == 0]
        heapq.heapify(fila)

        ordem = []
        while fila:
            v = heapq.heappop(fila)
            ordem.append(v)
            for w in self.adjacencia[v]:
                grau[w] -= 1
                if grau[w] == 0:
                    heapq.heappush(fila, w)

        return ordem, grau

    def ordenacao_topologica(self):
        """Devolve os vértices em ordem topológica (Kahn, determinística).

        :raises ErroCiclo: se houver ciclo — nesse caso a exceção carrega os
            vértices que nunca atingiram grau de entrada zero.
        """
        ordem, grau = self._kahn()
        if len(ordem) < len(self.adjacencia):
            # Os vértices com grau restante > 0 fazem parte do(s) ciclo(s).
            restantes = [v for v in grau if grau[v] > 0]
            raise ErroCiclo(restantes)
        return ordem

    def detectar_ciclo(self):
        """Verifica se há ciclo sem levantar exceção.

        :returns: lista (ordenada) dos vértices envolvidos no ciclo, ou
            ``None`` se o grafo for um DAG.
        """
        ordem, grau = self._kahn()
        if len(ordem) < len(self.adjacencia):
            return sorted(v for v in grau if grau[v] > 0)
        return None
