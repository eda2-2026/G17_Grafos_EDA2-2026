"""Interface Tkinter do sistema de migrations.

Consome exclusivamente :class:`core.migrador.Migrador`. Quatro regiões:

1. **Barra superior** — nome do documento, status e botões.
2. **Painel do grafo** (``Canvas``) — DAG em layout por níveis, colorido por
   estado, clicável.
3. **Painel do documento/diff** (``Text``) — conteúdo atual ou prévia do ``up``.
4. **Linha do tempo** (``Scale``) — desliza pelos estados 0..total.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.migrador import Migrador, APLICADA, PENDENTE, EM_CICLO

# Paleta de cores por estado da migration.
COR = {
    APLICADA: ("#cdeccd", "#2e7d32"),   # (preenchimento, borda) verde
    PENDENTE: ("#e8e8e8", "#9e9e9e"),   # cinza
    EM_CICLO: ("#f3c5c5", "#c62828"),   # vermelho
}
COR_SELECIONADO = "#1565c0"             # borda azul do nó selecionado

# Dimensões dos nós no canvas.
NO_LARGURA = 150
NO_ALTURA = 40
NIVEL_ALTURA = 100
MARGEM = 30


class App(tk.Tk):
    """Janela principal."""

    def __init__(self, pasta_migrations):
        super().__init__()
        self.title("Migrador de documentos — grafo de dependências")
        self.geometry("1000x680")

        self.migrador = Migrador(pasta_migrations)
        self.selecionado = None          # id da migration selecionada (diff)
        self._posicoes = {}              # id -> (x, y) do centro do nó no canvas
        self._suprimir_slider = False    # evita recursão no callback do Scale

        self._montar_barra_superior()
        self._montar_corpo()
        self._montar_linha_do_tempo()
        self._montar_barra_status()

        self.recarregar()

    # ----------------------------------------------------------- construção UI
    def _montar_barra_superior(self):
        barra = ttk.Frame(self, padding=(10, 8))
        barra.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(barra, text="Abrir pasta…", command=self.acao_abrir_pasta).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        self.lbl_titulo = ttk.Label(barra, font=("TkDefaultFont", 11, "bold"))
        self.lbl_titulo.pack(side=tk.LEFT)

        ttk.Button(barra, text="Resetar", command=self.acao_resetar).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(barra, text="Reverter", command=self.acao_reverter).pack(
            side=tk.RIGHT, padx=2
        )
        self.btn_migrar = ttk.Button(barra, text="Migrar", command=self.acao_migrar)
        self.btn_migrar.pack(side=tk.RIGHT, padx=2)

    def _montar_corpo(self):
        corpo = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        corpo.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=6)

        # Painel do grafo (esquerda).
        moldura_grafo = ttk.Labelframe(corpo, text="Grafo de dependências")
        self.canvas = tk.Canvas(moldura_grafo, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._clique_canvas)
        corpo.add(moldura_grafo, weight=3)

        # Painel do documento/diff (direita).
        self.moldura_doc = ttk.Labelframe(corpo, text="Documento")
        self.texto = tk.Text(
            self.moldura_doc, wrap=tk.NONE, font=("TkFixedFont", 10),
            state=tk.DISABLED,
        )
        self.texto.pack(fill=tk.BOTH, expand=True)
        self.texto.tag_configure("entra", background="#cdeccd")
        self.texto.tag_configure("sai", background="#f3c5c5", overstrike=True)
        self.texto.tag_configure("cabecalho", font=("TkDefaultFont", 9, "italic"))
        corpo.add(self.moldura_doc, weight=2)

    def _montar_linha_do_tempo(self):
        moldura = ttk.Labelframe(self, text="Linha do tempo", padding=(10, 4))
        moldura.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 6))

        self.scale = tk.Scale(
            moldura, from_=0, to=0, orient=tk.HORIZONTAL,
            command=self._slider_mudou, showvalue=False,
        )
        self.scale.pack(fill=tk.X)
        self.lbl_passos = ttk.Label(moldura, font=("TkDefaultFont", 8))
        self.lbl_passos.pack(fill=tk.X)

    def _montar_barra_status(self):
        self.lbl_status = ttk.Label(
            self, relief=tk.SUNKEN, anchor=tk.W, padding=(8, 3)
        )
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------- atualização
    def recarregar(self):
        """Recarrega as migrations e redesenha tudo."""
        self.migrador.carregar()
        total = self.migrador.total

        nome_pasta = os.path.basename(os.path.normpath(self.migrador.pasta))
        self.title("Migrador de documentos — pasta: %s" % nome_pasta)

        self._suprimir_slider = True
        self.scale.configure(to=max(total, 0))
        if self.migrador.valido:
            self.scale.set(self.migrador.posicao)
        self._suprimir_slider = False

        estado_slider = tk.NORMAL if self.migrador.valido else tk.DISABLED
        self.scale.configure(state=estado_slider)
        self.btn_migrar.configure(
            state=tk.NORMAL if self.migrador.valido else tk.DISABLED
        )

        self._atualizar_rotulos_passos()
        self._desenhar_grafo()
        self._mostrar_documento_atual()
        self._atualizar_status()

    def _atualizar_status(self):
        nome, aplicadas, total = self.migrador.status()
        self.lbl_titulo.configure(
            text="%s — %d de %d aplicadas" % (nome, aplicadas, total)
        )
        if self.migrador.valido:
            self.lbl_status.configure(
                text="Pronto. Arraste a linha do tempo ou clique num nó para ver a prévia.",
                foreground="black",
            )
        else:
            self.lbl_status.configure(
                text="Erro: %s" % self.migrador.erro, foreground="#c62828"
            )

    def _atualizar_rotulos_passos(self):
        rotulos = ["vazio"]
        for mig_id in self.migrador.ordem:
            # Rótulo curto: prefixo numérico se houver, senão o id inteiro.
            prefixo = mig_id.split("_", 1)[0]
            rotulos.append(prefixo)
        self.lbl_passos.configure(text="  →  ".join(rotulos))

    # ------------------------------------------------------------- grafo/canvas
    def _calcular_niveis(self):
        """Nível de cada nó = maior caminho desde uma raiz (grau de entrada 0).

        Processa na ordem topológica: cada nó empurra ``nivel+1`` para seus
        dependentes. Layout em camadas implementado à mão.
        """
        niveis = {v: 0 for v in self.migrador.grafo.vertices}
        for v in self.migrador.ordem:
            for w in self.migrador.grafo.adjacencia[v]:
                if niveis[v] + 1 > niveis[w]:
                    niveis[w] = niveis[v] + 1
        return niveis

    def _desenhar_grafo(self):
        self.canvas.delete("all")
        self._posicoes = {}

        if self.migrador.grafo is None:
            self.canvas.create_text(
                20, 20, anchor=tk.NW, fill="#c62828",
                text="Não foi possível montar o grafo (ver erro abaixo).",
            )
            return

        vertices = sorted(self.migrador.grafo.vertices)
        if self.migrador.valido:
            niveis = self._calcular_niveis()
        else:
            # Sem ordem topológica (ciclo): distribui em uma faixa só.
            niveis = {v: 0 for v in vertices}

        # Agrupa por nível e calcula posições.
        por_nivel = {}
        for v in vertices:
            por_nivel.setdefault(niveis[v], []).append(v)

        for nivel, nodes in por_nivel.items():
            nodes.sort()
            for col, v in enumerate(nodes):
                x = MARGEM + NO_LARGURA / 2 + col * (NO_LARGURA + 40)
                y = MARGEM + NO_ALTURA / 2 + nivel * NIVEL_ALTURA
                self._posicoes[v] = (x, y)

        # Arestas primeiro (ficam atrás dos nós).
        for origem in vertices:
            for destino in self.migrador.grafo.adjacencia[origem]:
                if origem in self._posicoes and destino in self._posicoes:
                    self._desenhar_aresta(self._posicoes[origem], self._posicoes[destino])

        # Nós por cima.
        for v in vertices:
            self._desenhar_no(v)

        # Ajusta a área rolável do canvas ao conteúdo.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _desenhar_aresta(self, p_origem, p_destino):
        x1, y1 = p_origem
        x2, y2 = p_destino
        # Sai da base do nó de origem e chega no topo do de destino.
        self.canvas.create_line(
            x1, y1 + NO_ALTURA / 2, x2, y2 - NO_ALTURA / 2,
            arrow=tk.LAST, fill="#777", width=2, smooth=True,
        )

    def _desenhar_no(self, v):
        x, y = self._posicoes[v]
        preench, borda = COR[self.migrador.estado_de(v)]
        largura_borda = 3 if v == self.selecionado else 1
        cor_borda = COR_SELECIONADO if v == self.selecionado else borda

        self.canvas.create_rectangle(
            x - NO_LARGURA / 2, y - NO_ALTURA / 2,
            x + NO_LARGURA / 2, y + NO_ALTURA / 2,
            fill=preench, outline=cor_borda, width=largura_borda,
            tags=("no", "no:%s" % v),
        )
        self.canvas.create_text(
            x, y, text=v, width=NO_LARGURA - 12, font=("TkDefaultFont", 8),
            tags=("no", "no:%s" % v),
        )

    def _clique_canvas(self, evento):
        x = self.canvas.canvasx(evento.x)
        y = self.canvas.canvasy(evento.y)
        for v, (cx, cy) in self._posicoes.items():
            if (abs(x - cx) <= NO_LARGURA / 2) and (abs(y - cy) <= NO_ALTURA / 2):
                self.selecionado = v
                self._desenhar_grafo()
                self._mostrar_diff(v)
                return

    # --------------------------------------------------------- painel do texto
    def _escrever_texto(self, render):
        """Helper: habilita o Text, limpa, chama ``render`` e desabilita."""
        self.texto.configure(state=tk.NORMAL)
        self.texto.delete("1.0", tk.END)
        render()
        self.texto.configure(state=tk.DISABLED)

    def _mostrar_documento_atual(self):
        self.moldura_doc.configure(text="Documento")
        conteudo = self.migrador.documento_atual() if self.migrador.valido else None

        def render():
            if conteudo is None:
                self.texto.insert(tk.END, "(documento ainda não criado)", ("cabecalho",))
            else:
                self.texto.insert(tk.END, conteudo)

        self._escrever_texto(render)

    def _mostrar_diff(self, mig_id):
        """Mostra a prévia (diff) do ``up`` da migration selecionada."""
        if not self.migrador.valido:
            return
        antes, depois = self.migrador.previa_diff(mig_id)
        self.moldura_doc.configure(text="Prévia — %s" % mig_id)

        linhas_antes = (antes or "").split("\n")
        linhas_depois = (depois or "").split("\n")
        estado = self.migrador.estado_de(mig_id)
        nota = "aplicada" if estado == APLICADA else "pendente"

        def render():
            self.texto.insert(
                tk.END, "Efeito do bloco [up] desta migration (%s):\n\n" % nota,
                ("cabecalho",),
            )
            for linha, tag in self._linhas_diff(linhas_antes, linhas_depois):
                self.texto.insert(tk.END, linha + "\n", tag)

        self._escrever_texto(render)

    @staticmethod
    def _linhas_diff(antes, depois):
        """Diff linha-a-linha simples (LCS) → lista de ``(linha, tag)``.

        ``tag`` é ``"sai"`` (vermelho), ``"entra"`` (verde) ou ``()`` (igual).
        """
        n, m = len(antes), len(depois)
        # Tabela de LCS para alinhar as linhas inalteradas.
        lcs = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                if antes[i] == depois[j]:
                    lcs[i][j] = lcs[i + 1][j + 1] + 1
                else:
                    lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])

        resultado = []
        i = j = 0
        while i < n and j < m:
            if antes[i] == depois[j]:
                resultado.append((antes[i], ()))
                i += 1
                j += 1
            elif lcs[i + 1][j] >= lcs[i][j + 1]:
                resultado.append((antes[i], ("sai",)))
                i += 1
            else:
                resultado.append((depois[j], ("entra",)))
                j += 1
        while i < n:
            resultado.append((antes[i], ("sai",)))
            i += 1
        while j < m:
            resultado.append((depois[j], ("entra",)))
            j += 1
        return resultado

    # ------------------------------------------------------------- linha tempo
    def _slider_mudou(self, valor):
        if self._suprimir_slider or not self.migrador.valido:
            return
        alvo = int(float(valor))
        if alvo == self.migrador.posicao:
            return
        try:
            self.migrador.ir_para_estado(alvo)
        except Exception as e:  # erro de execução de comando
            messagebox.showerror("Erro ao migrar", str(e))
            return
        self.selecionado = None
        self._desenhar_grafo()
        self._mostrar_documento_atual()
        self._atualizar_status()

    # ----------------------------------------------------------------- ações
    def _executar(self, operacao, descricao):
        if not self.migrador.valido:
            messagebox.showwarning(
                "Operação bloqueada",
                "Há um erro no conjunto de migrations:\n\n%s" % self.migrador.erro,
            )
            return
        try:
            operacao()
        except Exception as e:
            messagebox.showerror("Erro ao %s" % descricao, str(e))
            return
        self.selecionado = None
        self._suprimir_slider = True
        self.scale.set(self.migrador.posicao)
        self._suprimir_slider = False
        self._desenhar_grafo()
        self._mostrar_documento_atual()
        self._atualizar_status()

    def acao_abrir_pasta(self):
        """Abre um seletor de diretório e recarrega o grafo da pasta escolhida."""
        pasta = filedialog.askdirectory(
            title="Escolha a pasta de migrations",
            initialdir=self.migrador.pasta,
            mustexist=True,
        )
        if not pasta:
            return  # usuário cancelou
        self.migrador = Migrador(pasta)
        self.selecionado = None
        self.recarregar()

    def acao_migrar(self):
        self._executar(self.migrador.migrar, "migrar")

    def acao_reverter(self):
        self._executar(self.migrador.reverter, "reverter")

    def acao_resetar(self):
        self._executar(self.migrador.resetar, "resetar")


def iniciar(pasta_migrations):
    """Cria e executa a janela principal apontando para ``pasta_migrations``."""
    app = App(pasta_migrations)
    app.mainloop()
