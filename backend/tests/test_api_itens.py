"""Testes de ponta a ponta de Item (catálogo por cliente, com preço — v1.1)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.erros import CodigoErro
from tests.conftest import criar_item_api, criar_item_sem_preco, definir_preco, hoje_fixado

ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


@pytest.fixture
def outro_cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]


def criar_item(api: TestClient, cliente_id: str, nome: str, valor: str = "4.50"):  # noqa: ANN201
    return criar_item_api(api, cliente_id, nome, valor, em="2026-10-02")


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


def nomes_no_catalogo(api: TestClient, cliente_id: str) -> list[str]:
    return [i["nome"] for i in api.get(f"/api/clientes/{cliente_id}/itens").json()]


class TestCriacao:
    def test_cria_item_com_o_preco(self, api: TestClient, cliente_id: str) -> None:
        resposta = criar_item(api, cliente_id, "Lençol", "4.5")

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["nome"] == "Lençol"
        assert corpo["cliente_id"] == cliente_id
        assert corpo["ativo"] is True
        assert corpo["preco_atual"] == {
            "valor_unitario": "4.50",
            "desde": "2026-10-02",
            "e_hoje": True,
        }

    def test_preco_e_obrigatorio(self, api: TestClient, cliente_id: str) -> None:
        """Req 3.1."""
        resposta = api.post(f"/api/clientes/{cliente_id}/itens", json={"nome": "Lençol"})

        assert resposta.status_code == 422
        assert nomes_no_catalogo(api, cliente_id) == []

    @pytest.mark.parametrize("valor", ["0", "-1.00", "4.555"])
    def test_preco_invalido_nao_cria_o_item(
        self, api: TestClient, cliente_id: str, valor: str
    ) -> None:
        """Req 3.3: ou os dois são gravados, ou nenhum."""
        resposta = criar_item(api, cliente_id, "Lençol", valor)

        assert resposta.status_code == 422
        assert nomes_no_catalogo(api, cliente_id) == []

    def test_primeiro_preco_vale_para_pedido_anterior_ao_cadastro(
        self, api: TestClient, cliente_id: str
    ) -> None:
        """Req 1.7: item criado hoje entra em pedido retroativo."""
        item_id = criar_item_api(api, cliente_id, "Lençol", "4.50", em="2026-10-02").json()["id"]

        corpo = api.get(f"/api/clientes/{cliente_id}/precos", params={"data": "2026-09-01"}).json()

        assert corpo["itens"] == [
            {
                "item_id": item_id,
                "nome": "Lençol",
                "valor_unitario": "4.50",
                "desde": "2026-10-02",
                "sem_preco": False,
            }
        ]

    def test_recusa_nome_vazio(self, api: TestClient, cliente_id: str) -> None:
        resposta = criar_item(api, cliente_id, "   ")

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_404_para_cliente_inexistente(self, api: TestClient) -> None:
        resposta = criar_item(api, ID_INEXISTENTE, "Lençol")

        assert resposta.status_code == 404
        assert codigo_do_erro(resposta) == CodigoErro.NAO_ENCONTRADO.value

    def test_recusa_nome_duplicado_no_mesmo_cliente(self, api: TestClient, cliente_id: str) -> None:
        criar_item(api, cliente_id, "Lençol")

        resposta = criar_item(api, cliente_id, "lençol")

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.NOME_DUPLICADO.value

    def test_aceita_mesmo_nome_em_clientes_diferentes(
        self, api: TestClient, cliente_id: str, outro_cliente_id: str
    ) -> None:
        """A unicidade é POR CLIENTE, não global (Req 3.2)."""
        assert criar_item(api, cliente_id, "Lençol").status_code == 201
        assert criar_item(api, outro_cliente_id, "Lençol").status_code == 201


class TestListagem:
    def test_lista_apenas_itens_do_cliente(
        self, api: TestClient, cliente_id: str, outro_cliente_id: str
    ) -> None:
        criar_item(api, cliente_id, "Lençol")
        criar_item(api, outro_cliente_id, "Toalha")

        assert nomes_no_catalogo(api, cliente_id) == ["Lençol"]

    def test_lista_em_ordem_alfabetica(self, api: TestClient, cliente_id: str) -> None:
        for nome in ("Toalha", "fronha", "Lençol"):
            criar_item(api, cliente_id, nome)

        assert nomes_no_catalogo(api, cliente_id) == ["fronha", "Lençol", "Toalha"]

    def test_traz_o_preco_de_hoje(self, api: TestClient, cliente_id: str) -> None:
        """Req 3.4: o cartão mostra o preço atual, calculado pela API."""
        item_id = criar_item_api(api, cliente_id, "Lençol", "4.50", em="2026-06-01").json()["id"]
        definir_preco(api, item_id, "4.80", em="2026-09-15")

        with hoje_fixado(api, "2026-09-14"):
            vespera = api.get(f"/api/clientes/{cliente_id}/itens").json()[0]["preco_atual"]
        with hoje_fixado(api, "2026-10-02"):
            depois = api.get(f"/api/clientes/{cliente_id}/itens").json()[0]["preco_atual"]

        assert vespera == {"valor_unitario": "4.50", "desde": "2026-06-01", "e_hoje": False}
        assert depois == {"valor_unitario": "4.80", "desde": "2026-09-15", "e_hoje": False}

    def test_item_sem_preco_vem_com_preco_nulo(
        self, api: TestClient, sessao: Session, cliente_id: str
    ) -> None:
        """Req 3.5: dado legado sem preço aparece como tal."""
        criar_item_sem_preco(sessao, cliente_id, "Edredom")

        item = api.get(f"/api/clientes/{cliente_id}/itens").json()[0]

        assert item["nome"] == "Edredom"
        assert item["preco_atual"] is None

    def test_oculta_inativos_por_padrao(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]
        criar_item(api, cliente_id, "Lençol")
        api.post(f"/api/itens/{item_id}/inativar")

        assert nomes_no_catalogo(api, cliente_id) == ["Lençol"]

    def test_inclui_inativos_quando_solicitado(self, api: TestClient, cliente_id: str) -> None:
        """Necessário para registrar lançamento retroativo (Req 3.10)."""
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]
        api.post(f"/api/itens/{item_id}/inativar")

        itens = api.get(
            f"/api/clientes/{cliente_id}/itens", params={"incluir_inativos": True}
        ).json()

        assert [item["nome"] for item in itens] == ["Tapete"]

    def test_404_para_cliente_inexistente(self, api: TestClient) -> None:
        resposta = api.get(f"/api/clientes/{ID_INEXISTENTE}/itens")

        assert resposta.status_code == 404


class TestRenomeacao:
    def test_renomeia_mantendo_o_preco(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Toalha", "5.50").json()["id"]

        resposta = api.patch(f"/api/itens/{item_id}", json={"nome": "Toalha de banho"})

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Toalha de banho"
        assert resposta.json()["preco_atual"]["valor_unitario"] == "5.50"

    def test_recusa_nome_de_outro_item_do_mesmo_cliente(
        self, api: TestClient, cliente_id: str
    ) -> None:
        item_id = criar_item(api, cliente_id, "Toalha").json()["id"]
        criar_item(api, cliente_id, "Lençol")

        resposta = api.patch(f"/api/itens/{item_id}", json={"nome": "LENÇOL"})

        assert resposta.status_code == 409

    def test_aceita_nome_usado_em_outro_cliente(
        self, api: TestClient, cliente_id: str, outro_cliente_id: str
    ) -> None:
        item_id = criar_item(api, cliente_id, "Toalha").json()["id"]
        criar_item(api, outro_cliente_id, "Lençol")

        resposta = api.patch(f"/api/itens/{item_id}", json={"nome": "Lençol"})

        assert resposta.status_code == 200

    def test_404_para_item_inexistente(self, api: TestClient) -> None:
        resposta = api.patch(f"/api/itens/{ID_INEXISTENTE}", json={"nome": "Lençol"})

        assert resposta.status_code == 404


class TestSituacao:
    def test_inativa_e_reativa(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]

        assert api.post(f"/api/itens/{item_id}/inativar").json()["ativo"] is False
        assert api.post(f"/api/itens/{item_id}/reativar").json()["ativo"] is True

    def test_reativar_nao_duplica_registro(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]
        api.post(f"/api/itens/{item_id}/inativar")
        api.post(f"/api/itens/{item_id}/reativar")

        itens = api.get(
            f"/api/clientes/{cliente_id}/itens", params={"incluir_inativos": True}
        ).json()
        assert len(itens) == 1


class TestExclusao:
    def test_exclui_item_nunca_usado(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]

        resposta = api.delete(f"/api/itens/{item_id}")

        assert resposta.status_code == 204
        assert api.get(f"/api/itens/{item_id}").status_code == 404

    def test_404_para_item_inexistente(self, api: TestClient) -> None:
        assert api.delete(f"/api/itens/{ID_INEXISTENTE}").status_code == 404
