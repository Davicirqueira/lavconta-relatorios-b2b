"""Testes de ponta a ponta de Preço (v1.1), contra Postgres real.

Além de verificar os endpoints, estes testes confirmam que a consulta SQL do
repositório (``DISTINCT ON`` com a ordenação da regra por data) e a versão em
memória usada em ``test_resolucao_de_preco.py`` **concordam**. Se divergirem, o
mesmo cenário dá resultado diferente aqui e lá.

O "hoje" da API é fixado por chamada com ``definir_preco(..., em=...)``.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.erros import CodigoErro
from tests.conftest import criar_item_api, criar_item_sem_preco, definir_preco

ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


@pytest.fixture
def lencol(api: TestClient, cliente_id: str) -> str:
    """Criado com o primeiro preço em 01/06 (4,50)."""
    return criar_item_api(api, cliente_id, "Lençol", "4.50", em="2026-06-01").json()["id"]


@pytest.fixture
def fronha(sessao: Session, cliente_id: str) -> str:
    """Sem nenhum preço (dado legado: pela API o preço é obrigatório)."""
    return criar_item_sem_preco(sessao, cliente_id, "Fronha")


def preco_na_data(api: TestClient, cliente_id: str, item_id: str, data: str) -> dict:
    corpo = api.get(f"/api/clientes/{cliente_id}/precos", params={"data": data}).json()
    return next(i for i in corpo["itens"] if i["item_id"] == item_id)


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


class TestAlteracao:
    def test_define_preco_com_inicio_no_dia(self, api: TestClient, lencol: str) -> None:
        resposta = definir_preco(api, lencol, "4.50", em="2026-09-17")

        assert resposta.status_code == 200
        assert resposta.json() == {"valor_unitario": "4.50", "desde": "2026-09-17", "e_hoje": True}

    def test_dinheiro_trafega_como_texto(self, api: TestClient, lencol: str) -> None:
        """Número em JSON viraria float binário no JavaScript."""
        corpo = definir_preco(api, lencol, "4.5", em="2026-09-17").json()

        assert corpo["valor_unitario"] == "4.50"

    def test_duas_alteracoes_no_mesmo_dia_viram_uma(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        """Garantido também pela unicidade (cliente, item, início) no banco."""
        definir_preco(api, lencol, "4.50", em="2026-09-17")
        definir_preco(api, lencol, "4.70", em="2026-09-17")

        assert preco_na_data(api, cliente_id, lencol, "2026-09-17")["valor_unitario"] == "4.70"

    @pytest.mark.parametrize("valor", ["0", "-1.00", "4.555"])
    def test_recusa_valor_invalido(self, api: TestClient, lencol: str, valor: str) -> None:
        resposta = definir_preco(api, lencol, valor, em="2026-09-17")

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_recusa_data_de_inicio_vinda_do_cliente(self, api: TestClient, lencol: str) -> None:
        """Req 1.2: o navegador não escolhe a partir de quando o preço vale."""
        resposta = api.put(
            f"/api/itens/{lencol}/preco",
            json={"valor_unitario": "4.50", "vigencia_inicio": "2026-01-01"},
        )

        assert resposta.status_code == 422

    def test_recusa_modo_desconhecido(self, api: TestClient, lencol: str) -> None:
        resposta = definir_preco(api, lencol, "4.50", em="2026-09-17", modo="retroativo")

        assert resposta.status_code == 422

    def test_item_inexistente(self, api: TestClient) -> None:
        resposta = definir_preco(api, ID_INEXISTENTE, "4.50", em="2026-09-17")

        assert resposta.status_code == 404

    def test_corrigir_atual_mantem_o_inicio(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir_preco(api, lencol, "4.50", em="2026-06-01")
        definir_preco(api, lencol, "0.48", em="2026-09-10")

        corpo = definir_preco(api, lencol, "4.80", em="2026-09-12", modo="corrigir_atual").json()

        assert corpo == {"valor_unitario": "4.80", "desde": "2026-09-10", "e_hoje": False}
        assert preco_na_data(api, cliente_id, lencol, "2026-09-10")["valor_unitario"] == "4.80"
        assert preco_na_data(api, cliente_id, lencol, "2026-09-09")["valor_unitario"] == "4.50"

    def test_corrigir_sem_preco_e_recusado(self, api: TestClient, fronha: str) -> None:
        resposta = definir_preco(api, fronha, "4.50", em="2026-09-12", modo="corrigir_atual")

        assert resposta.status_code == 422


class TestResolucaoNoBancoReal:
    """A mesma regra dos testes em memória, agora pela consulta do Postgres."""

    @pytest.fixture(autouse=True)
    def _historico(self, api: TestClient, lencol: str) -> None:
        definir_preco(api, lencol, "4.50", em="2026-06-01")
        definir_preco(api, lencol, "4.80", em="2026-09-10")

    @pytest.mark.parametrize(
        ("data", "esperado", "desde"),
        [
            ("2026-09-09", "4.50", "2026-06-01"),  # véspera
            ("2026-09-10", "4.80", "2026-09-10"),  # dia da troca
            ("2026-09-11", "4.80", "2026-09-10"),  # dia seguinte
            ("2027-02-01", "4.80", "2026-09-10"),  # persiste na virada de mês e de ano
            ("2026-01-15", "4.50", "2026-06-01"),  # antes do primeiro: vale o primeiro
        ],
    )
    def test_preco_por_data(
        self,
        api: TestClient,
        cliente_id: str,
        lencol: str,
        data: str,
        esperado: str,
        desde: str,
    ) -> None:
        linha = preco_na_data(api, cliente_id, lencol, data)

        assert linha["valor_unitario"] == esperado
        assert linha["desde"] == desde
        assert linha["sem_preco"] is False

    def test_vence_o_mais_recente_entre_varios(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir_preco(api, lencol, "5.00", em="2026-11-03")

        assert preco_na_data(api, cliente_id, lencol, "2026-10-31")["valor_unitario"] == "4.80"
        assert preco_na_data(api, cliente_id, lencol, "2026-11-03")["valor_unitario"] == "5.00"


class TestListagemNaData:
    def test_marca_item_sem_preco(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        definir_preco(api, lencol, "4.50", em="2026-06-01")

        corpo = api.get(f"/api/clientes/{cliente_id}/precos", params={"data": "2026-09-01"}).json()
        por_id = {i["item_id"]: i for i in corpo["itens"]}

        assert corpo["data"] == "2026-09-01"
        assert len(corpo["itens"]) == 2
        assert por_id[lencol]["sem_preco"] is False
        assert por_id[fronha] == {
            "item_id": fronha,
            "nome": "Fronha",
            "valor_unitario": None,
            "desde": None,
            "sem_preco": True,
        }

    def test_data_e_obrigatoria(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(f"/api/clientes/{cliente_id}/precos")

        assert resposta.status_code == 422

    def test_oculta_itens_inativos_por_padrao(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        api.post(f"/api/itens/{fronha}/inativar")

        corpo = api.get(f"/api/clientes/{cliente_id}/precos", params={"data": "2026-09-01"}).json()

        assert [i["item_id"] for i in corpo["itens"]] == [lencol]

    def test_recusa_cliente_inexistente(self, api: TestClient) -> None:
        resposta = api.get(f"/api/clientes/{ID_INEXISTENTE}/precos", params={"data": "2026-09-01"})

        assert resposta.status_code == 404


class TestImpactoNoBancoReal:
    """Req 1.6 e 1.13 — contagem real de pedidos que mantêm o valor anterior."""

    def test_conta_pedidos_do_periodo_do_preco_atual(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir_preco(api, lencol, "4.50", em="2026-06-01")
        definir_preco(api, lencol, "0.48", em="2026-09-10")
        for data in ("2026-09-05", "2026-09-10", "2026-09-11"):
            api.post(
                "/api/lancamentos",
                json={
                    "cliente_id": cliente_id,
                    "data": data,
                    "linhas": [{"item_id": lencol, "quantidade": 10}],
                },
            )

        corrigir = api.get(
            f"/api/itens/{lencol}/preco/impacto",
            params={"valor_unitario": "4.80", "modo": "corrigir_atual"},
        )

        assert corrigir.status_code == 200
        # 10/09 e 11/09 estão no período do preço errado; 05/09 não
        assert corrigir.json() == {"pedidos_com_valor_anterior": 2}


class TestIsolamentoEntreClientes:
    def test_preco_de_um_cliente_nao_vaza_para_outro(
        self, api: TestClient, sessao: Session, lencol: str
    ) -> None:
        outro = api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]
        criar_item_sem_preco(sessao, outro, "Lençol")

        corpo = api.get(f"/api/clientes/{outro}/precos", params={"data": "2026-09-01"}).json()

        assert corpo["itens"][0]["sem_preco"] is True
