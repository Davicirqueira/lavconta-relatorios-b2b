"""PDF do relatório geral: todos os clientes com pedido no período (Req 5.6, 6.6).

Mesmo padrão visual do PDF por cliente. Um bloco por cliente (nome, itens a cada
valor e o total dele) e, no fim, o total geral com uma linha por cliente, como a
aba "Resumo" do Excel. Nada é somado aqui: os totais vêm de ``RelatorioGeral``.
"""

import io
from typing import Final
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer

from app.core.datas import hoje_sp
from app.dominio import RelatorioGeral
from app.exports.pdf.estilo import (
    COR_AZUL_900,
    COR_GELO_600,
    formatar_inteiro,
    formatar_moeda,
    paragrafo,
    registrar_fontes,
)
from app.exports.pdf.fechamento import TEXTO_VAZIO
from app.exports.pdf.pagina import CanvasComRodape, cabecalho, criar_documento
from app.exports.pdf.resumo import LARGURAS_CLIENTES, tabela_de_itens, tabela_de_resumo

TITULO_GERAL: Final[str] = "Todos os clientes"
TITULO_TOTAL_GERAL: Final[str] = "Total geral"


def gerar_pdf_geral(relatorio: RelatorioGeral) -> bytes:
    """Gera o PDF do relatório geral já calculado."""
    fonte_normal, fonte_bold = registrar_fontes()
    buffer = io.BytesIO()
    doc = criar_documento(buffer)

    titulo_secao = paragrafo("secao", fonte_bold, 11, COR_AZUL_900, TA_LEFT)
    subtitulo = paragrafo("secao-totais", fonte_normal, 9, COR_GELO_600, TA_LEFT)

    elementos: list[Flowable] = [
        cabecalho(
            titulo_direita=TITULO_GERAL,
            inicio=relatorio.inicio,
            fim=relatorio.fim,
            emissao=hoje_sp(),
            fonte_normal=fonte_normal,
            fonte_bold=fonte_bold,
        ),
        Spacer(1, 16),
    ]

    if relatorio.vazio:
        elementos.append(Paragraph(TEXTO_VAZIO, paragrafo("vazio", fonte_normal, 10, COR_GELO_600)))
        doc.build(elementos, canvasmaker=CanvasComRodape)
        return buffer.getvalue()

    for secao in relatorio.secoes:
        # Bloco pequeno não se parte entre páginas; bloco maior que uma página
        # é partido pelo reportlab, com o cabeçalho da tabela repetido.
        elementos.append(
            KeepTogether(
                [
                    Paragraph(escape(secao.cliente_nome), titulo_secao),
                    Paragraph(
                        f"{formatar_inteiro(secao.total_pecas)} peças · "
                        f"{formatar_moeda(secao.total_valor)}",
                        subtitulo,
                    ),
                    Spacer(1, 6),
                    tabela_de_itens(
                        secao.linhas,
                        secao.total_pecas,
                        secao.total_valor,
                        fonte_normal,
                        fonte_bold,
                    ),
                ]
            )
        )
        elementos.append(Spacer(1, 18))

    elementos.append(
        KeepTogether(
            [
                Paragraph(TITULO_TOTAL_GERAL, titulo_secao),
                Spacer(1, 6),
                tabela_de_resumo(
                    ["Cliente", "Peças", "Total R$"],
                    [
                        [
                            secao.cliente_nome,
                            formatar_inteiro(secao.total_pecas),
                            formatar_moeda(secao.total_valor),
                        ]
                        for secao in relatorio.secoes
                    ],
                    [
                        TITULO_TOTAL_GERAL,
                        formatar_inteiro(relatorio.total_pecas),
                        formatar_moeda(relatorio.total_valor),
                    ],
                    LARGURAS_CLIENTES,
                    fonte_normal,
                    fonte_bold,
                ),
            ]
        )
    )

    doc.build(elementos, canvasmaker=CanvasComRodape)
    return buffer.getvalue()
