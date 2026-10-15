"""PDF do relatório geral: todos os clientes com pedido no período (Req 5.6, 6.6).

Mesmo padrão visual do PDF por cliente. Fase 6 (v1.1): inclui tabela de controle
de demanda no início e, depois, um bloco por cliente (nome e o total dele)
e, no fim, o total geral com uma linha por cliente, como a aba "Resumo" do Excel.
Nada é somado aqui: os totais vêm de ``RelatorioGeral``.
"""

import io
from typing import Final
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer, Table, TableStyle

from app.core.datas import hoje_sp
from app.dominio import RelatorioGeral
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
from app.exports.pdf.fechamento import TEXTO_VAZIO
from app.exports.pdf.pagina import (
    LARGURA_UTIL,
    CanvasComRodape,
    cabecalho,
    criar_documento,
    medidor,
)
from app.exports.pdf.resumo import LARGURAS_CLIENTES, tabela_de_resumo

TITULO_GERAL: Final[str] = "Todos os clientes"
TITULO_DEMANDA: Final[str] = "Controle de demanda"
TITULO_TOTAL_GERAL: Final[str] = "Total geral"


def _tabela_demanda_diaria(relatorio: RelatorioGeral, fonte_normal: str, fonte_bold: str) -> Table | list[Flowable]:
    """Tabela de controle de demanda (v1.1 fase 6).

    Estrutura igual à do relatório individual: data e colunas de itens dinâmicas,
    sem comanda. Usa a mesma lógica de larguras e tipografia do fechamento individual.
    Se houver muitos itens (>8), divide em blocos.
    """
    ITENS_POR_BLOCO = 8
    num_itens = len(relatorio.colunas_itens)
    
    # Se couber em uma tabela, usa a lógica original
    if num_itens <= ITENS_POR_BLOCO:
        return _tabela_demanda_simples(relatorio, fonte_normal, fonte_bold)
    
    # Caso contrário, divide em blocos
    return _tabelas_demanda_em_blocos(relatorio, fonte_normal, fonte_bold, ITENS_POR_BLOCO)


def _tabela_demanda_simples(relatorio: RelatorioGeral, fonte_normal: str, fonte_bold: str) -> Table:
    """Tabela de controle de demanda (v1.1 fase 6).

    Estrutura igual à do relatório individual: data e colunas de itens dinâmicas,
    sem comanda. Usa a mesma lógica de larguras e tipografia do fechamento individual.
    """
    tipo = colunas.tipografia(len(relatorio.colunas_itens))

    # Montar títulos, linhas e totais
    titulos = ["Data", *(c.nome for c in relatorio.colunas_itens), "Total de peças", "Total R$"]

    linhas: list[list[str]] = []
    for linha in relatorio.demanda_diaria:
        celulas = [linha.data.strftime("%d/%m/%Y")]
        for col in relatorio.colunas_itens:
            qtd = linha.quantidades.get(col.item_id)
            celulas.append(formatar_inteiro(qtd) if qtd is not None else "")
        celulas += [formatar_inteiro(linha.total_pecas), formatar_moeda(linha.total_valor)]
        linhas.append(celulas)

    # Totais por item
    totais_por_item: dict = {}
    for linha in relatorio.demanda_diaria:
        for item_id, qtd in linha.quantidades.items():
            totais_por_item[item_id] = totais_por_item.get(item_id, 0) + qtd

    totais = ["Totais"]
    for col in relatorio.colunas_itens:
        totais.append(formatar_inteiro(totais_por_item.get(col.item_id, 0)))
    totais += [
        formatar_inteiro(relatorio.total_pecas),
        formatar_moeda(relatorio.total_valor),
    ]

    # Calcular larguras (sem coluna de comanda, passa lista com um item vazio)
    larguras = colunas.larguras_por_dia(
        titulos,
        linhas,
        totais,
        medir=medidor(fonte_normal, fonte_bold),
        tipo=tipo,
        largura_util=LARGURA_UTIL,
    )

    # Títulos como parágrafo
    cab_esq = paragrafo("dia-cab-esq", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_LEFT)
    cab_dir = paragrafo("dia-cab-dir", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_RIGHT)
    
    cabecalho_tabela = [
        Paragraph(escape(t), cab_esq if i == 0 else cab_dir) for i, t in enumerate(titulos)
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
    # Data à esquerda; números à direita
    estilos += [("ALIGN", (0, 0), (0, -1), "LEFT"), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]

    tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle(estilos))
    return tabela


def _tabelas_demanda_em_blocos(
    relatorio: RelatorioGeral, fonte_normal: str, fonte_bold: str, itens_por_bloco: int
) -> list[Flowable]:
    """Divide os itens em blocos para a tabela de demanda diária."""
    blocos: list[Flowable] = []
    num_itens = len(relatorio.colunas_itens)
    
    # Calcular totais por item uma vez
    totais_por_item: dict = {}
    for linha in relatorio.demanda_diaria:
        for item_id, qtd in linha.quantidades.items():
            totais_por_item[item_id] = totais_por_item.get(item_id, 0) + qtd
    
    for inicio in range(0, num_itens, itens_por_bloco):
        fim = min(inicio + itens_por_bloco, num_itens)
        itens_bloco = relatorio.colunas_itens[inicio:fim]
        
        # Construir títulos do bloco
        titulos = ["Data"]
        titulos.extend(col.nome for col in itens_bloco)
        titulos.extend(["Total de peças", "Total R$"])
        
        # Construir linhas do bloco
        linhas_bloco: list[list[str]] = []
        for linha in relatorio.demanda_diaria:
            celulas = [linha.data.strftime("%d/%m/%Y")]
            for col in itens_bloco:
                qtd = linha.quantidades.get(col.item_id)
                celulas.append(formatar_inteiro(qtd) if qtd is not None else "")
            celulas.extend([formatar_inteiro(linha.total_pecas), formatar_moeda(linha.total_valor)])
            linhas_bloco.append(celulas)
        
        # Construir totais do bloco
        totais_bloco = ["Totais"]
        for col in itens_bloco:
            totais_bloco.append(formatar_inteiro(totais_por_item.get(col.item_id, 0)))
        totais_bloco.extend([
            formatar_inteiro(relatorio.total_pecas),
            formatar_moeda(relatorio.total_valor),
        ])
        
        # Criar tabela do bloco
        tipo = colunas.tipografia(len(itens_bloco))
        larguras = colunas.larguras_por_dia(
            titulos,
            linhas_bloco,
            totais_bloco,
            medir=medidor(fonte_normal, fonte_bold),
            tipo=tipo,
            largura_util=LARGURA_UTIL,
        )
        
        cab_esq = paragrafo("bloco-cab-esq", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_LEFT)
        cab_dir = paragrafo("bloco-cab-dir", fonte_bold, tipo.tam_cabecalho, COR_GELO_900, TA_RIGHT)
        
        cabecalho_tabela = [
            Paragraph(escape(t), cab_esq if i == 0 else cab_dir) for i, t in enumerate(titulos)
        ]
        
        dados = [cabecalho_tabela, *linhas_bloco, totais_bloco]
        estilos = estilos_de_tabela(
            ultima=len(dados) - 1,
            fonte_normal=fonte_normal,
            fonte_bold=fonte_bold,
            tam_cabecalho=tipo.tam_cabecalho,
            tam_celula=tipo.tam_celula,
            padding_v=tipo.padding_v,
            padding_h=tipo.padding_h,
        )
        estilos += [("ALIGN", (0, 0), (0, -1), "LEFT"), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]
        
        tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
        tabela.setStyle(TableStyle(estilos))
        
        # Adicionar título do bloco se houver múltiplos blocos
        if num_itens > itens_por_bloco:
            titulo_bloco = Paragraph(
                f"Itens {inicio + 1} a {fim}",
                paragrafo("titulo-bloco", fonte_bold, 10, COR_AZUL_900, TA_LEFT)
            )
            blocos.append(KeepTogether([titulo_bloco, Spacer(1, 4), tabela]))
            if fim < num_itens:  # Não adicionar espaço após o último bloco
                blocos.append(Spacer(1, 16))
        else:
            blocos.append(tabela)
    
    return blocos


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

    # Tabela de controle de demanda (v1.1 fase 6)
    if relatorio.demanda_diaria:
        elementos.append(Paragraph(TITULO_DEMANDA, titulo_secao))
        elementos.append(Spacer(1, 6))
        tabela_ou_blocos = _tabela_demanda_diaria(relatorio, fonte_normal, fonte_bold)
        # Se for lista (blocos), adiciona todos; se for Table única, adiciona ela
        if isinstance(tabela_ou_blocos, list):
            elementos.extend(tabela_ou_blocos)
        else:
            elementos.append(tabela_ou_blocos)
        elementos.append(Spacer(1, 20))

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
