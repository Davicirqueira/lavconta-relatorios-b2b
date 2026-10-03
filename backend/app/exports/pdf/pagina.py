"""Moldura da página: formato do documento, cabeçalho e rodapé "Página X de Y"."""

import io
from datetime import date
from typing import Any, Final
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from app.exports.pdf.colunas import Medidor
from app.exports.pdf.estilo import (
    COR_AZUL_900,
    COR_GELO_300,
    COR_GELO_600,
    paragrafo,
    registrar_fontes,
)
from app.exports.pdf.marca import TEXTO_SEM_LOGO, logo

# A4 paisagem (841.89 × 595.27 pt)
MARGEM: Final[float] = 36.0
MARGEM_INFERIOR: Final[float] = 48.0  # espaço para o rodapé
TAMANHO_PAGINA: Final[tuple[float, float]] = landscape(A4)
LARGURA_UTIL: Final[float] = TAMANHO_PAGINA[0] - 2 * MARGEM

TEXTO_RODAPE: Final[str] = "Lavandix · Relação de valores"
Y_RODAPE: Final[float] = 24.0


def criar_documento(buffer: io.BytesIO) -> SimpleDocTemplate:
    """Documento A4 paisagem com as margens padrão."""
    return SimpleDocTemplate(
        buffer,
        pagesize=TAMANHO_PAGINA,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=MARGEM,
        bottomMargin=MARGEM_INFERIOR,
    )


def medidor(fonte_normal: str, fonte_bold: str) -> Medidor:
    """Mede texto com as fontes registradas, para o cálculo de larguras."""

    def medir(texto: str, negrito: bool, tamanho: float) -> float:
        return stringWidth(texto, fonte_bold if negrito else fonte_normal, tamanho)

    return medir


class CanvasComRodape(Canvas):
    """Canvas que escreve "Página X de Y" depois de conhecer o total de páginas.

    O total só é conhecido no fim do documento, então cada página é guardada em
    ``showPage`` em vez de emitida, e em ``save`` todas são emitidas com o rodapé.
    É a receita conhecida do reportlab para "page x of y" (``canvasmaker`` de
    ``SimpleDocTemplate.build``); a versão 5.0.1 não traz um recurso pronto para
    isso. O comportamento está coberto por ``test_exports_pdf.py``.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._paginas_guardadas: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802 — nome da API do reportlab
        self._paginas_guardadas.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._paginas_guardadas)
        for estado in self._paginas_guardadas:
            self.__dict__.update(estado)
            self._desenhar_rodape(total)
            super().showPage()
        super().save()

    def _desenhar_rodape(self, total: int) -> None:
        fonte_normal, _ = registrar_fontes()
        largura = TAMANHO_PAGINA[0]
        self.saveState()
        self.setStrokeColor(COR_GELO_300)
        self.setLineWidth(0.5)
        self.line(MARGEM, Y_RODAPE + 12, largura - MARGEM, Y_RODAPE + 12)
        self.setFont(fonte_normal, 8)
        self.setFillColor(COR_GELO_600)
        self.drawString(MARGEM, Y_RODAPE, TEXTO_RODAPE)
        self.drawRightString(
            largura - MARGEM, Y_RODAPE, f"Página {self.getPageNumber()} de {total}"
        )
        self.restoreState()


def _periodo(inicio: date, fim: date) -> str:
    return f"Período: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"


def cabecalho(
    *,
    titulo_direita: str,
    inicio: date,
    fim: date,
    emissao: date,
    fonte_normal: str,
    fonte_bold: str,
) -> Table:
    """Logo à esquerda; título do documento, destinatário, período e emissão à direita."""
    imagem = logo()
    marca: Any = imagem or Paragraph(
        TEXTO_SEM_LOGO, paragrafo("marca", fonte_bold, 12, COR_AZUL_900)
    )
    largura_marca = (imagem.drawWidth if imagem else 200.0) + 12

    def linha(nome: str, texto: str, fonte: str, tamanho: float, cor: Any) -> Paragraph:
        return Paragraph(escape(texto), paragrafo(nome, fonte, tamanho, cor, TA_RIGHT))

    identificacao = [
        linha("doc", "Relação de valores para fechamento", fonte_normal, 9, COR_GELO_600),
        linha("dest", titulo_direita, fonte_bold, 14, COR_AZUL_900),
        linha(
            "periodo",
            f"{_periodo(inicio, fim)}  ·  Emissão: {emissao.strftime('%d/%m/%Y')}",
            fonte_normal,
            9,
            COR_GELO_600,
        ),
    ]
    tabela = Table(
        [[marca, identificacao]],
        colWidths=[largura_marca, LARGURA_UTIL - largura_marca],
    )
    tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (-1, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, COR_GELO_300),
            ]
        )
    )
    return tabela
