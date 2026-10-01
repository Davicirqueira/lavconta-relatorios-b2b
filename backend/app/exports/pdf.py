"""Exportação do Relatório de Fechamento em documento PDF.

Utiliza reportlab em formato A4 paisagem com tabelas estruturadas via platypus.
Consome a mesma estrutura calculada de ``Relatorio`` sem recalcular nenhum total.
Registra as fontes TTF da família Inter para consistência visual com a interface.
Degrada graciosamente tamanhos de fonte e larguras de coluna quando houver muitos itens no período.
"""

import io
from decimal import Decimal
from pathlib import Path
from typing import Final

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.datas import hoje_sp
from app.dominio import Relatorio

# Cores da identidade visual (mesmos valores de frontend/src/styles/tokens.css)
COR_AZUL_900 = colors.HexColor("#0B2F58")
COR_AZUL_700 = colors.HexColor("#1C5CA6")
COR_AZUL_50 = colors.HexColor("#F1F7FF")
COR_GELO_50 = colors.HexColor("#F8FAFD")
COR_GELO_100 = colors.HexColor("#F0F4F9")
COR_GELO_200 = colors.HexColor("#E0E7EE")
COR_GELO_300 = colors.HexColor("#CDD5DF")
COR_GELO_600 = colors.HexColor("#56626F")
COR_GELO_900 = colors.HexColor("#141B24")

FONTE_REGULAR: Final[str] = "Inter"
FONTE_NEGRITO: Final[str] = "Inter-Bold"


def _registrar_fontes() -> tuple[str, str]:
    """Registra as fontes Inter-Regular e Inter-SemiBold no reportlab.

    Caso os arquivos TTF não estejam disponíveis, recorre a Helvetica como fallback seguro.
    """
    if FONTE_REGULAR in pdfmetrics.getRegisteredFontNames():
        return FONTE_REGULAR, FONTE_NEGRITO

    dir_fontes = Path(__file__).resolve().parent / "assets" / "fontes"
    caminho_reg = dir_fontes / "Inter-Regular.ttf"
    caminho_bold = dir_fontes / "Inter-SemiBold.ttf"

    if caminho_reg.exists() and caminho_bold.exists():
        pdfmetrics.registerFont(TTFont(FONTE_REGULAR, str(caminho_reg)))
        pdfmetrics.registerFont(TTFont(FONTE_NEGRITO, str(caminho_bold)))
        return FONTE_REGULAR, FONTE_NEGRITO

    return "Helvetica", "Helvetica-Bold"


def _formatar_moeda(valor: Decimal) -> str:
    """Formata valor decimal como moeda brasileira: R$ 1.380,00."""
    formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado}"


def gerar_pdf(relatorio: Relatorio) -> bytes:
    """Gera o arquivo binário PDF a partir do relatório de fechamento já calculado.

    Args:
        relatorio: objeto de domínio contendo linhas, colunas e totais agregados.

    Returns:
        Bytes correspondentes ao arquivo PDF gerado.
    """
    fonte_normal, fonte_bold = _registrar_fontes()

    buffer = io.BytesIO()
    # A4 Paisagem: largura 841.89 pt x altura 595.27 pt
    # Margens de 36 pt (0.5 polegada) -> largura útil = 769.89 pt
    margem = 36.0
    largura_util = landscape(A4)[0] - 2 * margem

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=margem,
        rightMargin=margem,
        topMargin=margem,
        bottomMargin=margem,
    )

    elementos = []

    # 1. Cabeçalho de identificação (Lavandix + Cliente + Período + Emissão)
    caminho_logo = Path(__file__).resolve().parent / "assets" / "lavandix-marca.png"
    emissao_texto = f"Emissão: {hoje_sp().strftime('%d/%m/%Y')}"
    periodo_texto = (
        f"Período: {relatorio.inicio.strftime('%d/%m/%Y')} a {relatorio.fim.strftime('%d/%m/%Y')}"
    )

    logo_elemento = None
    if caminho_logo.exists():
        try:
            # Logo compacto no topo
            logo_elemento = Image(str(caminho_logo), width=110, height=28)
        except Exception:  # noqa: BLE001
            logo_elemento = None

    bloco_esquerda = [
        logo_elemento or "LAVANDIX — Lavanderia Profissional",
        "Relação de Valores para Fechamento",
    ]
    bloco_direita = [
        f"Cliente: {relatorio.cliente_nome}",
        f"{periodo_texto}  ·  {emissao_texto}",
    ]

    tabela_cabecalho_dados = [
        [bloco_esquerda[0], bloco_direita[0]],
        [bloco_esquerda[1], bloco_direita[1]],
    ]
    tabela_cabecalho = Table(
        tabela_cabecalho_dados,
        colWidths=[largura_util * 0.45, largura_util * 0.55],
    )
    tabela_cabecalho.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (0, 0), fonte_bold),
                ("FONTSIZE", (0, 0), (0, 0), 12),
                ("TEXTCOLOR", (0, 0), (0, 0), COR_AZUL_900),
                ("FONTNAME", (0, 1), (0, 1), fonte_normal),
                ("FONTSIZE", (0, 1), (0, 1), 9),
                ("TEXTCOLOR", (0, 1), (0, 1), COR_GELO_600),
                ("FONTNAME", (1, 0), (1, 0), fonte_bold),
                ("FONTSIZE", (1, 0), (1, 0), 12),
                ("TEXTCOLOR", (1, 0), (1, 0), COR_AZUL_900),
                ("FONTNAME", (1, 1), (1, 1), fonte_normal),
                ("FONTSIZE", (1, 1), (1, 1), 9),
                ("TEXTCOLOR", (1, 1), (1, 1), COR_GELO_600),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elementos.append(tabela_cabecalho)
    elementos.append(Spacer(1, 14))

    # 2. Cálculo de larguras de coluna e degradação de fonte
    largura_data = 68.0
    largura_comanda = 56.0
    largura_pecas = 74.0
    largura_valor = 88.0
    largura_fixas = largura_data + largura_comanda + largura_pecas + largura_valor
    espaco_itens = largura_util - largura_fixas

    num_itens = len(relatorio.colunas_itens)

    if num_itens == 0:
        larguras_colunas = [
            largura_data + espaco_itens * 0.25,
            largura_comanda + espaco_itens * 0.25,
            largura_pecas + espaco_itens * 0.25,
            largura_valor + espaco_itens * 0.25,
        ]
        tam_cabecalho = 9.0
        tam_celula = 8.5
        padding_v = 4.0
    else:
        largura_por_item = max(34.0, espaco_itens / num_itens)
        larguras_colunas = [
            largura_data,
            largura_comanda,
            *([largura_por_item] * num_itens),
            largura_pecas,
            largura_valor,
        ]

        # Degradação graciosa conforme a quantidade de colunas de itens
        if num_itens <= 6:
            tam_cabecalho = 9.0
            tam_celula = 8.5
            padding_v = 4.0
        elif num_itens <= 10:
            tam_cabecalho = 8.0
            tam_celula = 7.5
            padding_v = 3.0
        elif num_itens <= 15:
            tam_cabecalho = 7.0
            tam_celula = 6.5
            padding_v = 2.0
        else:
            tam_cabecalho = 6.0
            tam_celula = 5.5
            padding_v = 1.5

    # 3. Montagem dos dados da tabela
    titulos = ["Data", "Comanda"]
    for col in relatorio.colunas_itens:
        titulos.append(col.nome)
    titulos.extend(["Total de peças", "Total R$"])

    linhas_tabela: list[list[str]] = [titulos]

    for linha in relatorio.linhas:
        linha_celulas = [
            linha.data.strftime("%d/%m/%Y"),
            linha.comanda or "",
        ]
        for col_item in relatorio.colunas_itens:
            qtd = linha.quantidades.get(col_item.item_id)
            linha_celulas.append(str(qtd) if qtd is not None else "")
        linha_celulas.append(str(linha.total_pecas))
        linha_celulas.append(_formatar_moeda(linha.total_valor))
        linhas_tabela.append(linha_celulas)

    # Linha de totais
    linha_totais = ["Totais", ""]
    for col_item in relatorio.colunas_itens:
        tot_qtd = relatorio.totais.por_item.get(col_item.item_id, 0)
        linha_totais.append(str(tot_qtd))
    linha_totais.append(str(relatorio.totais.total_pecas))
    linha_totais.append(_formatar_moeda(relatorio.totais.total_valor))
    linhas_tabela.append(linha_totais)

    # 4. Estilos da tabela platypus
    idx_ultima_linha = len(linhas_tabela) - 1
    estilos_tabela = [
        # Cabeçalho
        ("BACKGROUND", (0, 0), (-1, 0), COR_GELO_100),
        ("FONTNAME", (0, 0), (-1, 0), fonte_bold),
        ("FONTSIZE", (0, 0), (-1, 0), tam_cabecalho),
        ("TEXTCOLOR", (0, 0), (-1, 0), COR_GELO_900),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, COR_GELO_300),
        # Linhas de dados gerais
        ("FONTNAME", (0, 1), (-1, idx_ultima_linha - 1), fonte_normal),
        ("FONTSIZE", (0, 1), (-1, idx_ultima_linha - 1), tam_celula),
        ("TEXTCOLOR", (0, 1), (-1, idx_ultima_linha - 1), COR_GELO_900),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), padding_v),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding_v),
        # Alinhamentos
        ("ALIGN", (0, 0), (1, -1), "CENTER"),  # Data e Comanda
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),  # Itens, peças e valores
        # Linhas horizontais suaves
        ("LINEBELOW", (0, 1), (-1, idx_ultima_linha - 1), 0.5, COR_GELO_200),
        # Linha de Totais
        ("BACKGROUND", (0, idx_ultima_linha), (-1, idx_ultima_linha), COR_AZUL_50),
        ("FONTNAME", (0, idx_ultima_linha), (-1, idx_ultima_linha), fonte_bold),
        ("FONTSIZE", (0, idx_ultima_linha), (-1, idx_ultima_linha), max(tam_celula, 7.5)),
        ("TEXTCOLOR", (0, idx_ultima_linha), (-1, idx_ultima_linha), COR_AZUL_900),
        ("LINEABOVE", (0, idx_ultima_linha), (-1, idx_ultima_linha), 1.5, COR_AZUL_900),
        ("LINEBELOW", (0, idx_ultima_linha), (-1, idx_ultima_linha), 1.0, COR_AZUL_900),
    ]

    # Alternância suave de cores nas linhas de dados
    for i in range(1, idx_ultima_linha):
        if i % 2 == 1:
            estilos_tabela.append(("BACKGROUND", (0, i), (-1, i), colors.white))
        else:
            estilos_tabela.append(("BACKGROUND", (0, i), (-1, i), COR_GELO_50))

    tabela = Table(linhas_tabela, colWidths=larguras_colunas)
    tabela.setStyle(TableStyle(estilos_tabela))
    elementos.append(tabela)

    doc.build(elementos)
    return buffer.getvalue()
