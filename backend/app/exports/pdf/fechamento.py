"""PDF do Relatório de Fechamento de um cliente.

Consome a estrutura já calculada de ``Relatorio`` sem recalcular nenhum total
(Req 6.7): a tabela por dia usa ``linhas`` e ``totais``.
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

TEXTO_VAZIO: Final[str] = "Nenhum pedido no período escolhido."


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


def _tabela_por_dia(relatorio: Relatorio, fonte_normal: str, fonte_bold: str) -> Table | list[Flowable]:
    """Uma linha por pedido; cabeçalho repetido em cada página (Req 6.5).
    
    Se houver muitos itens (>8), a tabela é dividida em blocos verticais para 
    manter legibilidade. Cada bloco mostra data, comanda, até 8 itens, e totais.
    """
    ITENS_POR_BLOCO = 8
    num_itens = len(relatorio.colunas_itens)
    
    # Se couber em uma tabela, usa a lógica original
    if num_itens <= ITENS_POR_BLOCO:
        return _tabela_simples(relatorio, fonte_normal, fonte_bold)
    
    # Caso contrário, divide em blocos
    return _tabelas_em_blocos(relatorio, fonte_normal, fonte_bold, ITENS_POR_BLOCO)


def _tabela_simples(relatorio: Relatorio, fonte_normal: str, fonte_bold: str) -> Table:
    """Tabela única com todos os itens (usado quando há poucos itens)."""
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


def _tabelas_em_blocos(
    relatorio: Relatorio, fonte_normal: str, fonte_bold: str, itens_por_bloco: int
) -> list[Flowable]:
    """Divide os itens em blocos e gera uma tabela para cada bloco.
    
    Cada bloco contém: Data, Comanda, até N itens, Total peças, Total R$.
    Os blocos são empilhados verticalmente com espaçamento entre eles.
    """
    blocos: list[Flowable] = []
    num_itens = len(relatorio.colunas_itens)
    
    for inicio in range(0, num_itens, itens_por_bloco):
        fim = min(inicio + itens_por_bloco, num_itens)
        itens_bloco = relatorio.colunas_itens[inicio:fim]
        
        # Construir títulos do bloco
        titulos = ["Data", "Comanda"]
        titulos.extend(col.nome for col in itens_bloco)
        titulos.extend(["Total de peças", "Total R$"])
        
        # Construir linhas do bloco
        linhas_bloco: list[list[str]] = []
        for linha in relatorio.linhas:
            celulas = [linha.data.strftime("%d/%m/%Y"), linha.comanda or ""]
            for col in itens_bloco:
                qtd = linha.quantidades.get(col.item_id)
                celulas.append(formatar_inteiro(qtd) if qtd is not None else "")
            celulas.extend([formatar_inteiro(linha.total_pecas), formatar_moeda(linha.total_valor)])
            linhas_bloco.append(celulas)
        
        # Construir totais do bloco
        totais_bloco = ["Totais", ""]
        for col in itens_bloco:
            totais_bloco.append(formatar_inteiro(relatorio.totais.por_item.get(col.item_id, 0)))
        totais_bloco.extend([
            formatar_inteiro(relatorio.totais.total_pecas),
            formatar_moeda(relatorio.totais.total_valor),
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
            Paragraph(escape(t), cab_esq if i < 2 else cab_dir) for i, t in enumerate(titulos)
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
        estilos += [("ALIGN", (0, 0), (1, -1), "LEFT"), ("ALIGN", (2, 0), (-1, -1), "RIGHT")]
        
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
        tabela_ou_blocos = _tabela_por_dia(relatorio, fonte_normal, fonte_bold)
        # Se for lista (blocos), adiciona todos; se for Table única, adiciona ela
        if isinstance(tabela_ou_blocos, list):
            elementos.extend(tabela_ou_blocos)
        else:
            elementos.append(tabela_ou_blocos)

    doc.build(elementos, canvasmaker=CanvasComRodape)
    return buffer.getvalue()
