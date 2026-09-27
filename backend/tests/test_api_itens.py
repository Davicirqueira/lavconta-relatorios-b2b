"""Testes de ponta a ponta de Item (catálogo por cliente)."""

import pytest
from fastapi.testclient import TestClient

from app.core.erros import CodigoErro

ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


@pytest.fixture
def outro_cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]


def criar_item(api: TestClient, cliente_id: str, nome: str):  # noqa: ANN201
    return api.post(f"/api/clientes/{cliente_id}/itens", json={"nome": nome})


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


class TestCriacao:
    def test_cria_item_vinculado_ao_cliente(self, api: TestClient, cliente_id: str) -> None:
        resposta = criar_item(api, cliente_id, "Lençol")

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["nome"] == "Lençol"
        assert corpo["cliente_id"] == cliente_id
        assert corpo["ativo"] is True

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

        itens = api.get(f"/api/clientes/{cliente_id}/itens").json()

        assert [item["nome"] for item in itens] == ["Lençol"]

    def test_lista_em_ordem_alfabetica(self, api: TestClient, cliente_id: str) -> None:
        for nome in ("Toalha", "fronha", "Lençol"):
            criar_item(api, cliente_id, nome)

        itens = api.get(f"/api/clientes/{cliente_id}/itens").json()

        assert [item["nome"] for item in itens] == ["fronha", "Lençol", "Toalha"]

    def test_oculta_inativos_por_padrao(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Tapete").json()["id"]
        criar_item(api, cliente_id, "Lençol")
        api.post(f"/api/itens/{item_id}/inativar")

        itens = api.get(f"/api/clientes/{cliente_id}/itens").json()

        assert [item["nome"] for item in itens] == ["Lençol"]

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
    def test_renomeia(self, api: TestClient, cliente_id: str) -> None:
        item_id = criar_item(api, cliente_id, "Toalha").json()["id"]

        resposta = api.patch(f"/api/itens/{item_id}", json={"nome": "Toalha de banho"})

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Toalha de banho"

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
