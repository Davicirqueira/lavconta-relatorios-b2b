"""PDF do Relatório de Fechamento de um cliente.

Consome a estrutura já calculada de ``Relatorio`` sem recalcular nenhum total
(Req 6.7): a tabela por dia usa ``linhas`` e ``totais``; o resumo por item usa
``resumo_por_item``.
"""

import io
from typing import Final
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer, Table, TableStyle

from app.core.datas import hoje_sp
from app.dominio import Relatorio
from app.exports.pdf import colunas
from app.exports.pdf.estilo import (
    COR_AZUL_900,
    COR_GELO_600,
    COR_GELO_900,
    estilos_de_tabela,
    formatar_inteiro,
    formatar_moeda,
    paragrafo,
    registrar_fontes,
)
from app.exports.pdf.pagina import (
    LARGURA_UTIL,
    CanvasComRodape,
    cabecalho,
    criar_documento,
    medidor,
)
from app.exports.pdf.resumo import tabela_de_itens

TEXTO_VAZIO: Final[str] = "Nenhum pedido no período escolhido."
TITULO_RESUMO: Final[str] = "Resumo por item"


def _celulas(relatorio: Relatorio) -> tuple[list[str], list[list[str]], list[str]]:
    """Títulos, uma linha por pedido e a linha de totais, já formatados."""
    titulos = ["Data", "Comanda", *(c.nome for c in relatorio.colunas_itens)]
    titulos += ["Total de peças", "Total R$"]

    linhas: list[list[str]] = []
    for linha in relatorio.linhas:
        celulas = [linha.data.strftime("%d/%m/%Y"), linha.comanda or ""]
        for col in relatorio.colunas_itens:
            qtd = linha.quantidades.get(col.item_id)
            celulas.append(formatar_inteiro(qtd) if qtd is not None else "")
        celulas += [formatar_inteiro(linha.total_pecas), formatar_moeda(linha.total_valor)]
        linhas.append(celulas)

    totais = ["Totais", ""]
    for col in relatorio.colunas_itens:
        totais.append(formatar_inteiro(relatorio.totais.por_item.get(col.item_id, 0)))
    totais += [
        formatar_inteiro(relatorio.totais.total_pecas),
        formatar_moeda(relatorio.totais.total_valor),
    ]
    return titulos, linhas, totais


def _tabela_por_dia(relatorio: Relatorio, fonte_normal: str, fonte_bold: str) -> Table:
    """Uma linha por pedido; cabeçalho repetido em cada página (Req 6.5)."""
    tipo = colunas.tipografia(len(relatorio.colunas_itens))
    titulos, linhas, totais = _celulas(relatorio)
    larguras = colunas.larguras_por_dia(
        titulos,
        linhas,
        totais,
        medir=medidor(fonte_normal, fonte_bold),
        tipo=tipo,
        largura_util=LARGURA_UTIL,
    )

    # Títulos como parágrafo: nome de item longo quebra linha em vez de vazar.
    cab_esq = paragrafo("dia-cab-esq", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_LEFT)
    cab_dir = paragrafo("dia-cab-dir", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_RIGHT)
    cabecalho_tabela = [
        Paragraph(escape(t), cab_esq if i < 2 else cab_dir) for i, t in enumerate(titulos)
    ]

    dados = [cabecalho_tabela, *linhas, totais]
    estilos = estilos_de_tabela(
        ultima=len(dados) - 1,
        fonte_normal=fonte_normal,
        fonte_bold=fonte_bold,
        tam_cabecalho=tipo.tam_cabecalho,
        tam_celula=tipo.tam_celula,
        padding_v=tipo.padding_v,
        padding_h=tipo.padding_h,
    )
    # Texto (Data, Comanda) à esquerda; números à direita (Req 6.3)
    estilos += [("ALIGN", (0, 0), (1, -1), "LEFT"), ("ALIGN", (2, 0), (-1, -1), "RIGHT")]

    tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle(estilos))
    return tabela


def gerar_pdf(relatorio: Relatorio) -> bytes:
    """Gera o PDF do relatório de fechamento já calculado.

    Args:
        relatorio: objeto de domínio contendo linhas, colunas e totais agregados.

    Returns:
        Bytes correspondentes ao arquivo PDF gerado.
    """
    fonte_normal, fonte_bold = registrar_fontes()
    buffer = io.BytesIO()
    doc = criar_documento(buffer)

    elementos: list[Flowable] = [
        cabecalho(
            titulo_direita=f"Cliente: {relatorio.cliente_nome}",
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
    else:
        elementos.append(_tabela_por_dia(relatorio, fonte_normal, fonte_bold))
        elementos.append(Spacer(1, 20))
        elementos.append(
            KeepTogether(
                [
                    Paragraph(TITULO_RESUMO, paragrafo("titulo", fonte_bold, 11, COR_AZUL_900)),
                    Spacer(1, 6),
                    tabela_de_itens(
                        relatorio.resumo_por_item,
                        relatorio.totais.total_pecas,
                        relatorio.totais.total_valor,
                        fonte_normal,
                        fonte_bold,
                    ),
                ]
            )
        )

    doc.build(elementos, canvasmaker=CanvasComRodape)
    return buffer.getvalue()
