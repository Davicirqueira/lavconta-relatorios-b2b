"""Testes de ponta a ponta de Lançamento, contra Postgres real.

Além dos endpoints, verificam duas coisas que só o banco real prova:

  - a coluna gerada ``total`` recalcula quando a quantidade muda na edição;
  - as constraints de unicidade barram o que a validação prévia não viu.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.datas import hoje_sp
from app.core.erros import CodigoErro
from tests.conftest import criar_item_api, criar_item_sem_preco, definir_preco

CAMINHO = "/api/lancamentos"
ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"

# data passada e estável; o preço é semeado para o mês dela
DATA_PEDIDO = "2026-09-10"
MES_PEDIDO = "2026-09"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


def criar_item_com_preco(
    api: TestClient, cliente_id: str, nome: str, valor: str, mes: str = "2026-06"
) -> str:
    return criar_item_api(api, cliente_id, nome, valor, em=f"{mes}-01").json()["id"]


@pytest.fixture
def lencol(api: TestClient, cliente_id: str) -> str:
    return criar_item_com_preco(api, cliente_id, "Lençol", "4.50")


@pytest.fixture
def fronha(api: TestClient, cliente_id: str) -> str:
    return criar_item_com_preco(api, cliente_id, "Fronha", "3.50")


@pytest.fixture
def sem_preco(sessao: Session, cliente_id: str) -> str:
    return criar_item_sem_preco(sessao, cliente_id, "Roupão")


def criar(
    api: TestClient,
    cliente_id: str,
    linhas: list[dict],
    data: str = DATA_PEDIDO,
    comanda: str | None = None,
):  # noqa: ANN201
    corpo = {"cliente_id": cliente_id, "data": data, "linhas": linhas}
    if comanda is not None:
        corpo["comanda"] = comanda
    return api.post(CAMINHO, json=corpo)


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


class TestCriacao:
    def test_cria_congelando_o_valor(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        resposta = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}], comanda="1201")

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["comanda"] == "1201"
        assert corpo["total_pecas"] == 40
        assert corpo["total_valor"] == "180.00"
        assert corpo["linhas"][0]["valor_unitario_congelado"] == "4.50"
        assert corpo["linhas"][0]["total"] == "180.00"

    def test_dinheiro_trafega_como_texto(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        corpo = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()

        assert isinstance(corpo["total_valor"], str)
        assert isinstance(corpo["linhas"][0]["total"], str)

    def test_soma_multiplas_linhas(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        corpo = criar(
            api,
            cliente_id,
            [
                {"item_id": lencol, "quantidade": 40},
                {"item_id": fronha, "quantidade": 30},
            ],
        ).json()

        assert corpo["total_pecas"] == 70
        assert corpo["total_valor"] == "285.00"

    def test_aceita_sem_comanda(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        corpo = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}]).json()

        assert corpo["comanda"] is None

    def test_recusa_item_sem_preco_nomeando(
        self, api: TestClient, cliente_id: str, lencol: str, sem_preco: str
    ) -> None:
        resposta = criar(
            api,
            cliente_id,
            [
                {"item_id": lencol, "quantidade": 10},
                {"item_id": sem_preco, "quantidade": 5},
            ],
        )

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.ITENS_SEM_PRECO.value
        assert "Roupão" in resposta.json()["erro"]["mensagem"]
        assert resposta.json()["erro"]["detalhes"]["itens"] == ["Roupão"]

    def test_nada_e_gravado_quando_falta_preco(
        self, api: TestClient, cliente_id: str, sem_preco: str
    ) -> None:
        criar(api, cliente_id, [{"item_id": sem_preco, "quantidade": 5}])

        listagem = api.get(
            CAMINHO,
            params={"cliente_id": cliente_id, "inicio": "2026-09-01", "fim": "2026-09-30"},
        )
        assert listagem.json() == []

    def test_recusa_data_futura(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        amanha = (hoje_sp() + timedelta(days=1)).isoformat()

        resposta = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data=amanha)

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.DATA_FUTURA.value

    def test_recusa_segundo_lancamento_na_mesma_data(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}])

        resposta = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}])

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.LANCAMENTO_DUPLICADO.value

    def test_recusa_comanda_repetida_ignorando_caixa(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}], comanda="A100")

        resposta = criar(
            api,
            cliente_id,
            [{"item_id": lencol, "quantidade": 10}],
            data="2026-09-11",
            comanda="a100",
        )

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.COMANDA_DUPLICADA.value

    def test_permite_varios_sem_comanda(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        assert criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).status_code == 201
        assert (
            criar(
                api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data="2026-09-11"
            ).status_code
            == 201
        )

    def test_recusa_item_repetido(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        resposta = criar(
            api,
            cliente_id,
            [
                {"item_id": lencol, "quantidade": 40},
                {"item_id": lencol, "quantidade": 10},
            ],
        )

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.ITEM_DUPLICADO_NO_LANCAMENTO.value

    @pytest.mark.parametrize("quantidade", [0, -5])
    def test_recusa_quantidade_nao_positiva(
        self, api: TestClient, cliente_id: str, lencol: str, quantidade: int
    ) -> None:
        resposta = criar(api, cliente_id, [{"item_id": lencol, "quantidade": quantidade}])

        assert resposta.status_code == 422

    def test_recusa_sem_linhas(self, api: TestClient, cliente_id: str) -> None:
        resposta = criar(api, cliente_id, [])

        assert resposta.status_code == 422

    def test_recusa_item_de_outro_cliente(self, api: TestClient, cliente_id: str) -> None:
        outro = api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]
        item_do_outro = criar_item_com_preco(api, outro, "Toalha", "6.00")

        resposta = criar(api, cliente_id, [{"item_id": item_do_outro, "quantidade": 5}])

        assert resposta.status_code == 404


class TestCongelamentoNoBancoReal:
    def test_alterar_o_preco_depois_nao_muda_o_lancamento(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        """A promessa central do produto, verificada contra Postgres."""
        criado = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()

        # preço sobe, com vigência no próprio mês do pedido
        definir_preco(api, lencol, "9.99", em=f"{MES_PEDIDO}-01")

        relido = api.get(f"{CAMINHO}/{criado['id']}").json()

        assert relido["linhas"][0]["valor_unitario_congelado"] == "4.50"
        assert relido["total_valor"] == "180.00"

    def test_lancamento_retroativo_usa_o_mes_do_pedido(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir_preco(api, lencol, "4.80", em=f"{MES_PEDIDO}-01")

        corpo = criar(
            api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data="2026-08-28"
        ).json()

        assert corpo["linhas"][0]["valor_unitario_congelado"] == "4.50"


class TestEdicao:
    def test_altera_quantidade_mantendo_o_congelado(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criado = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()
        definir_preco(api, lencol, "9.99", em=f"{MES_PEDIDO}-01")

        editado = api.put(
            f"{CAMINHO}/{criado['id']}",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "linhas": [{"item_id": lencol, "quantidade": 50}],
            },
        ).json()

        assert editado["linhas"][0]["valor_unitario_congelado"] == "4.50"
        # a coluna gerada do banco recalculou: 50 × 4,50
        assert editado["linhas"][0]["total"] == "225.00"
        assert editado["total_valor"] == "225.00"

    def test_linha_nova_congela_pelo_mes_da_data(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        """Pedido de agosto: a linha nova recebe preço de agosto."""
        toalha = criar_item_com_preco(api, cliente_id, "Toalha", "6.00", mes="2026-08")
        definir_preco(api, toalha, "7.00", em="2026-09-01")

        criado = criar(
            api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data="2026-08-28"
        ).json()

        editado = api.put(
            f"{CAMINHO}/{criado['id']}",
            json={
                "cliente_id": cliente_id,
                "data": "2026-08-28",
                "linhas": [
                    {"item_id": lencol, "quantidade": 10},
                    {"item_id": toalha, "quantidade": 5},
                ],
            },
        ).json()

        por_item = {linha["item_id"]: linha for linha in editado["linhas"]}
        assert por_item[toalha]["valor_unitario_congelado"] == "6.00"

    def test_remove_linha(self, api: TestClient, cliente_id: str, lencol: str, fronha: str) -> None:
        criado = criar(
            api,
            cliente_id,
            [
                {"item_id": lencol, "quantidade": 40},
                {"item_id": fronha, "quantidade": 30},
            ],
        ).json()

        editado = api.put(
            f"{CAMINHO}/{criado['id']}",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "linhas": [{"item_id": lencol, "quantidade": 40}],
            },
        ).json()

        assert len(editado["linhas"]) == 1
        assert editado["total_valor"] == "180.00"

    def test_permite_salvar_sem_alterar_a_data(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criado = criar(
            api, cliente_id, [{"item_id": lencol, "quantidade": 40}], comanda="1201"
        ).json()

        resposta = api.put(
            f"{CAMINHO}/{criado['id']}",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "comanda": "1201",
                "linhas": [{"item_id": lencol, "quantidade": 41}],
            },
        )

        assert resposta.status_code == 200

    def test_recusa_mover_para_data_ocupada(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        primeiro = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data="2026-09-11")

        resposta = api.put(
            f"{CAMINHO}/{primeiro['id']}",
            json={
                "cliente_id": cliente_id,
                "data": "2026-09-11",
                "linhas": [{"item_id": lencol, "quantidade": 40}],
            },
        )

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.LANCAMENTO_DUPLICADO.value

    def test_404_para_inexistente(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        resposta = api.put(
            f"{CAMINHO}/{ID_INEXISTENTE}",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "linhas": [{"item_id": lencol, "quantidade": 10}],
            },
        )

        assert resposta.status_code == 404


class TestPrevia:
    def test_calcula_sem_gravar(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        resposta = api.post(
            f"{CAMINHO}/previa",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "linhas": [
                    {"item_id": lencol, "quantidade": 40},
                    {"item_id": fronha, "quantidade": 30},
                ],
            },
        )

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["total_pecas"] == 70
        assert corpo["total_valor"] == "285.00"
        assert corpo["itens_sem_preco"] == []

        # nada foi persistido
        listagem = api.get(
            CAMINHO,
            params={"cliente_id": cliente_id, "inicio": "2026-09-01", "fim": "2026-09-30"},
        )
        assert listagem.json() == []

    def test_previa_e_salvamento_dao_o_mesmo_total(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        """Impede que a barra de totais mostre valor diferente do cobrado."""
        linhas = [
            {"item_id": lencol, "quantidade": 37},
            {"item_id": fronha, "quantidade": 23},
        ]

        previa = api.post(
            f"{CAMINHO}/previa",
            json={"cliente_id": cliente_id, "data": DATA_PEDIDO, "linhas": linhas},
        ).json()
        salvo = criar(api, cliente_id, linhas).json()

        assert previa["total_pecas"] == salvo["total_pecas"]
        assert previa["total_valor"] == salvo["total_valor"]

    def test_nao_falha_por_item_sem_preco(
        self, api: TestClient, cliente_id: str, lencol: str, sem_preco: str
    ) -> None:
        resposta = api.post(
            f"{CAMINHO}/previa",
            json={
                "cliente_id": cliente_id,
                "data": DATA_PEDIDO,
                "linhas": [
                    {"item_id": lencol, "quantidade": 40},
                    {"item_id": sem_preco, "quantidade": 5},
                ],
            },
        )

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["itens_sem_preco"] == [sem_preco]
        assert corpo["total_valor"] == "180.00"

    def test_nao_valida_data_futura(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        amanha = (hoje_sp() + timedelta(days=1)).isoformat()

        resposta = api.post(
            f"{CAMINHO}/previa",
            json={
                "cliente_id": cliente_id,
                "data": amanha,
                "linhas": [{"item_id": lencol, "quantidade": 2}],
            },
        )

        assert resposta.status_code == 200


class TestListagemEExclusao:
    def test_lista_em_ordem_de_data(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        for dia in ("2026-09-12", "2026-09-10", "2026-09-11"):
            criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data=dia)

        datas = [
            lancamento["data"]
            for lancamento in api.get(
                CAMINHO,
                params={
                    "cliente_id": cliente_id,
                    "inicio": "2026-09-01",
                    "fim": "2026-09-30",
                },
            ).json()
        ]

        assert datas == ["2026-09-10", "2026-09-11", "2026-09-12"]

    def test_filtra_pelo_periodo(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data="2026-08-15")
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}], data=DATA_PEDIDO)

        resultado = api.get(
            CAMINHO,
            params={"cliente_id": cliente_id, "inicio": "2026-09-01", "fim": "2026-09-30"},
        ).json()

        assert len(resultado) == 1
        assert resultado[0]["data"] == DATA_PEDIDO

    def test_recusa_periodo_invertido(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(
            CAMINHO,
            params={"cliente_id": cliente_id, "inicio": "2026-09-30", "fim": "2026-09-01"},
        )

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.PERIODO_INVALIDO.value

    def test_exclui(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        criado = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()

        assert api.delete(f"{CAMINHO}/{criado['id']}").status_code == 204
        assert api.get(f"{CAMINHO}/{criado['id']}").status_code == 404

    def test_exclusao_libera_a_data(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        criado = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()
        api.delete(f"{CAMINHO}/{criado['id']}")

        assert criar(api, cliente_id, [{"item_id": lencol, "quantidade": 10}]).status_code == 201

    def test_exclusao_permite_excluir_o_item_depois(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        """Sem histórico, o item volta a ser excluível."""
        criado = criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}]).json()

        assert api.delete(f"/api/itens/{lencol}").status_code == 409
        api.delete(f"{CAMINHO}/{criado['id']}")
        assert api.delete(f"/api/itens/{lencol}").status_code == 204

    def test_404_ao_excluir_inexistente(self, api: TestClient) -> None:
        assert api.delete(f"{CAMINHO}/{ID_INEXISTENTE}").status_code == 404


class TestProtecaoDoHistorico:
    def test_item_usado_nao_pode_ser_excluido(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}])

        resposta = api.delete(f"/api/itens/{lencol}")

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.EXCLUSAO_COM_HISTORICO.value

    def test_cliente_com_lancamento_nao_pode_ser_excluido(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        criar(api, cliente_id, [{"item_id": lencol, "quantidade": 40}])

        resposta = api.delete(f"/api/clientes/{cliente_id}")

        assert resposta.status_code == 409
        assert codigo_do_erro(resposta) == CodigoErro.EXCLUSAO_COM_HISTORICO.value
