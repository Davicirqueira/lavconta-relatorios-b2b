"""Identidade visual do PDF: cores, fontes e formatação de valores.

Cores com os mesmos valores de ``frontend/src/styles/tokens.css``. As fontes Inter
são registradas a partir dos TTF locais; sem eles, cai para Helvetica.
"""

from decimal import Decimal
from pathlib import Path
from typing import Final

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DIR_ASSETS: Final[Path] = Path(__file__).resolve().parent.parent / "assets"
# a linha de total não fica menor que isso, mesmo com fonte reduzida
TAM_MINIMO_TOTAIS: Final[float] = 7.5

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


def registrar_fontes() -> tuple[str, str]:
    """Registra Inter-Regular e Inter-SemiBold e devolve (normal, negrito).

    Caso os arquivos TTF não estejam disponíveis, recorre a Helvetica.
    """
    if FONTE_REGULAR in pdfmetrics.getRegisteredFontNames():
        return FONTE_REGULAR, FONTE_NEGRITO

    dir_fontes = DIR_ASSETS / "fontes"
    caminho_reg = dir_fontes / "Inter-Regular.ttf"
    caminho_bold = dir_fontes / "Inter-SemiBold.ttf"

    if caminho_reg.exists() and caminho_bold.exists():
        pdfmetrics.registerFont(TTFont(FONTE_REGULAR, str(caminho_reg)))
        pdfmetrics.registerFont(TTFont(FONTE_NEGRITO, str(caminho_bold)))
        return FONTE_REGULAR, FONTE_NEGRITO

    return "Helvetica", "Helvetica-Bold"


def formatar_moeda(valor: Decimal) -> str:
    """Formata valor decimal como moeda brasileira: R$ 1.380,00."""
    formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado}"


def formatar_inteiro(valor: int) -> str:
    """Inteiro com separador de milhar brasileiro: 1.234 (igual à tela)."""
    return f"{valor:,}".replace(",", ".")


def paragrafo(
    nome: str, fonte: str, tamanho: float, cor: colors.Color, alinhamento: int = TA_LEFT
) -> ParagraphStyle:
    """Estilo de parágrafo com entrelinha proporcional ao tamanho."""
    return ParagraphStyle(
        nome,
        fontName=fonte,
        fontSize=tamanho,
        leading=tamanho * 1.2,
        textColor=cor,
        alignment=alinhamento,
    )


def estilos_de_tabela(
    *,
    ultima: int,
    fonte_normal: str,
    fonte_bold: str,
    tam_cabecalho: float,
    tam_celula: float,
    padding_v: float,
    padding_h: float = 6.0,
) -> list[tuple]:
    """Moldura comum das tabelas: cabeçalho, linhas alternadas e linha de total.

    ``ultima`` é o índice da linha de total. Índices explícitos (não ``-1``): numa
    tabela partida entre páginas, ``-1`` apontaria para a última linha de cada
    pedaço e pintaria uma linha de pedido como se fosse o total.
    """
    estilos: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_GELO_100),
        ("FONTNAME", (0, 0), (-1, 0), fonte_bold),
        ("FONTSIZE", (0, 0), (-1, 0), tam_cabecalho),
        ("TEXTCOLOR", (0, 0), (-1, 0), COR_GELO_900),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, COR_GELO_300),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), padding_v),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding_v),
        ("LEFTPADDING", (0, 0), (-1, -1), padding_h),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding_h),
        ("BACKGROUND", (0, ultima), (-1, ultima), COR_AZUL_50),
        ("FONTNAME", (0, ultima), (-1, ultima), fonte_bold),
        ("FONTSIZE", (0, ultima), (-1, ultima), max(tam_celula, TAM_MINIMO_TOTAIS)),
        ("TEXTCOLOR", (0, ultima), (-1, ultima), COR_AZUL_900),
        ("LINEABOVE", (0, ultima), (-1, ultima), 1.5, COR_AZUL_900),
        ("LINEBELOW", (0, ultima), (-1, ultima), 1.0, COR_AZUL_900),
    ]
    if ultima > 1:
        estilos += [
            ("FONTNAME", (0, 1), (-1, ultima - 1), fonte_normal),
            ("FONTSIZE", (0, 1), (-1, ultima - 1), tam_celula),
            ("TEXTCOLOR", (0, 1), (-1, ultima - 1), COR_GELO_900),
            ("LINEBELOW", (0, 1), (-1, ultima - 2), 0.5, COR_GELO_200),
        ]
    for i in range(1, ultima):
        fundo = colors.white if i % 2 == 1 else COR_GELO_50
        estilos.append(("BACKGROUND", (0, i), (-1, i), fundo))
    return estilos
