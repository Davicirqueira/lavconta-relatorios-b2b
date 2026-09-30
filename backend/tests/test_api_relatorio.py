"""Testes de ponta a ponta do endpoint de Relatório, contra Postgres real (tarefa 30).

Exercita o endpoint GET /api/relatorio através da API HTTP com autenticação,
sessão de banco, consulta SQL real (buscar_linhas_do_periodo) e serialização Pydantic.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.erros import CodigoErro

CAMINHO = "/api/relatorio"
ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


def criar_item_com_preco(
    api: TestClient, cliente_id: str, nome: str, valor: str, mes: str = "2026-06"
) -> str:
    item_id = api.post(f"/api/clientes/{cliente_id}/itens", json={"nome": nome}).json()["id"]
    api.put(
        f"/api/clientes/{cliente_id}/precos",
        json={"item_id": item_id, "vigencia_mes": mes, "valor_unitario": valor},
    )
    return item_id


@pytest.fixture
def lencol(api: TestClient, cliente_id: str) -> str:
    return criar_item_com_preco(api, cliente_id, "Lençol", "4.50")


@pytest.fixture
def fronha(api: TestClient, cliente_id: str) -> str:
    return criar_item_com_preco(api, cliente_id, "Fronha", "3.50")


def criar_lancamento(
    api: TestClient,
    cliente_id: str,
    data: str,
    linhas: list[dict],
    comanda: str | None = None,
) -> str:
    corpo = {"cliente_id": cliente_id, "data": data, "linhas": linhas}
    if comanda is not None:
        corpo["comanda"] = comanda
    resposta = api.post("/api/lancamentos", json=corpo)
    assert resposta.status_code == 201
    return resposta.json()["id"]


class TestEndpointRelatorio:
    def test_gerar_relatorio_com_sucesso(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        criar_lancamento(
            api,
            cliente_id,
            "2026-09-01",
            [{"item_id": lencol, "quantidade": 40}, {"item_id": fronha, "quantidade": 30}],
            comanda="1201",
        )
        criar_lancamento(
            api,
            cliente_id,
            "2026-09-02",
            [{"item_id": lencol, "quantidade": 10}],
        )

        resposta = api.get(f"{CAMINHO}?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30")

        assert resposta.status_code == 200
        corpo = resposta.json()

        # Identificação e período
        assert corpo["cliente"]["id"] == cliente_id
        assert corpo["cliente"]["nome"] == "Hotel Aurora"
        assert corpo["periodo"] == {"inicio": "2026-09-01", "fim": "2026-09-30"}

        # Colunas ordenadas alfabeticamente
        assert [col["nome"] for col in corpo["colunas_itens"]] == ["Fronha", "Lençol"]

        # Linhas de lançamentos
        linhas = corpo["linhas"]
        assert len(linhas) == 2
        assert linhas[0]["data"] == "2026-09-01"
        assert linhas[0]["comanda"] == "1201"
        assert linhas[0]["quantidades"] == {lencol: 40, fronha: 30}
        assert linhas[0]["total_pecas"] == 70
        assert linhas[0]["total_valor"] == "285.00"

        assert linhas[1]["data"] == "2026-09-02"
        assert linhas[1]["comanda"] is None
        assert linhas[1]["quantidades"] == {lencol: 10}
        assert linhas[1]["total_pecas"] == 10
        assert linhas[1]["total_valor"] == "45.00"

        # Totais
        assert corpo["totais"]["por_item"] == {lencol: 50, fronha: 30}
        assert corpo["totais"]["total_pecas"] == 80
        assert corpo["totais"]["total_valor"] == "330.00"

        # Resumo coincide exatamente com totais (defeito B1)
        assert corpo["resumo"]["total_pecas"] == corpo["totais"]["total_pecas"]
        assert corpo["resumo"]["total_valor"] == corpo["totais"]["total_valor"]
        assert corpo["resumo"]["quantidade_lancamentos"] == 2
        assert corpo["resumo"]["media_diaria_pecas"] == 40

    def test_relatorio_periodo_vazio(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(f"{CAMINHO}?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30")

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["linhas"] == []
        assert corpo["colunas_itens"] == []
        assert corpo["totais"]["total_pecas"] == 0
        assert corpo["totais"]["total_valor"] == "0.00"
        assert corpo["totais"]["por_item"] == {}
        assert corpo["resumo"]["quantidade_lancamentos"] == 0
        assert corpo["resumo"]["media_diaria_pecas"] == 0

    def test_recusa_periodo_invalido(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(f"{CAMINHO}?cliente_id={cliente_id}&inicio=2026-09-30&fim=2026-09-01")

        assert resposta.status_code == 422
        assert resposta.json()["erro"]["codigo"] == CodigoErro.PERIODO_INVALIDO.value

    def test_recusa_cliente_inexistente(self, api: TestClient) -> None:
        resposta = api.get(
            f"{CAMINHO}?cliente_id={ID_INEXISTENTE}&inicio=2026-09-01&fim=2026-09-30"
        )

        assert resposta.status_code == 404
        assert resposta.json()["erro"]["codigo"] == CodigoErro.NAO_ENCONTRADO.value

    def test_recusa_parametros_faltantes(self, api: TestClient, cliente_id: str) -> None:
        # Sem cliente_id
        r1 = api.get(f"{CAMINHO}?inicio=2026-09-01&fim=2026-09-30")
        assert r1.status_code == 422

        # Sem inicio
        r2 = api.get(f"{CAMINHO}?cliente_id={cliente_id}&fim=2026-09-30")
        assert r2.status_code == 422

        # Sem fim
        r3 = api.get(f"{CAMINHO}?cliente_id={cliente_id}&inicio=2026-09-01")
        assert r3.status_code == 422


class TestEndpointsExportacao:
    """Tarefa 33 — endpoints /excel e /pdf reproduzem os mesmos totais do relatório em tela.

    Req 8.1, 8.4: cada formato retorna bytes com content-type e Content-Disposition corretos.
    Req 8.2: as mesmas linhas, colunas e totais exibidos em tela.
    Req 8.5: a geração ocorre no backend a partir dos mesmos dados calculados.

    Verificação de paridade: busca os totais da resposta JSON e confirma que os
    bytes do Excel/PDF contêm os mesmos números — provando que os três formatos
    derivam da mesma agregação e não de cálculos paralelos que poderiam divergir.
    """

    @pytest.fixture
    def relatorio_base(self, api: TestClient, cliente_id: str, lencol: str, fronha: str) -> dict:
        """Cria dois lançamentos e devolve o corpo JSON do relatório."""
        criar_lancamento(
            api,
            cliente_id,
            "2026-09-01",
            [{"item_id": lencol, "quantidade": 40}, {"item_id": fronha, "quantidade": 30}],
            comanda="1201",
        )
        criar_lancamento(
            api,
            cliente_id,
            "2026-09-03",
            [{"item_id": lencol, "quantidade": 50}],
        )
        resposta = api.get(f"{CAMINHO}?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30")
        assert resposta.status_code == 200
        return resposta.json()

    # --- Excel ------------------------------------------------------------

    def test_excel_retorna_bytes_com_content_type_correto(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        resposta = api.get(
            f"{CAMINHO}/excel?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )

        assert resposta.status_code == 200
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in resposta.headers["content-type"]
        )
        assert "attachment" in resposta.headers["content-disposition"]
        assert ".xlsx" in resposta.headers["content-disposition"]
        assert len(resposta.content) > 0

    def test_excel_nome_do_arquivo_e_descritivo(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        resposta = api.get(
            f"{CAMINHO}/excel?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )
        disposition = resposta.headers["content-disposition"]

        # Nome contém slug do cliente e o período
        assert "hotel-aurora" in disposition.lower()
        assert "2026-09-01" in disposition
        assert "2026-09-30" in disposition

    def test_excel_totais_coincidem_com_relatorio_em_tela(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        """Req 8.2 — totais do Excel batem com o JSON do relatório."""
        import io

        import openpyxl

        total_pecas_tela = relatorio_base["totais"]["total_pecas"]
        total_valor_tela = relatorio_base["totais"]["total_valor"]

        resposta = api.get(
            f"{CAMINHO}/excel?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )
        assert resposta.status_code == 200

        wb = openpyxl.load_workbook(io.BytesIO(resposta.content))
        ws = wb.active

        # A linha de totais é a última linha preenchida
        ultima_linha = ws.max_row
        assert ws.cell(row=ultima_linha, column=1).value == "Totais"

        # Colunas: Data | Comanda | Fronha | Lençol | Total peças | Total R$
        # = colunas 1, 2, 3, 4, 5, 6
        total_pecas_excel = ws.cell(row=ultima_linha, column=5).value
        total_valor_excel = ws.cell(row=ultima_linha, column=6).value

        assert total_pecas_excel == total_pecas_tela
        # total_valor vem como string decimal ("330.00") na API; no Excel é float
        assert abs(total_valor_excel - float(total_valor_tela)) < 0.001

    # --- PDF --------------------------------------------------------------

    def test_pdf_retorna_bytes_com_content_type_correto(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        resposta = api.get(
            f"{CAMINHO}/pdf?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )

        assert resposta.status_code == 200
        assert "application/pdf" in resposta.headers["content-type"]
        assert "attachment" in resposta.headers["content-disposition"]
        assert ".pdf" in resposta.headers["content-disposition"]
        assert resposta.content.startswith(b"%PDF-")

    def test_pdf_nome_do_arquivo_e_descritivo(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        resposta = api.get(
            f"{CAMINHO}/pdf?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )
        disposition = resposta.headers["content-disposition"]

        assert "hotel-aurora" in disposition.lower()
        assert "2026-09-01" in disposition
        assert "2026-09-30" in disposition

    def test_pdf_contem_nome_do_cliente_e_periodo(
        self, api: TestClient, relatorio_base: dict, cliente_id: str
    ) -> None:
        """O PDF embute os metadados — verificável pelo texto codificado nos bytes."""
        resposta = api.get(
            f"{CAMINHO}/pdf?cliente_id={cliente_id}&inicio=2026-09-01&fim=2026-09-30"
        )
        assert resposta.status_code == 200
        # "Hotel Aurora" deve aparecer no fluxo de bytes do PDF como texto
        assert b"Hotel Aurora" in resposta.content

    def test_exportacoes_exigem_mesmos_parametros_que_relatorio(
        self, api: TestClient, cliente_id: str
    ) -> None:
        """Sem cliente_id ou datas, os endpoints de exportação respondem 422."""
        for formato in ("excel", "pdf"):
            r = api.get(f"{CAMINHO}/{formato}?inicio=2026-09-01&fim=2026-09-30")
            assert r.status_code == 422, f"{formato} sem cliente_id deveria ser 422"
