"""Testes de ponta a ponta de Cliente: router → service → repositório → banco.

Exercitam a pilha completa contra o Postgres local. A autenticação é substituída
por um usuário fictício: o que está sob teste aqui é a regra de negócio, e a
validação de JWT tem suíte própria.
"""

from fastapi.testclient import TestClient

from app.core.erros import CodigoErro

CAMINHO = "/api/clientes"
ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


def criar(api: TestClient, nome: str):  # noqa: ANN201
    return api.post(CAMINHO, json={"nome": nome})


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


class TestCriacao:
    def test_cria_e_devolve_201(self, api: TestClient) -> None:
        resposta = criar(api, "Hotel Aurora")

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["nome"] == "Hotel Aurora"
        assert corpo["ativo"] is True
        assert corpo["id"]

    def test_remove_espacos_nas_pontas(self, api: TestClient) -> None:
        resposta = criar(api, "   Hotel Aurora   ")

        assert resposta.status_code == 201
        assert resposta.json()["nome"] == "Hotel Aurora"

    def test_recusa_nome_vazio(self, api: TestClient) -> None:
        resposta = criar(api, "   ")

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_recusa_nome_ausente(self, api: TestClient) -> None:
        resposta = api.post(CAMINHO, json={})

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_recusa_nome_duplicado_ignorando_caixa(self, api: TestClient) -> None:
        criar(api, "Hotel Aurora")

        resposta = criar(api, "hotel aurora")

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.NOME_DUPLICADO.value

    def test_mensagem_de_duplicidade_nomeia_o_cliente(self, api: TestClient) -> None:
        criar(api, "Hotel Aurora")

        resposta = criar(api, "Hotel Aurora")

        assert "Hotel Aurora" in resposta.json()["erro"]["mensagem"]


class TestListagem:
    def test_lista_em_ordem_alfabetica(self, api: TestClient) -> None:
        for nome in ("Restaurante Bom Prato", "clinica sao lucas", "Hotel Aurora"):
            criar(api, nome)

        nomes = [cliente["nome"] for cliente in api.get(CAMINHO).json()]

        assert nomes == ["clinica sao lucas", "Hotel Aurora", "Restaurante Bom Prato"]

    def test_oculta_inativos_por_padrao(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]
        criar(api, "Pousada Vista Verde")
        api.post(f"{CAMINHO}/{identificador}/inativar")

        nomes = [cliente["nome"] for cliente in api.get(CAMINHO).json()]

        assert nomes == ["Pousada Vista Verde"]

    def test_inclui_inativos_quando_solicitado(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]
        api.post(f"{CAMINHO}/{identificador}/inativar")

        resposta = api.get(CAMINHO, params={"incluir_inativos": True})

        assert len(resposta.json()) == 1

    def test_lista_vazia_quando_nao_ha_clientes(self, api: TestClient) -> None:
        assert api.get(CAMINHO).json() == []


class TestObtencao:
    def test_obtem_por_id(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]

        resposta = api.get(f"{CAMINHO}/{identificador}")

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Hotel Aurora"

    def test_404_para_id_inexistente(self, api: TestClient) -> None:
        resposta = api.get(f"{CAMINHO}/{ID_INEXISTENTE}")

        assert resposta.status_code == 404
        assert codigo_do_erro(resposta) == CodigoErro.NAO_ENCONTRADO.value


class TestRenomeacao:
    def test_renomeia(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]

        resposta = api.patch(f"{CAMINHO}/{identificador}", json={"nome": "Hotel Aurora Ltda"})

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Hotel Aurora Ltda"

    def test_permite_manter_o_proprio_nome(self, api: TestClient) -> None:
        """O próprio registro não pode colidir consigo mesmo."""
        identificador = criar(api, "Hotel Aurora").json()["id"]

        resposta = api.patch(f"{CAMINHO}/{identificador}", json={"nome": "Hotel Aurora"})

        assert resposta.status_code == 200

    def test_recusa_nome_de_outro_cliente(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]
        criar(api, "Pousada Vista Verde")

        resposta = api.patch(f"{CAMINHO}/{identificador}", json={"nome": "pousada vista verde"})

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.NOME_DUPLICADO.value


class TestSituacao:
    def test_inativa_e_reativa(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]

        inativado = api.post(f"{CAMINHO}/{identificador}/inativar")
        assert inativado.json()["ativo"] is False

        reativado = api.post(f"{CAMINHO}/{identificador}/reativar")
        assert reativado.json()["ativo"] is True

    def test_reativar_nao_duplica_registro(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]
        api.post(f"{CAMINHO}/{identificador}/inativar")
        api.post(f"{CAMINHO}/{identificador}/reativar")

        assert len(api.get(CAMINHO, params={"incluir_inativos": True}).json()) == 1

    def test_404_ao_inativar_inexistente(self, api: TestClient) -> None:
        resposta = api.post(f"{CAMINHO}/{ID_INEXISTENTE}/inativar")

        assert resposta.status_code == 404


class TestExclusao:
    def test_exclui_cliente_sem_lancamento(self, api: TestClient) -> None:
        identificador = criar(api, "Hotel Aurora").json()["id"]

        resposta = api.delete(f"{CAMINHO}/{identificador}")

        assert resposta.status_code == 204
        assert api.get(CAMINHO, params={"incluir_inativos": True}).json() == []

    def test_exclusao_leva_o_catalogo(self, api: TestClient) -> None:
        """Sem histórico, a exclusão remove também itens e preços (Req 2.10)."""
        cliente = criar(api, "Hotel Aurora").json()["id"]
        api.post(f"{CAMINHO}/{cliente}/itens", json={"nome": "Lençol"})

        assert api.delete(f"{CAMINHO}/{cliente}").status_code == 204
        assert api.get(f"{CAMINHO}/{cliente}/itens").status_code == 404

    def test_404_ao_excluir_inexistente(self, api: TestClient) -> None:
        resposta = api.delete(f"{CAMINHO}/{ID_INEXISTENTE}")

        assert resposta.status_code == 404
