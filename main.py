"""Ponto de entrada: abre a interface gráfica do migrador.

Uso::

    python main.py                       # usa exemplos/migrations
    python main.py exemplos/ciclo        # abre outra pasta de migrations

Toda a lógica vive em ``core/`` (sem tkinter); este script apenas inicia a UI.
"""

import os
import sys

from ui.app import iniciar

PASTA_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "exemplos", "migrations")


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else PASTA_PADRAO
    iniciar(pasta)


if __name__ == "__main__":
    main()
