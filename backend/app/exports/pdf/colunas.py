"""Larguras das colunas e tipografia da tabela por dia (funções puras).

A medição de texto entra como função (``Medidor``): em produção é ``stringWidth``
do reportlab com a fonte registrada; nos testes pode ser qualquer função
determinística. Assim a regra de largura é testável sem gerar PDF.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from app.exports.pdf.estilo import TAM_MINIMO_TOTAIS

# (texto, negrito, tamanho em pt) -> largura em pt
Medidor = Callable[[str, bool, float], float]

ITEM_MIN: Final[float] = 48.0
ITEM_MAX: Final[float] = 96.0


@dataclass(frozen=True)
class Tipografia:
    """Tamanhos usados na tabela, reduzidos conforme o número de itens."""

    tam_cabecalho: float
    tam_celula: float
    padding_v: float
    padding_h: float

    @property
    def tam_totais(self) -> float:
        return max(self.tam_celula, TAM_MINIMO_TOTAIS)


def tipografia(num_itens: int) -> Tipografia:
    """Degradação de fonte e espaçamento conforme a quantidade de colunas de item."""
    if num_itens <= 6:
        return Tipografia(9.0, 8.5, 4.0, 6.0)
    if num_itens <= 10:
        return Tipografia(8.0, 7.5, 3.0, 4.0)
    if num_itens <= 15:
        return Tipografia(7.0, 6.5, 2.0, 3.0)
    return Tipografia(6.0, 5.5, 1.5, 2.0)


def _maior(
    textos_titulo: Sequence[str],
    valores: Sequence[str],
    total: str,
    medir: Medidor,
    tipo: Tipografia,
) -> float:
    candidatos = [
        *(medir(t, True, tipo.tam_cabecalho) for t in textos_titulo),
        medir(total, True, tipo.tam_totais),
        *(medir(v, False, tipo.tam_celula) for v in valores),
    ]
    return max(candidatos) + 2 * tipo.padding_h


def larguras_por_dia(
    titulos: Sequence[str],
    linhas: Sequence[Sequence[str]],
    totais: Sequence[str],
    *,
    medir: Medidor,
    tipo: Tipografia,
    largura_util: float,
) -> list[float]:
    """Larguras na ordem Data, Comanda, itens..., Total de peças, Total R$.

    - Largura ideal: o maior texto da coluna (título inteiro numa linha, valores e
      total). Para itens, limitada a 48–96 pt; título maior que isso quebra linha
      (a célula de título é um parágrafo).
    - A tabela **não estica** para ocupar a página: sobra espaço à direita.
    - Se não couber (muitos itens), todas as colunas encolhem por igual em direção
      à largura mínima, que é a maior **palavra** do título (ou o maior valor):
      o título quebra entre palavras, nunca no meio de uma.
    - Só se nem a mínima couber, as colunas de item encolhem além dela.
    """
    n = len(titulos)
    indices_item = range(2, n - 2)
    ideal: list[float] = []
    minimo: list[float] = []
    for i in range(n):
        valores = [linha[i] for linha in linhas]
        ideal.append(_maior([titulos[i]], valores, totais[i], medir, tipo))
        minimo.append(_maior(titulos[i].split() or [""], valores, totais[i], medir, tipo))
    for i in indices_item:
        ideal[i] = min(ITEM_MAX, max(ITEM_MIN, ideal[i]))
        minimo[i] = min(minimo[i], ideal[i])

    excesso = sum(ideal) - largura_util
    if excesso <= 0:
        return ideal

    folga = sum(ideal) - sum(minimo)
    if folga >= excesso:
        fracao = excesso / folga
        return [w - fracao * (w - m) for w, m in zip(ideal, minimo, strict=True)]

    # nem a largura mínima cabe: encolhe só os itens, proporcionalmente
    colunas = list(minimo)
    restante = sum(colunas) - largura_util
    soma_itens = sum(colunas[i] for i in indices_item)
    if soma_itens > 0:
        fator = max(0.0, (soma_itens - restante) / soma_itens)
        for i in indices_item:
            colunas[i] *= fator
    return colunas
