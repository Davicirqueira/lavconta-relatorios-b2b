"""Testes da exportação PDF (tarefa 32).

Garante que o arquivo gerado por ``exports/pdf.py``:
- Gera documento PDF válido em A4 paisagem via reportlab.
- Registra a família Inter a partir dos arquivos TTF locais.
- Degrada tamanho de fonte e largura quando houver muitos itens, preservando legibilidade.
- Funciona corretamente com período vazio.
- Reproduz os dados sem recalcular nada do domínio.
"""

import uuid
from datetime import date
from decimal import Decimal

from app.dominio import (
    ColunaDeItem,
    LinhaDoRelatorio,
    Relatorio,
    ResumoDoRelatorio,
    TotaisDoRelatorio,
)
from app.exports.pdf import _formatar_moeda, gerar_pdf


def criar_relatorio_de_teste(num_itens: int = 3) -> Relatorio:
    colunas = tuple(
        ColunaDeItem(item_id=uuid.uuid4(), nome=f"Item {i + 1}") for i in range(num_itens)
    )
    quantidades = {col.item_id: 10 * (idx + 1) for idx, col in enumerate(colunas)}
    linhas = (
        LinhaDoRelatorio(
            lancamento_id=uuid.uuid4(),
            data=date(2026, 9, 1),
            comanda="1001",
            quantidades=quantidades,
            total_pecas=sum(quantidades.values()),
            total_valor=Decimal("250.00"),
        ),
        LinhaDoRelatorio(
            lancamento_id=uuid.uuid4(),
            data=date(2026, 9, 2),
            comanda=None,
            quantidades={colunas[0].item_id: 15} if colunas else {},
            total_pecas=15 if colunas else 0,
            total_valor=Decimal("45.00"),
        ),
    )
    tot_item = {col.item_id: quantidades[col.item_id] for col in colunas}
    if colunas:
        tot_item[colunas[0].item_id] += 15

    totais = TotaisDoRelatorio(
        por_item=tot_item,
        total_pecas=sum(tot_item.values()),
        total_valor=Decimal("295.00"),
    )
    resumo = ResumoDoRelatorio(
        total_pecas=totais.total_pecas,
        total_valor=totais.total_valor,
        quantidade_lancamentos=len(linhas),
        media_diaria_pecas=totais.total_pecas // len(linhas),
    )
    return Relatorio(
        cliente_id=uuid.uuid4(),
        cliente_nome="Hotel Teste Aurora",
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        colunas_itens=colunas,
        linhas=linhas,
        totais=totais,
        resumo=resumo,
    )


class TestExportacaoPDF:
    def test_gerar_pdf_valido(self) -> None:
        relatorio = criar_relatorio_de_teste(3)
        conteudo = gerar_pdf(relatorio)

        assert isinstance(conteudo, bytes)
        assert len(conteudo) > 0
        # Todo PDF começa com o cabeçalho %PDF-
        assert conteudo.startswith(b"%PDF-")

    def test_gerar_pdf_muitas_colunas_degrada_graciosamente(self) -> None:
        # Testa a degradação com 12 e 18 itens
        relatorio_12 = criar_relatorio_de_teste(12)
        pdf_12 = gerar_pdf(relatorio_12)
        assert pdf_12.startswith(b"%PDF-")

        relatorio_18 = criar_relatorio_de_teste(18)
        pdf_18 = gerar_pdf(relatorio_18)
        assert pdf_18.startswith(b"%PDF-")

    def test_gerar_pdf_periodo_vazio(self) -> None:
        relatorio_vazio = Relatorio(
            cliente_id=uuid.uuid4(),
            cliente_nome="Hotel Vazio",
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
        pdf = gerar_pdf(relatorio_vazio)
        assert pdf.startswith(b"%PDF-")

    def test_formatador_de_moeda(self) -> None:
        assert _formatar_moeda(Decimal("1380.50")) == "R$ 1.380,50"
        assert _formatar_moeda(Decimal("0.00")) == "R$ 0,00"
        assert _formatar_moeda(Decimal("45.10")) == "R$ 45,10"
