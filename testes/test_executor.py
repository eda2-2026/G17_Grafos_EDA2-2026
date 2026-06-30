"""Testes do motor de texto (mini-linguagem de comandos).

Rodam sem tkinter::

    python -m unittest testes.test_executor
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.executor import aplicar_comando, aplicar_bloco, ErroExecutor


class TestComandos(unittest.TestCase):
    def test_criar_arquivo(self):
        self.assertEqual(aplicar_comando(None, 'CRIAR_ARQUIVO "olá"'), "olá")

    def test_remover_arquivo(self):
        self.assertIsNone(aplicar_comando("qualquer", "REMOVER_ARQUIVO"))

    def test_inserir_apos_linha(self):
        doc = "a\nb\nc"
        self.assertEqual(
            aplicar_comando(doc, 'INSERIR_APOS "b" "novo"'), "a\nb\nnovo\nc"
        )

    def test_inserir_apos_ancora_inexistente(self):
        with self.assertRaises(ErroExecutor):
            aplicar_comando("a\nb", 'INSERIR_APOS "x" "y"')

    def test_inserir_fim(self):
        self.assertEqual(aplicar_comando("a", 'INSERIR_FIM "b"'), "a\nb")

    def test_inserir_fim_em_vazio(self):
        self.assertEqual(aplicar_comando("", 'INSERIR_FIM "b"'), "b")

    def test_remover_texto_primeira_ocorrencia(self):
        self.assertEqual(aplicar_comando("xyx", 'REMOVER_TEXTO "x"'), "yx")

    def test_remover_texto_inexistente(self):
        with self.assertRaises(ErroExecutor):
            aplicar_comando("abc", 'REMOVER_TEXTO "z"')

    def test_substituir_primeira_ocorrencia(self):
        self.assertEqual(aplicar_comando("a a", 'SUBSTITUIR "a" "b"'), "b a")

    def test_substituir_inexistente(self):
        with self.assertRaises(ErroExecutor):
            aplicar_comando("abc", 'SUBSTITUIR "z" "w"')

    def test_comando_desconhecido(self):
        with self.assertRaises(ErroExecutor):
            aplicar_comando("abc", 'FAZER_MAGICA "x"')

    def test_comando_em_documento_inexistente(self):
        with self.assertRaises(ErroExecutor):
            aplicar_comando(None, 'INSERIR_FIM "x"')


class TestEscapes(unittest.TestCase):
    def test_quebra_de_linha(self):
        self.assertEqual(aplicar_comando(None, r'CRIAR_ARQUIVO "a\nb"'), "a\nb")

    def test_aspas_literais(self):
        self.assertEqual(aplicar_comando(None, r'CRIAR_ARQUIVO "diz \"oi\""'), 'diz "oi"')

    def test_barra_invertida(self):
        self.assertEqual(aplicar_comando(None, r'CRIAR_ARQUIVO "c:\\temp"'), "c:\\temp")


class TestParesInversos(unittest.TestCase):
    """up seguido do down correspondente volta ao conteúdo original."""

    def _round_trip(self, conteudo, up, down):
        depois = aplicar_comando(conteudo, up)
        voltou = aplicar_comando(depois, down)
        self.assertEqual(voltou, conteudo)

    def test_inserir_apos_remover_texto(self):
        self._round_trip(
            "## Sumário\nfim",
            'INSERIR_APOS "## Sumário" "## Introdução\\ntexto"',
            'REMOVER_TEXTO "## Introdução\\ntexto"',
        )

    def test_inserir_fim_remover_texto(self):
        self._round_trip("início", 'INSERIR_FIM "rodapé"', 'REMOVER_TEXTO "rodapé"')

    def test_substituir_ida_e_volta(self):
        self._round_trip(
            "## Introdução", 'SUBSTITUIR "## Introdução" "## 1. Introdução"',
            'SUBSTITUIR "## 1. Introdução" "## Introdução"',
        )

    def test_criar_remover_arquivo(self):
        depois = aplicar_comando(None, 'CRIAR_ARQUIVO "x"')
        self.assertEqual(depois, "x")
        self.assertIsNone(aplicar_comando(depois, "REMOVER_ARQUIVO"))


class TestBloco(unittest.TestCase):
    def test_aplicar_bloco_em_sequencia(self):
        comandos = [
            'CRIAR_ARQUIVO "# Trabalho\\n## Sumário\\n## Bibliografia"',
            'INSERIR_APOS "## Sumário" "## Metodologia"',
            'INSERIR_APOS "## Sumário" "## Introdução"',
            'SUBSTITUIR "## Introdução" "## 1. Introdução"',
        ]
        resultado = aplicar_bloco(None, comandos)
        self.assertIn("## 1. Introdução", resultado)
        self.assertIn("## Metodologia", resultado)
        self.assertTrue(resultado.startswith("# Trabalho"))


if __name__ == "__main__":
    unittest.main()
