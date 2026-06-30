"""Orquestrador: junta parser, validador, grafo, executor e estado.

É o ponto único de acesso para a interface. **Não importa tkinter** — toda a
lógica funciona sem UI e é testável isoladamente.

Fluxo de :meth:`Migrador.carregar`:
    carregar migrations → validar → construir grafo → ordenação topológica.

Os "estados" do documento vão de ``0`` (vazio) a ``total`` (todas aplicadas).
O estado ``N`` corresponde a aplicar os blocos ``up`` das primeiras ``N``
migrations da ordem topológica, partindo do documento vazio. Esse modelo é a
fonte da verdade tanto para o slider da interface quanto para a persistência.
"""

import os

from core import estado as estado_mod
from core import parser as parser_mod
from core import validador as validador_mod
from core.executor import aplicar_bloco
from core.grafo import ErroCiclo


# Estados possíveis de uma migration, do ponto de vista da UI.
APLICADA = "aplicada"
PENDENTE = "pendente"
EM_CICLO = "em_ciclo"


class Migrador:
    """Coordena o ciclo de vida das migrations de uma pasta.

    Após :meth:`carregar`, se tudo estiver válido, ``self.erro`` é ``None`` e
    ``self.ordem`` traz a ordem topológica. Se houver erro de validação,
    ``self.erro`` recebe a exceção e ``self.nos_problematicos`` lista os ids
    envolvidos (para a UI destacar), sem derrubar a aplicação.
    """

    def __init__(self, pasta):
        self.pasta = pasta
        self.migrations = {}
        self.grafo = None
        self.ordem = []
        self.erro = None
        self.nos_problematicos = []
        self.estado = estado_mod.carregar_estado(pasta)

    # ------------------------------------------------------------------ carga
    def carregar(self):
        """Lê as migrations da pasta, valida e calcula a ordem topológica.

        Não levanta erro de validação: registra-o em ``self.erro`` e retorna.
        Erros de parsing/leitura, por serem mais graves, também são capturados
        para manter a UI estável.
        """
        self.erro = None
        self.nos_problematicos = []
        self.grafo = None
        self.ordem = []
        try:
            self.migrations = parser_mod.carregar_migrations(self.pasta)
            # Constrói o grafo já aqui, antes de validar, para que a interface
            # consiga desenhar os nós mesmo quando há ciclo (e pintá-los de
            # vermelho). A validação abaixo é quem decide se está tudo certo.
            self.grafo = validador_mod.construir_grafo(self.migrations)
            validador_mod.validar(self.migrations)
            self.ordem = self.grafo.ordenacao_topologica()
        except validador_mod.ErroDependenciaInexistente as e:
            self.erro = e
            self.nos_problematicos = sorted(e.faltantes.keys())
        except ErroCiclo as e:
            self.erro = e
            self.nos_problematicos = list(e.vertices)
        except (parser_mod.ErroParser, FileNotFoundError) as e:
            self.erro = e

        # Remove da lista de aplicadas qualquer id que não exista mais.
        if not self.erro:
            self.estado["aplicadas"] = [
                m for m in self.estado["aplicadas"] if m in self.migrations
            ]
        return self.erro is None

    @property
    def valido(self):
        """``True`` se a última carga não encontrou erros."""
        return self.erro is None

    @property
    def total(self):
        """Número total de migrations."""
        return len(self.ordem)

    @property
    def documento_nome(self):
        """Nome do arquivo de documento configurado no estado."""
        return self.estado.get("documento", estado_mod.DOCUMENTO_PADRAO)

    # ----------------------------------------------------------- estado/posição
    @property
    def posicao(self):
        """Estado atual ``N`` = quantas migrations estão aplicadas."""
        return len(self.estado["aplicadas"])

    def documento_no_estado(self, n):
        """Conteúdo do documento aplicando as primeiras ``n`` migrations.

        :param n: inteiro de ``0`` (vazio) a :attr:`total`.
        :returns: conteúdo (``str``) ou ``None`` se o documento não existir
            naquele estado.
        :raises IndexError: se ``n`` estiver fora de ``0..total``.
        """
        if n < 0 or n > self.total:
            raise IndexError("Estado fora do intervalo 0..%d: %d" % (self.total, n))
        conteudo = None
        for mig_id in self.ordem[:n]:
            conteudo = aplicar_bloco(conteudo, self.migrations[mig_id].up)
        return conteudo

    def documento_atual(self):
        """Conteúdo do documento na posição atual."""
        return self.documento_no_estado(self.posicao)

    def estado_de(self, mig_id):
        """Estado de uma migration para colorir o grafo na UI.

        :returns: :data:`APLICADA`, :data:`PENDENTE` ou :data:`EM_CICLO`.
        """
        if mig_id in self.nos_problematicos:
            return EM_CICLO
        if mig_id in self.estado["aplicadas"]:
            return APLICADA
        return PENDENTE

    def status(self):
        """Resumo textual: ``(nome_documento, aplicadas, total)``."""
        return self.documento_nome, self.posicao, self.total

    # -------------------------------------------------------------- transições
    def ir_para_estado(self, n):
        """Leva o documento ao estado ``n`` (aplica ou reverte conforme preciso).

        Atualiza a lista de aplicadas (sempre o prefixo da ordem topológica),
        grava o documento e persiste o estado.

        :raises RuntimeError: se o conjunto estiver inválido (erro pendente).
        :raises IndexError: se ``n`` estiver fora de ``0..total``.
        """
        if not self.valido:
            raise RuntimeError(
                "Não é possível migrar: %s" % (self.erro or "conjunto inválido")
            )
        if n < 0 or n > self.total:
            raise IndexError("Estado fora do intervalo 0..%d: %d" % (self.total, n))

        self.estado["aplicadas"] = list(self.ordem[:n])
        self._gravar_documento(self.documento_no_estado(n))
        estado_mod.salvar_estado(self.pasta, self.estado)

    def migrar(self):
        """Aplica todas as migrations pendentes (vai ao estado :attr:`total`)."""
        self.ir_para_estado(self.total)

    def reverter(self):
        """Reverte um passo (executa o ``down`` da última migration aplicada)."""
        if self.posicao > 0:
            self.ir_para_estado(self.posicao - 1)

    def resetar(self):
        """Volta ao estado 0 (documento vazio/inexistente)."""
        self.ir_para_estado(0)

    # -------------------------------------------------------------------- diff
    def previa_diff(self, mig_id):
        """Conteúdo antes e depois do ``up`` de ``mig_id``, para o painel de diff.

        Calcula a partir da ordem topológica: aplica tudo até imediatamente
        antes de ``mig_id`` e então o ``up`` dele.

        :returns: tupla ``(antes, depois)`` de strings (ou ``None``).
        """
        if mig_id not in self.ordem:
            return None, None
        idx = self.ordem.index(mig_id)
        antes = self.documento_no_estado(idx)
        depois = aplicar_bloco(antes, self.migrations[mig_id].up)
        return antes, depois

    # ----------------------------------------------------------------- arquivo
    def caminho_documento(self):
        """Caminho absoluto do arquivo de documento (dentro da pasta)."""
        return os.path.join(self.pasta, self.documento_nome)

    def _gravar_documento(self, conteudo):
        """Escreve (ou remove) o arquivo de documento conforme ``conteudo``."""
        caminho = self.caminho_documento()
        if conteudo is None:
            if os.path.isfile(caminho):
                os.remove(caminho)
            return
        with open(caminho, "w", encoding="utf-8") as fp:
            fp.write(conteudo)
