"""Testes de ponta a ponta de Preço, contra Postgres real.

Além de verificar os endpoints, estes testes cumprem um papel específico: confirmam
que a consulta ``DISTINCT ON`` do repositório e a versão em memória usada nos testes
de resolução **concordam**. Se divergirem, o mesmo cenário dá resultado diferente
aqui e em ``test_resolucao_de_preco.py``.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.erros import CodigoErro

ID_INEXISTENTE = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def cliente_id(api: TestClient) -> str:
    return api.post("/api/clientes", json={"nome": "Hotel Aurora"}).json()["id"]


@pytest.fixture
def lencol(api: TestClient, cliente_id: str) -> str:
    return api.post(f"/api/clientes/{cliente_id}/itens", json={"nome": "Lençol"}).json()["id"]


@pytest.fixture
def fronha(api: TestClient, cliente_id: str) -> str:
    return api.post(f"/api/clientes/{cliente_id}/itens", json={"nome": "Fronha"}).json()["id"]


def definir(api: TestClient, cliente_id: str, item_id: str, mes: str, valor: str):  # noqa: ANN201
    return api.put(
        f"/api/clientes/{cliente_id}/precos",
        json={"item_id": item_id, "vigencia_mes": mes, "valor_unitario": valor},
    )


def listar(api: TestClient, cliente_id: str, mes: str):  # noqa: ANN201
    return api.get(f"/api/clientes/{cliente_id}/precos", params={"mes": mes})


def codigo_do_erro(resposta) -> str:  # noqa: ANN001
    return resposta.json()["erro"]["codigo"]


class TestDefinicao:
    def test_define_preco(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        resposta = definir(api, cliente_id, lencol, "2026-06", "4.50")

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["valor_unitario"] == "4.50"
        assert corpo["vigencia_mes"] == "2026-06"
        assert corpo["item_id"] == lencol

    def test_dinheiro_trafega_como_texto(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        """Número em JSON viraria float binário no JavaScript."""
        corpo = definir(api, cliente_id, lencol, "2026-06", "4.50").json()

        assert isinstance(corpo["valor_unitario"], str)

    def test_normaliza_para_duas_casas(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        corpo = definir(api, cliente_id, lencol, "2026-06", "4.5").json()

        assert corpo["valor_unitario"] == "4.50"

    def test_repetir_o_mes_atualiza_sem_duplicar(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")
        definir(api, cliente_id, lencol, "2026-06", "5.00")

        itens = listar(api, cliente_id, "2026-06").json()["itens"]
        do_lencol = next(i for i in itens if i["item_id"] == lencol)

        assert do_lencol["valor_unitario"] == "5.00"
        assert do_lencol["vigencia_origem"] == "2026-06"

    @pytest.mark.parametrize("valor", ["0", "-1.00"])
    def test_recusa_valor_nao_positivo(
        self, api: TestClient, cliente_id: str, lencol: str, valor: str
    ) -> None:
        resposta = definir(api, cliente_id, lencol, "2026-06", valor)

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_recusa_mais_de_duas_casas(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        resposta = definir(api, cliente_id, lencol, "2026-06", "4.555")

        assert resposta.status_code == 422

    @pytest.mark.parametrize("mes", ["2026-13", "2026", "junho/2026", "26-06", ""])
    def test_recusa_mes_malformado(
        self, api: TestClient, cliente_id: str, lencol: str, mes: str
    ) -> None:
        resposta = definir(api, cliente_id, lencol, mes, "4.50")

        assert resposta.status_code == 422

    def test_recusa_item_de_outro_cliente(self, api: TestClient, cliente_id: str) -> None:
        outro = api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]
        item_do_outro = api.post(f"/api/clientes/{outro}/itens", json={"nome": "Toalha"}).json()[
            "id"
        ]

        resposta = definir(api, cliente_id, item_do_outro, "2026-06", "4.50")

        assert resposta.status_code == 404

    def test_recusa_cliente_inexistente(self, api: TestClient, lencol: str) -> None:
        resposta = definir(api, ID_INEXISTENTE, lencol, "2026-06", "4.50")

        assert resposta.status_code == 404


class TestPropagacaoNoBancoReal:
    """A mesma regra dos testes em memória, agora pelo DISTINCT ON do Postgres."""

    def test_propaga_para_meses_seguintes(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")

        for mes in ("2026-07", "2026-09", "2026-12", "2027-03"):
            itens = listar(api, cliente_id, mes).json()["itens"]
            do_lencol = next(i for i in itens if i["item_id"] == lencol)
            assert do_lencol["valor_unitario"] == "4.50", f"falhou em {mes}"
            assert do_lencol["vigencia_origem"] == "2026-06"
            assert do_lencol["sem_preco"] is False

    def test_mes_com_vigencia_propria_sobrepoe(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")
        definir(api, cliente_id, lencol, "2026-10", "4.80")

        setembro = next(
            i for i in listar(api, cliente_id, "2026-09").json()["itens"] if i["item_id"] == lencol
        )
        outubro = next(
            i for i in listar(api, cliente_id, "2026-10").json()["itens"] if i["item_id"] == lencol
        )

        assert setembro["valor_unitario"] == "4.50"
        assert setembro["vigencia_origem"] == "2026-06"
        assert outubro["valor_unitario"] == "4.80"
        assert outubro["vigencia_origem"] == "2026-10"

    def test_vence_o_mais_recente_entre_varios(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-01", "3.00")
        definir(api, cliente_id, lencol, "2026-04", "3.50")
        definir(api, cliente_id, lencol, "2026-08", "4.00")

        junho = next(
            i for i in listar(api, cliente_id, "2026-06").json()["itens"] if i["item_id"] == lencol
        )

        assert junho["valor_unitario"] == "3.50"
        assert junho["vigencia_origem"] == "2026-04"

    def test_preco_futuro_nao_vale_antes_da_vigencia(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")
        definir(api, cliente_id, lencol, "2026-11", "5.20")

        setembro = next(
            i for i in listar(api, cliente_id, "2026-09").json()["itens"] if i["item_id"] == lencol
        )

        assert setembro["valor_unitario"] == "4.50"

    def test_virada_de_ano(self, api: TestClient, cliente_id: str, lencol: str) -> None:
        definir(api, cliente_id, lencol, "2026-12", "5.00")
        definir(api, cliente_id, lencol, "2027-01", "5.50")

        dezembro = next(
            i for i in listar(api, cliente_id, "2026-12").json()["itens"] if i["item_id"] == lencol
        )
        janeiro = next(
            i for i in listar(api, cliente_id, "2027-01").json()["itens"] if i["item_id"] == lencol
        )

        assert dezembro["valor_unitario"] == "5.00"
        assert janeiro["valor_unitario"] == "5.50"


class TestListagem:
    def test_marca_item_sem_preco(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")

        itens = listar(api, cliente_id, "2026-09").json()["itens"]
        por_id = {i["item_id"]: i for i in itens}

        assert por_id[lencol]["sem_preco"] is False
        assert por_id[fronha]["sem_preco"] is True
        assert por_id[fronha]["valor_unitario"] is None
        assert por_id[fronha]["vigencia_origem"] is None

    def test_lista_todos_os_itens_do_catalogo(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        """Inclusive os sem preço: eles bloqueiam lançamento e precisam aparecer."""
        corpo = listar(api, cliente_id, "2026-09").json()

        assert corpo["mes"] == "2026-09"
        assert len(corpo["itens"]) == 2

    def test_mes_omitido_usa_o_corrente(self, api: TestClient, cliente_id: str) -> None:
        from app.core.datas import hoje_sp, mes_como_texto

        corpo = api.get(f"/api/clientes/{cliente_id}/precos").json()

        assert corpo["mes"] == mes_como_texto(hoje_sp())

    def test_recusa_mes_malformado(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(f"/api/clientes/{cliente_id}/precos", params={"mes": "setembro"})

        assert resposta.status_code == 422
        assert codigo_do_erro(resposta) == CodigoErro.VALIDACAO.value

    def test_oculta_itens_inativos_por_padrao(
        self, api: TestClient, cliente_id: str, lencol: str, fronha: str
    ) -> None:
        api.post(f"/api/itens/{fronha}/inativar")

        itens = listar(api, cliente_id, "2026-09").json()["itens"]

        assert [i["item_id"] for i in itens] == [lencol]

    def test_recusa_cliente_inexistente(self, api: TestClient) -> None:
        resposta = api.get(f"/api/clientes/{ID_INEXISTENTE}/precos")

        assert resposta.status_code == 404


class TestIsolamentoEntreClientes:
    def test_preco_de_um_cliente_nao_vaza_para_outro(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        definir(api, cliente_id, lencol, "2026-06", "4.50")

        outro = api.post("/api/clientes", json={"nome": "Pousada Vista Verde"}).json()["id"]
        api.post(f"/api/clientes/{outro}/itens", json={"nome": "Lençol"})

        itens = listar(api, outro, "2026-09").json()["itens"]

        assert itens[0]["sem_preco"] is True


class TestVigenciaSugerida:
    def test_primeiro_preco_sugere_mes_corrente(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        from app.core.datas import hoje_sp, mes_como_texto

        resposta = api.get(f"/api/clientes/{cliente_id}/precos/vigencia-sugerida/{lencol}")

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["vigencia_mes"] == mes_como_texto(hoje_sp())
        assert corpo["e_primeiro_preco"] is True

    def test_alteracao_sugere_mes_seguinte(
        self, api: TestClient, cliente_id: str, lencol: str
    ) -> None:
        from app.core.datas import hoje_sp, mes_como_texto, mes_seguinte

        definir(api, cliente_id, lencol, "2026-06", "4.50")

        corpo = api.get(f"/api/clientes/{cliente_id}/precos/vigencia-sugerida/{lencol}").json()

        assert corpo["vigencia_mes"] == mes_como_texto(mes_seguinte(hoje_sp()))
        assert corpo["e_primeiro_preco"] is False

    def test_recusa_item_inexistente(self, api: TestClient, cliente_id: str) -> None:
        resposta = api.get(f"/api/clientes/{cliente_id}/precos/vigencia-sugerida/{ID_INEXISTENTE}")

        assert resposta.status_code == 404
