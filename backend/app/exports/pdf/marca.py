"""Logo da Lavandix para o cabeçalho do PDF.

O arquivo é o original de ``assets/marca/lavandix-marca-original.png`` com a margem
transparente recortada (600×538 px). A altura desenhada sai da proporção do próprio
arquivo; nenhuma proporção fica fixa no código.
"""

from typing import Final

from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image

from app.exports.pdf.estilo import DIR_ASSETS

CAMINHO_LOGO = DIR_ASSETS / "lavandix-marca-emblema.png"
TEXTO_SEM_LOGO = "LAVANDIX — Lavanderia Profissional"
# 120 pt (o valor do design) deixava o cabeçalho com ~1/5 da página e a
# primeira página com 5 linhas a menos; o emblema é quase quadrado.
LARGURA_LOGO: Final[float] = 80.0


def tamanho_do_logo(largura: float = LARGURA_LOGO) -> tuple[float, float]:
    """(largura, altura) em pt, com a altura pela proporção real do arquivo."""
    px_largura, px_altura = ImageReader(str(CAMINHO_LOGO)).getSize()
    return largura, largura * px_altura / px_largura


def logo(largura: float = LARGURA_LOGO) -> Image | None:
    """Devolve o logo como flowable, ou ``None`` se o arquivo não puder ser lido."""
    if not CAMINHO_LOGO.exists():
        return None
    try:
        w, h = tamanho_do_logo(largura)
        return Image(str(CAMINHO_LOGO), width=w, height=h)
    except Exception:  # noqa: BLE001 — arquivo ilegível: o cabeçalho usa o texto
        return None
