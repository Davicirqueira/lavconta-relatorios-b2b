"""Tabelas de resumo usadas nos dois PDFs.

Mesmas colunas da tela e do Excel: Item · Por peça · Peças · Subtotal. A primeira
coluna é texto (à esquerda, quebra linha se for longa); as demais são números (à
direita). Os valores chegam prontos do domínio; aqui só se formata.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Final
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import Paragraph, Table, TableStyle

from app.dominio import LinhaResumoItem
from app.exports.pdf.estilo import (
    COR_AZUL_900,
    COR_GELO_900,
    estilos_de_tabela,
    formatar_inteiro,
    formatar_moeda,
    paragrafo,
)

TAM_CABECALHO: Final[float] = 9.0
TAM_CELULA: Final[float] = 8.5
PADDING_V: Final[float] = 4.0

# Larguras fixas: no PDF geral as colunas ficam alinhadas entre os clientes.
LARGURAS_ITENS: Final[list[float]] = [220.0, 80.0, 70.0, 100.0]
LARGURAS_CLIENTES: Final[list[float]] = [300.0, 70.0, 100.0]


def tabela_de_resumo(
    titulos: Sequence[str],
    linhas: Sequence[Sequence[str]],
    total: Sequence[str],
    larguras: Sequence[float],
    fonte_normal: str,
    fonte_bold: str,
) -> Table:
    """Cabeçalho, linhas e linha de total, com a moldura comum das tabelas."""
    texto = paragrafo("resumo-texto", fonte_normal, TAM_CELULA, COR_GELO_900, TA_LEFT)
    texto_total = paragrafo("resumo-total", fonte_bold, TAM_CELULA, COR_AZUL_900, TA_LEFT)
    cab_esq = paragrafo("resumo-cab-esq", fonte_bold, TAM_CABECALHO, COR_GELO_900, TA_LEFT)
    cab_dir = paragrafo("resumo-cab-dir", fonte_bold, TAM_CABECALHO, COR_GELO_900, TA_RIGHT)

    dados: list[list] = [
        [Paragraph(escape(t), cab_esq if i == 0 else cab_dir) for i, t in enumerate(titulos)]
    ]
    for linha in linhas:
        dados.append([Paragraph(escape(linha[0]), texto), *linha[1:]])
    dados.append([Paragraph(escape(total[0]), texto_total), *total[1:]])

    ultima = len(dados) - 1
    estilos = estilos_de_tabela(
        ultima=ultima,
        fonte_normal=fonte_normal,
        fonte_bold=fonte_bold,
        tam_cabecalho=TAM_CABECALHO,
        tam_celula=TAM_CELULA,
        padding_v=PADDING_V,
    )
    estilos += [("ALIGN", (0, 0), (0, -1), "LEFT"), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]

    tabela = Table(dados, colWidths=list(larguras), repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle(estilos))
    return tabela


def tabela_de_itens(
    linhas: Sequence[LinhaResumoItem],
    total_pecas: int,
    total_valor: Decimal,
    fonte_normal: str,
    fonte_bold: str,
) -> Table:
    """Item a cada valor por peça, com o total (o total vem pronto, não é somado aqui)."""
    return tabela_de_resumo(
        ["Item", "Por peça", "Peças", "Subtotal"],
        [
            [
                linha.item_nome,
                formatar_moeda(linha.valor_unitario),
                formatar_inteiro(linha.quantidade),
                formatar_moeda(linha.subtotal),
            ]
            for linha in linhas
        ],
        ["Total", "", formatar_inteiro(total_pecas), formatar_moeda(total_valor)],
        LARGURAS_ITENS,
        fonte_normal,
        fonte_bold,
    )
