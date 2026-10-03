"""Testes da exportação Excel (tarefa 31).

Garante que o arquivo gerado por ``exports/excel.py``:
- Consome o objeto ``Relatorio`` do domínio sem recalcular nada.
- Contém metadados de cliente e período (Req 8.3).
- Contém células numéricas de verdade para quantidades e valores monetários (Req 8.6).
- Células sem quantidade ficam vazias (None), e não com zero.
- Linha de totais reproduz exatamente os totais do fechamento.
- Primeira linha de dados da tabela é congelada (freeze_panes).
- Funciona corretamente com período vazio.
"""

import io
import uuid
from datetime import date
from decimal import Decimal

import openpyxl

from app.dominio import (
    ColunaDeItem,
    LinhaDoRelatorio,
    Relatorio,
    ResumoDoRelatorio,
    TotaisDoRelatorio,
)
from app.exports.excel import FORMATO_MOEDA, gerar_excel

LENCOL = uuid.uuid4()
FRONHA = uuid.uuid4()
TOALHA = uuid.uuid4()


def criar_relatorio_de_teste() -> Relatorio:
    colunas = (
        ColunaDeItem(item_id=FRONHA, nome="Fronha"),
        ColunaDeItem(item_id=LENCOL, nome="Lençol"),
        ColunaDeItem(item_id=TOALHA, nome="Toalha"),
    )
    linhas = (
        LinhaDoRelatorio(
            lancamento_id=uuid.uuid4(),
            data=date(2026, 9, 1),
            comanda="1201",
            quantidades={LENCOL: 40, FRONHA: 30, TOALHA: 20},
            total_pecas=90,
            total_valor=Decimal("315.00"),
        ),
        LinhaDoRelatorio(
            lancamento_id=uuid.uuid4(),
            data=date(2026, 9, 3),
            comanda=None,  # sem comanda
            quantidades={LENCOL: 50, FRONHA: 40},  # Toalha vazia
            total_pecas=90,
            total_valor=Decimal("330.00"),
        ),
    )
    totais = TotaisDoRelatorio(
        por_item={FRONHA: 70, LENCOL: 90, TOALHA: 20},
        total_pecas=180,
        total_valor=Decimal("645.00"),
    )
    resumo = ResumoDoRelatorio(
        total_pecas=180,
        total_valor=Decimal("645.00"),
        quantidade_lancamentos=2,
        media_diaria_pecas=90,
    )
    return Relatorio(
        cliente_id=uuid.uuid4(),
        cliente_nome="Hotel Aurora",
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        colunas_itens=colunas,
        linhas=linhas,
        totais=totais,
        resumo=resumo,
    )


class TestExportacaoExcel:
    def test_gerar_excel_valido_e_legivel(self) -> None:
        relatorio = criar_relatorio_de_teste()
        conteudo = gerar_excel(relatorio)
        assert isinstance(conteudo, bytes)
        assert len(conteudo) > 0

        # Carregar workbook a partir dos bytes
        wb = openpyxl.load_workbook(io.BytesIO(conteudo))
        ws = wb.active
        assert ws.title == "Fechamento"

        # 1. Metadados de cabeçalho
        assert "Hotel Aurora" in str(ws["A1"].value)
        assert "01/09/2026 a 30/09/2026" in str(ws["A2"].value)

        # 2. Cabeçalho da tabela (linha 4)
        titulos = [ws.cell(row=4, column=col).value for col in range(1, 8)]
        assert titulos == [
            "Data",
            "Comanda",
            "Fronha",
            "Lençol",
            "Toalha",
            "Total de peças",
            "Total R$",
        ]

        # 3. Linha 1 de dados (linha 5 da planilha)
        assert ws.cell(row=5, column=1).value == "01/09/2026"
        assert ws.cell(row=5, column=2).value == "1201"
        assert ws.cell(row=5, column=3).value == 30
        assert ws.cell(row=5, column=4).value == 40
        assert ws.cell(row=5, column=5).value == 20
        assert ws.cell(row=5, column=6).value == 90
        assert ws.cell(row=5, column=7).value == 315.0
        assert ws.cell(row=5, column=7).number_format == FORMATO_MOEDA

        # Células numéricas reais (Req 8.6)
        assert isinstance(ws.cell(row=5, column=3).value, int)
        assert isinstance(ws.cell(row=5, column=6).value, int)
        assert isinstance(ws.cell(row=5, column=7).value, (int, float))

        # 4. Linha 2 de dados (linha 6 da planilha) - comanda nula e Toalha vazia
        assert ws.cell(row=6, column=1).value == "03/09/2026"
        assert ws.cell(row=6, column=2).value in ("", None)
        assert ws.cell(row=6, column=3).value == 40
        assert ws.cell(row=6, column=4).value == 50
        assert ws.cell(row=6, column=5).value is None  # Não exibe zero, fica vazio
        assert ws.cell(row=6, column=6).value == 90
        assert ws.cell(row=6, column=7).value == 330.0

        # 5. Linha de Totais (linha 7 da planilha)
        assert ws.cell(row=7, column=1).value == "Totais"
        assert ws.cell(row=7, column=2).value in ("", None)
        assert ws.cell(row=7, column=3).value == 70
        assert ws.cell(row=7, column=4).value == 90
        assert ws.cell(row=7, column=5).value == 20
        assert ws.cell(row=7, column=6).value == 180
        assert ws.cell(row=7, column=7).value == 645.0
        assert ws.cell(row=7, column=7).number_format == FORMATO_MOEDA

        # Totais em negrito
        assert ws.cell(row=7, column=1).font.bold is True
        assert ws.cell(row=7, column=7).font.bold is True

        # 6. Painel congelado
        assert ws.freeze_panes == "A5"

    def test_gerar_excel_periodo_vazio(self) -> None:
        relatorio = Relatorio(
            cliente_id=uuid.uuid4(),
            cliente_nome="Hotel Aurora",
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
        conteudo = gerar_excel(relatorio)
        wb = openpyxl.load_workbook(io.BytesIO(conteudo))
        ws = wb.active

        # Cabeçalho da tabela com colunas padrão (sem colunas de item)
        titulos = [ws.cell(row=4, column=col).value for col in range(1, 5)]
        assert titulos == ["Data", "Comanda", "Total de peças", "Total R$"]

        # Totais na linha 5
        assert ws.cell(row=5, column=1).value == "Totais"
        assert ws.cell(row=5, column=3).value == 0
        assert ws.cell(row=5, column=4).value == 0.0


class TestNomeDeAba:
    """Excel recusa []:*?/\\ e mais de 31 caracteres; nomes não podem repetir."""

    def test_remove_caracteres_proibidos_e_corta(self) -> None:
        from app.exports.excel import nome_de_aba

        nome = nome_de_aba("Hotel: Aurora / Filial [Centro] * 2026 com nome bem longo", set())

        assert len(nome) <= 31
        assert not set(nome) & set("[]:*?/\\")

    def test_nomes_repetidos_ganham_sufixo(self) -> None:
        from app.exports.excel import nome_de_aba

        usados = {"resumo"}
        primeiro = nome_de_aba("Hotel Aurora", usados)
        segundo = nome_de_aba("hotel aurora", usados)
        resumo = nome_de_aba("Resumo", usados)

        assert (primeiro, segundo, resumo) == ("Hotel Aurora", "hotel aurora (2)", "Resumo (2)")
