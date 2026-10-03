"""Acabamento do PDF v1.1 (Req 6.2–6.7 · design §6.3–§6.5).

- Larguras: função pura, com medidor falso (determinístico) e com a fonte real.
- Conteúdo: texto extraído com ``pypdf`` — rodapé "Página X de Y", cabeçalho da
  tabela repetido, resumo por item, totais, estado vazio, PDF geral.
"""

import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pypdf import PdfReader

from app.dominio import (
    ColunaDeItem,
    LinhaDoRelatorio,
    LinhaResumoItem,
    Relatorio,
    RelatorioGeral,
    ResumoDoRelatorio,
    SecaoDoCliente,
    TotaisDoRelatorio,
)
from app.exports.pdf import gerar_pdf, gerar_pdf_geral
from app.exports.pdf.colunas import ITEM_MAX, ITEM_MIN, larguras_por_dia, tipografia
from app.exports.pdf.estilo import registrar_fontes
from app.exports.pdf.pagina import LARGURA_UTIL, medidor


def _texto_por_pagina(conteudo: bytes) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(conteudo)).pages]


def _relatorio(
    nomes_itens: list[str],
    dias: int,
    *,
    cliente: str = "Hotel Aurora",
    preco: str = "4.50",
) -> Relatorio:
    """Relatório coerente: cada dia, 10 peças de cada item ao mesmo preço."""
    valor = Decimal(preco)
    colunas = tuple(ColunaDeItem(uuid.uuid4(), nome) for nome in nomes_itens)
    linhas = tuple(
        LinhaDoRelatorio(
            lancamento_id=uuid.uuid4(),
            data=date(2026, 9, 1) + timedelta(days=d % 30),
            comanda=str(1000 + d) if d % 2 == 0 else None,
            quantidades={c.item_id: 10 for c in colunas},
            total_pecas=10 * len(colunas),
            total_valor=valor * 10 * len(colunas),
        )
        for d in range(dias)
    )
    total_pecas = sum(linha.total_pecas for linha in linhas)
    total_valor = sum((linha.total_valor for linha in linhas), Decimal("0"))
    return Relatorio(
        cliente_id=uuid.uuid4(),
        cliente_nome=cliente,
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        colunas_itens=colunas,
        linhas=linhas,
        totais=TotaisDoRelatorio(
            por_item={c.item_id: 10 * dias for c in colunas},
            total_pecas=total_pecas,
            total_valor=total_valor,
        ),
        resumo=ResumoDoRelatorio(
            total_pecas=total_pecas,
            total_valor=total_valor,
            quantidade_lancamentos=dias,
            media_diaria_pecas=total_pecas // dias if dias else 0,
        ),
        resumo_por_item=tuple(
            LinhaResumoItem(c.item_id, c.nome, valor, 10 * dias, valor * 10 * dias) for c in colunas
        ),
    )


# ---------------------------------------------------------------------------
# Larguras (função pura)
# ---------------------------------------------------------------------------


def _medir_falso(texto: str, negrito: bool, tamanho: float) -> float:
    del negrito, tamanho
    return 5.0 * len(texto)


def _larguras(nomes: list[str], medir=_medir_falso) -> list[float]:  # noqa: ANN001
    titulos = ["Data", "Comanda", *nomes, "Total de peças", "Total R$"]
    linha = ["01/09/2026", "1001", *(["10"] * len(nomes)), "30", "R$ 135,00"]
    totais = ["Totais", "", *(["300"] * len(nomes)), "900", "R$ 4.050,00"]
    return larguras_por_dia(
        titulos,
        [linha],
        totais,
        medir=medir,
        tipo=tipografia(len(nomes)),
        largura_util=LARGURA_UTIL,
    )


class TestLarguras:
    @pytest.mark.parametrize("n", [1, 3])
    def test_poucos_itens_ficam_entre_48_e_96_sem_esticar(self, n: int) -> None:
        larguras = _larguras([f"Item {i}" for i in range(n)])

        assert all(ITEM_MIN <= w <= ITEM_MAX for w in larguras[2:-2])
        # não ocupa a página inteira: sobra espaço à direita
        assert sum(larguras) < LARGURA_UTIL * 0.6

    def test_vinte_itens_encolhem_para_caber_na_pagina(self) -> None:
        larguras = _larguras([f"Item {i}" for i in range(20)])

        assert sum(larguras) == pytest.approx(LARGURA_UTIL)
        assert all(0 < w <= ITEM_MAX for w in larguras[2:-2])

    def test_largura_acompanha_o_conteudo_com_limites(self) -> None:
        curto, medio, longo = _larguras(["A", "Toalha rosto", "Edredom king size bordado"])[2:5]

        assert curto == ITEM_MIN
        assert medio == pytest.approx(5.0 * len("Toalha rosto") + 12)
        assert longo == ITEM_MAX

    def test_colunas_fixas_com_largura_natural(self) -> None:
        larguras = _larguras(["Lençol"])

        assert larguras[0] == pytest.approx(5.0 * len("01/09/2026") + 12)
        assert larguras[-1] == pytest.approx(5.0 * len("R$ 4.050,00") + 12)

    def test_muitos_itens_nao_quebram_palavra_no_titulo(self) -> None:
        """Visto no PDF renderizado: "Lenç/ol", "Fronh/a" com 18 itens.

        Ao encolher, cada coluna para na maior palavra do título; a página ainda
        comporta isso com 18 itens de nomes reais.
        """
        nomes = [
            "Lençol casal", "Lençol solteiro", "Fronha", "Toalha de banho",
            "Toalha de rosto", "Toalha de piso", "Roupão", "Edredom", "Cobertor",
            "Colcha", "Travesseiro", "Capa de colchão", "Cortina", "Toalha de mesa",
            "Guardanapo", "Avental", "Jaleco", "Uniforme camareira",
        ]  # fmt: skip
        medir = medidor(*registrar_fontes())
        tipo = tipografia(len(nomes))
        larguras = _larguras(nomes, medir)

        assert sum(larguras) <= LARGURA_UTIL + 0.01
        for nome, largura in zip(nomes, larguras[2:-2], strict=True):
            maior_palavra = max(medir(p, True, tipo.tam_cabecalho) for p in nome.split())
            assert largura >= maior_palavra + 2 * tipo.padding_h - 0.01, nome

    @pytest.mark.parametrize("n", [1, 3, 20])
    def test_com_a_fonte_real_cabe_na_pagina(self, n: int) -> None:
        larguras = _larguras([f"Item {i}" for i in range(n)], medidor(*registrar_fontes()))

        assert sum(larguras) <= LARGURA_UTIL + 0.01
        assert all(w <= ITEM_MAX for w in larguras[2:-2])


# ---------------------------------------------------------------------------
# Conteúdo do PDF por cliente
# ---------------------------------------------------------------------------


class TestPdfPorCliente:
    def test_uma_pagina_tem_rodape_pagina_1_de_1(self) -> None:
        paginas = _texto_por_pagina(gerar_pdf(_relatorio(["Lençol", "Fronha"], 5)))

        assert len(paginas) == 1
        assert "Página 1 de 1" in paginas[0]
        assert "Lavandix · Relação de valores" in paginas[0]

    def test_varias_paginas_numeradas_e_cabecalho_repetido(self) -> None:
        paginas = _texto_por_pagina(gerar_pdf(_relatorio(["Lençol", "Fronha"], 60)))
        total = len(paginas)

        assert total >= 2
        for numero, texto in enumerate(paginas, start=1):
            assert f"Página {numero} de {total}" in texto
        # cabeçalho da tabela em toda página seguinte que tem linhas de pedido
        # (só a página 1 traz o período; nas outras, data = linha de pedido)
        com_pedidos = [t for t in paginas[1:] if "/09/2026" in t]
        assert com_pedidos, "o cenário deveria ter pedidos além da página 1"
        for texto in com_pedidos:
            assert "Total de peças" in texto

    def test_resumo_por_item_e_totais(self) -> None:
        relatorio = _relatorio(["Lençol", "Fronha"], 3, preco="4.50")
        texto = "\n".join(_texto_por_pagina(gerar_pdf(relatorio)))

        assert "Resumo por item" in texto
        # 3 dias × 10 peças × R$ 4,50 = R$ 135,00 por item; total R$ 270,00
        assert "R$ 4,50" in texto
        assert "R$ 135,00" in texto
        assert "R$ 270,00" in texto
        assert "60" in texto

    def test_milhar_com_ponto_como_na_tela(self) -> None:
        texto = "\n".join(_texto_por_pagina(gerar_pdf(_relatorio(["Lençol"], 120))))

        assert "1.200" in texto  # 120 dias × 10 peças

    def test_periodo_vazio_avisa_e_nao_mostra_resumo(self) -> None:
        relatorio = _relatorio([], 0)
        texto = "\n".join(_texto_por_pagina(gerar_pdf(relatorio)))

        assert "Nenhum pedido no período escolhido." in texto
        assert "Resumo por item" not in texto
        assert "Página 1 de 1" in texto

    def test_nome_com_caracteres_de_marcacao(self) -> None:
        relatorio = _relatorio(["Toalha <G> & P"], 2, cliente="Hotel A & B <Centro>")
        texto = "\n".join(_texto_por_pagina(gerar_pdf(relatorio)))

        assert "Hotel A & B <Centro>" in texto
        assert "Toalha <G> & P" in texto


# ---------------------------------------------------------------------------
# PDF geral
# ---------------------------------------------------------------------------


def _geral() -> RelatorioGeral:
    lencol, fronha, toalha = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    aurora = SecaoDoCliente(
        cliente_id=uuid.uuid4(),
        cliente_nome="Hotel Aurora",
        linhas=(
            LinhaResumoItem(fronha, "Fronha", Decimal("3.50"), 10, Decimal("35.00")),
            LinhaResumoItem(lencol, "Lençol", Decimal("4.50"), 40, Decimal("180.00")),
            LinhaResumoItem(lencol, "Lençol", Decimal("4.80"), 20, Decimal("96.00")),
        ),
        total_pecas=70,
        total_valor=Decimal("311.00"),
    )
    pousada = SecaoDoCliente(
        cliente_id=uuid.uuid4(),
        cliente_nome="Pousada Vista Verde",
        linhas=(LinhaResumoItem(toalha, "Toalha", Decimal("5.80"), 12, Decimal("69.60")),),
        total_pecas=12,
        total_valor=Decimal("69.60"),
    )
    return RelatorioGeral(
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        secoes=(aurora, pousada),
        total_pecas=82,
        total_valor=Decimal("380.60"),
    )


class TestPdfGeral:
    def test_bloco_por_cliente_e_total_geral(self) -> None:
        texto = "\n".join(_texto_por_pagina(gerar_pdf_geral(_geral())))

        assert "Todos os clientes" in texto
        assert texto.index("Hotel Aurora") < texto.index("Pousada Vista Verde")
        assert "R$ 4,50" in texto and "R$ 4,80" in texto  # Lençol a dois valores
        assert "Total geral" in texto
        assert "R$ 380,60" in texto
        assert "Página 1 de 1" in texto

    def test_vazio(self) -> None:
        vazio = RelatorioGeral(
            inicio=date(2025, 1, 1),
            fim=date(2025, 1, 31),
            secoes=(),
            total_pecas=0,
            total_valor=Decimal("0.00"),
        )
        texto = "\n".join(_texto_por_pagina(gerar_pdf_geral(vazio)))

        assert "Nenhum pedido no período escolhido." in texto
        assert "Total geral" not in texto
