"""Testes do grafo: ordenação topológica determinística e detecção de ciclo.

Rodam sem tkinter::

    python -m unittest testes.test_grafo
"""

import os
import sys
import unittest

# Permite rodar tanto via `python -m unittest` na raiz quanto diretamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grafo import Grafo, ErroCiclo


def grafo_diamante():
    """DAG em diamante: 001 -> {002, 003} -> 004."""
    g = Grafo()
    for v in ("001", "002", "003", "004"):
        g.adicionar_vertice(v)
    g.adicionar_aresta("001", "002")
    g.adicionar_aresta("001", "003")
    g.adicionar_aresta("002", "004")
    g.adicionar_aresta("003", "004")
    return g


class TestOrdenacaoTopologica(unittest.TestCase):
    def test_diamante_deterministico(self):
        g = grafo_diamante()
        # Fila de prioridade por id: 002 sai antes de 003.
        self.assertEqual(g.ordenacao_topologica(), ["001", "002", "003", "004"])

    def test_saida_estavel_em_varias_chamadas(self):
        g = grafo_diamante()
        primeira = g.ordenacao_topologica()
        for _ in range(5):
            self.assertEqual(g.ordenacao_topologica(), primeira)

    def test_respeita_dependencias(self):
        ordem = grafo_diamante().ordenacao_topologica()
        self.assertLess(ordem.index("001"), ordem.index("002"))
        self.assertLess(ordem.index("001"), ordem.index("003"))
        self.assertLess(ordem.index("002"), ordem.index("004"))
        self.assertLess(ordem.index("003"), ordem.index("004"))

    def test_apenas_raizes_ordem_alfabetica(self):
        g = Grafo()
        for v in ("z", "a", "m"):
            g.adicionar_vertice(v)
        self.assertEqual(g.ordenacao_topologica(), ["a", "m", "z"])

    def test_grau_de_entrada(self):
        g = grafo_diamante()
        self.assertEqual(g.grau_entrada["001"], 0)
        self.assertEqual(g.grau_entrada["002"], 1)
        self.assertEqual(g.grau_entrada["003"], 1)
        self.assertEqual(g.grau_entrada["004"], 2)

    def test_ordenacao_nao_muta_grafo(self):
        g = grafo_diamante()
        g.ordenacao_topologica()
        # Grau de entrada deve permanecer intacto após a ordenação.
        self.assertEqual(g.grau_entrada["004"], 2)


class TestDeteccaoCiclo(unittest.TestCase):
    def test_ciclo_simples_a_b(self):
        g = Grafo()
        g.adicionar_aresta("a", "b")
        g.adicionar_aresta("b", "a")
        self.assertEqual(g.detectar_ciclo(), ["a", "b"])

    def test_ordenacao_levanta_erro_em_ciclo(self):
        g = Grafo()
        g.adicionar_aresta("a", "b")
        g.adicionar_aresta("b", "a")
        with self.assertRaises(ErroCiclo) as ctx:
            g.ordenacao_topologica()
        self.assertEqual(ctx.exception.vertices, ["a", "b"])

    def test_dag_nao_tem_ciclo(self):
        self.assertIsNone(grafo_diamante().detectar_ciclo())

    def test_ciclo_maior_reporta_envolvidos(self):
        g = Grafo()
        # raiz -> x -> y -> z -> x  (x, y, z em ciclo; raiz fora)
        g.adicionar_aresta("raiz", "x")
        g.adicionar_aresta("x", "y")
        g.adicionar_aresta("y", "z")
        g.adicionar_aresta("z", "x")
        self.assertEqual(g.detectar_ciclo(), ["x", "y", "z"])


if __name__ == "__main__":
    unittest.main()
