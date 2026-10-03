"""Logo do PDF com a proporção real do arquivo (Req 6.1 · §6.2)."""

import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from PIL import Image as ImagemPIL
from pypdf import PdfReader

from app.dominio import Relatorio, ResumoDoRelatorio, TotaisDoRelatorio
from app.exports.pdf import gerar_pdf
from app.exports.pdf.marca import CAMINHO_LOGO, logo, tamanho_do_logo


def _proporcao_do_arquivo() -> float:
    with ImagemPIL.open(CAMINHO_LOGO) as im:
        return im.height / im.width


def test_arquivo_do_logo_sem_margem_transparente() -> None:
    with ImagemPIL.open(CAMINHO_LOGO) as im:
        assert im.mode == "RGBA"
        # Recortado: o conteúdo visível ocupa a imagem inteira
        assert im.getchannel("A").getbbox() == (0, 0, im.width, im.height)


@pytest.mark.parametrize("largura", [60.0, 120.0, 200.0])
def test_altura_segue_a_proporcao_do_arquivo(largura: float) -> None:
    w, h = tamanho_do_logo(largura)
    assert w == largura
    assert h / w == pytest.approx(_proporcao_do_arquivo(), rel=1e-9)


def test_flowable_desenhado_na_proporcao_real() -> None:
    imagem = logo()
    assert imagem is not None
    assert imagem.drawHeight / imagem.drawWidth == pytest.approx(_proporcao_do_arquivo())


def test_pdf_embute_o_logo_recortado() -> None:
    relatorio = Relatorio(
        cliente_id=uuid.uuid4(),
        cliente_nome="Hotel Teste",
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        colunas_itens=(),
        linhas=(),
        totais=TotaisDoRelatorio(por_item={}, total_pecas=0, total_valor=Decimal("0.00")),
        resumo=ResumoDoRelatorio(
            total_pecas=0,
            total_valor=Decimal("0.00"),
            quantidade_lancamentos=0,
            media_diaria_pecas=0,
        ),
    )
    pagina = PdfReader(io.BytesIO(gerar_pdf(relatorio))).pages[0]
    with ImagemPIL.open(CAMINHO_LOGO) as im:
        esperado = im.size
    assert [img.image.size for img in pagina.images] == [esperado]
