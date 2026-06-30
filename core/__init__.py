"""Núcleo (core) do sistema de migrations.

Toda a lógica vive aqui e é independente da interface gráfica: nenhum módulo
deste pacote importa ``tkinter``. A interface (``ui/``) apenas consome o que
este pacote expõe — principalmente a classe :class:`core.migrador.Migrador`.
"""
