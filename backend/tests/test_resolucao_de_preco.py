"""Testes da regra de preço por data (v1.1, Req 1).

Esta é a regra mais consequente do produto: dela sai o valor que será congelado no
pedido e cobrado do cliente. Um erro aqui produz fatura errada sem que nada
pareça quebrado.

Rodam SEM banco, contra repositórios em memória. A mesma regra na consulta SQL é
verificada contra Postgres em ``test_api_precos.py``.

O relógio do serviço é fixado em cada teste (``hoje=``), para que véspera, dia e
dia seguinte de uma alteração sejam provados sem depender da data real.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.erros import CodigoErro, ErroDeDominio
from app.dominio import ModoDeAlteracao
from app.services.servico_preco import ServicoPreco
from tests.repositorios_falsos import (
    RepositorioClienteFalso,
    RepositorioItemFalso,
    RepositorioPrecoFalso,
)

DIA_DA_TROCA = date(2026, 9, 10)


@pytest.fixture
def repositorio_cliente() -> RepositorioClienteFalso:
    return RepositorioClienteFalso()


@pytest.fixture
def repositorio_item() -> RepositorioItemFalso:
    return RepositorioItemFalso()


@pytest.fixture
def repositorio() -> RepositorioPrecoFalso:
    return RepositorioPrecoFalso()


@pytest.fixture
def em(
    repositorio: RepositorioPrecoFalso,
    repositorio_cliente: RepositorioClienteFalso,
    repositorio_item: RepositorioItemFalso,
):  # noqa: ANN201
    """Serviço com o relógio fixado no dia informado: ``em(date(...)).metodo(...)``."""

    def _servico(dia: date) -> ServicoPreco:
        return ServicoPreco(repositorio, repositorio_cliente, repositorio_item, hoje=lambda: dia)

    return _servico


@pytest.fixture
def cliente_id(repositorio_cliente: RepositorioClienteFalso) -> uuid.UUID:
    return repositorio_cliente.semear("Hotel Aurora").id


@pytest.fixture
def lencol(repositorio_item: RepositorioItemFalso, cliente_id: uuid.UUID) -> uuid.UUID:
    return repositorio_item.semear(cliente_id, "Lençol").id


@pytest.fixture
def fronha(repositorio_item: RepositorioItemFalso, cliente_id: uuid.UUID) -> uuid.UUID:
    return repositorio_item.semear(cliente_id, "Fronha").id


def _valor(servico: ServicoPreco, cliente_id: uuid.UUID, item_id: uuid.UUID, dia: date) -> Decimal:
    vigente = servico.resolver(cliente_id, [item_id], dia).vigentes.get(item_id)
    assert vigente is not None, f"sem preço em {dia}"
    return vigente.valor_unitario


class TestResolucaoPorData:
    """Req 1.1 e 1.3 — o preço vale do dia de início até a próxima alteração."""

    @pytest.fixture(autouse=True)
    def _historico(self, em, cliente_id: uuid.UUID, lencol: uuid.UUID) -> None:  # noqa: ANN001
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        em(DIA_DA_TROCA).mudar_a_partir_de_hoje(lencol, Decimal("4.80"))

    def test_vespera_da_troca_usa_o_preco_antigo(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        assert _valor(em(DIA_DA_TROCA), cliente_id, lencol, date(2026, 9, 9)) == Decimal("4.50")

    def test_dia_da_troca_usa_o_preco_novo(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        assert _valor(em(DIA_DA_TROCA), cliente_id, lencol, DIA_DA_TROCA) == Decimal("4.80")

    def test_dia_seguinte_usa_o_preco_novo(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        assert _valor(em(DIA_DA_TROCA), cliente_id, lencol, date(2026, 9, 11)) == Decimal("4.80")

    def test_preco_persiste_na_virada_do_mes_e_do_ano(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        servico = em(DIA_DA_TROCA)
        assert _valor(servico, cliente_id, lencol, date(2026, 10, 1)) == Decimal("4.80")
        assert _valor(servico, cliente_id, lencol, date(2027, 3, 20)) == Decimal("4.80")

    def test_pedido_retroativo_usa_o_preco_da_data_do_pedido(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        # alteração no dia 10; pedido do dia 5 lançado no dia 12
        servico = em(date(2026, 9, 12))
        assert _valor(servico, cliente_id, lencol, date(2026, 9, 5)) == Decimal("4.50")

    def test_informa_desde_quando_o_preco_vale(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        vigente = (
            em(DIA_DA_TROCA).resolver(cliente_id, [lencol], date(2026, 9, 20)).vigentes[lencol]
        )
        assert vigente.desde == DIA_DA_TROCA


class TestPrimeiroPrecoValeParaTras:
    """Req 1.7 — item novo pode entrar em pedido retroativo."""

    def test_primeiro_preco_vale_para_data_anterior_ao_cadastro(
        self,
        em,  # noqa: ANN001
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 10, 2)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))

        assert _valor(em(date(2026, 10, 2)), cliente_id, lencol, date(2026, 9, 1)) == Decimal(
            "4.50"
        )

    def test_so_o_primeiro_vale_para_tras_nao_o_mais_recente(
        self,
        em,  # noqa: ANN001
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        em(date(2026, 9, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.80"))

        # antes de junho: o primeiro (4.50), não o mais recente (4.80)
        assert _valor(em(date(2026, 9, 1)), cliente_id, lencol, date(2026, 1, 15)) == Decimal(
            "4.50"
        )


class TestItemSemPreco:
    """Só fica sem preço o item que nunca teve nenhum."""

    def test_item_sem_nenhum_preco(self, em, cliente_id, lencol) -> None:  # noqa: ANN001
        resolucao = em(date(2026, 9, 1)).resolver(cliente_id, [lencol], date(2026, 9, 1))

        assert resolucao.vigentes == {}
        assert resolucao.sem_preco == (lencol,)

    def test_separa_resolvidos_de_sem_preco_na_ordem_pedida(
        self,
        em,  # noqa: ANN001
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))

        resolucao = em(date(2026, 9, 1)).resolver(cliente_id, [fronha, lencol], date(2026, 9, 1))

        assert set(resolucao.vigentes) == {lencol}
        assert resolucao.sem_preco == (fronha,)

    def test_lista_vazia(self, em, cliente_id) -> None:  # noqa: ANN001
        resolucao = em(date(2026, 9, 1)).resolver(cliente_id, [], date(2026, 9, 1))
        assert resolucao.completa


class TestIsolamentoEntreClientes:
    def test_preco_de_um_cliente_nao_vale_para_outro(
        self,
        em,  # noqa: ANN001
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        outro = repositorio_cliente.semear("Clínica São Lucas").id
        lencol_outro = repositorio_item.semear(outro, "Lençol").id

        resolucao = em(date(2026, 9, 1)).resolver(outro, [lencol_outro], date(2026, 9, 1))

        assert resolucao.sem_preco == (lencol_outro,)


class TestMudarAPartirDeHoje:
    """Req 1.2 e 1.4."""

    def test_inicio_e_hoje_do_relogio_do_servico(self, em, lencol) -> None:  # noqa: ANN001
        preco = em(date(2026, 9, 17)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        assert preco.vigencia_inicio == date(2026, 9, 17)

    def test_duas_mudancas_no_mesmo_dia_viram_uma(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        lencol: uuid.UUID,
    ) -> None:
        servico = em(date(2026, 9, 17))
        primeiro = servico.mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        segundo = servico.mudar_a_partir_de_hoje(lencol, Decimal("4.70"))

        assert segundo is primeiro
        assert len(repositorio.registros) == 1
        assert segundo.valor_unitario == Decimal("4.70")

    def test_mudanca_em_outro_dia_cria_historico(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 9, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        em(date(2026, 9, 17)).mudar_a_partir_de_hoje(lencol, Decimal("4.80"))

        assert len(repositorio.registros) == 2

    def test_normaliza_para_duas_casas(self, em, lencol) -> None:  # noqa: ANN001
        preco = em(date(2026, 9, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.5"))
        assert str(preco.valor_unitario) == "4.50"

    @pytest.mark.parametrize("valor", ["0", "-1", "4.555"])
    def test_recusa_valor_invalido(self, em, lencol, valor: str) -> None:  # noqa: ANN001
        with pytest.raises(ErroDeDominio) as erro:
            em(date(2026, 9, 1)).mudar_a_partir_de_hoje(lencol, Decimal(valor))
        assert erro.value.codigo is CodigoErro.VALIDACAO

    def test_item_inexistente(self, em) -> None:  # noqa: ANN001
        with pytest.raises(ErroDeDominio) as erro:
            em(date(2026, 9, 1)).mudar_a_partir_de_hoje(uuid.uuid4(), Decimal("4.50"))
        assert erro.value.codigo is CodigoErro.NAO_ENCONTRADO


class TestCorrigirAtual:
    """Req 1.11 a 1.13 — erro de digitação, sem criar histórico."""

    def test_corrige_o_valor_desde_o_dia_em_que_foi_definido(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        em(DIA_DA_TROCA).mudar_a_partir_de_hoje(lencol, Decimal("0.48"))  # digitado errado

        corrigido = em(date(2026, 9, 12)).corrigir_atual(lencol, Decimal("4.80"))

        assert corrigido.vigencia_inicio == DIA_DA_TROCA
        assert len(repositorio.registros) == 2
        servico = em(date(2026, 9, 12))
        assert _valor(servico, cliente_id, lencol, DIA_DA_TROCA) == Decimal("4.80")
        # o preço anterior à troca não é tocado
        assert _valor(servico, cliente_id, lencol, date(2026, 9, 9)) == Decimal("4.50")

    def test_corrigir_sem_preco_e_recusado(self, em, lencol) -> None:  # noqa: ANN001
        with pytest.raises(ErroDeDominio) as erro:
            em(date(2026, 9, 1)).corrigir_atual(lencol, Decimal("4.50"))
        assert erro.value.codigo is CodigoErro.VALIDACAO

    def test_alterar_despacha_pelo_modo(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 9, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))

        em(date(2026, 9, 5)).alterar(lencol, Decimal("4.60"), ModoDeAlteracao.CORRIGIR_ATUAL)
        assert len(repositorio.registros) == 1

        em(date(2026, 9, 5)).alterar(lencol, Decimal("4.70"), ModoDeAlteracao.A_PARTIR_DE_HOJE)
        assert len(repositorio.registros) == 2


class TestImpacto:
    """Req 1.6 e 1.13 — quantos pedidos gravados mantêm o valor anterior."""

    @pytest.fixture(autouse=True)
    def _historico(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))
        em(DIA_DA_TROCA).mudar_a_partir_de_hoje(lencol, Decimal("0.48"))
        repositorio.semear_pedido(cliente_id, lencol, date(2026, 9, 5), "4.50")  # antes da troca
        repositorio.semear_pedido(cliente_id, lencol, date(2026, 9, 10), "0.48")
        repositorio.semear_pedido(cliente_id, lencol, date(2026, 9, 12), "0.48")

    def test_corrigir_conta_os_pedidos_do_periodo_do_preco_atual(self, em, lencol) -> None:  # noqa: ANN001
        quantidade = em(date(2026, 9, 12)).impacto(
            lencol, Decimal("4.80"), ModoDeAlteracao.CORRIGIR_ATUAL
        )
        assert quantidade == 2

    def test_mudar_a_partir_de_hoje_conta_so_de_hoje_em_diante(self, em, lencol) -> None:  # noqa: ANN001
        quantidade = em(date(2026, 9, 12)).impacto(
            lencol, Decimal("4.80"), ModoDeAlteracao.A_PARTIR_DE_HOJE
        )
        assert quantidade == 1

    def test_pedido_que_ja_tem_o_novo_valor_nao_conta(self, em, lencol) -> None:  # noqa: ANN001
        quantidade = em(date(2026, 9, 12)).impacto(
            lencol, Decimal("0.48"), ModoDeAlteracao.CORRIGIR_ATUAL
        )
        assert quantidade == 0

    def test_corrigir_o_primeiro_preco_alcanca_datas_anteriores(
        self,
        em,  # noqa: ANN001
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        em(date(2026, 9, 20)).mudar_a_partir_de_hoje(fronha, Decimal("3.50"))
        # pedido retroativo anterior ao primeiro preço, gravado com ele
        repositorio.semear_pedido(cliente_id, fronha, date(2026, 9, 1), "3.50")

        quantidade = em(date(2026, 9, 25)).impacto(
            fronha, Decimal("3.60"), ModoDeAlteracao.CORRIGIR_ATUAL
        )
        assert quantidade == 1

    def test_item_sem_preco_tem_impacto_zero(self, em, fronha) -> None:  # noqa: ANN001
        assert (
            em(date(2026, 9, 12)).impacto(fronha, Decimal("3.50"), ModoDeAlteracao.CORRIGIR_ATUAL)
            == 0
        )


class TestListagemNaData:
    def test_marca_item_sem_preco(
        self,
        em,  # noqa: ANN001
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        em(date(2026, 6, 1)).mudar_a_partir_de_hoje(lencol, Decimal("4.50"))

        linhas = em(date(2026, 9, 1)).listar_na_data(cliente_id, date(2026, 9, 1))
        por_id = {item.id: vigente for item, vigente in linhas}

        assert por_id[lencol] is not None
        assert por_id[lencol].valor_unitario == Decimal("4.50")
        assert por_id[fronha] is None

    def test_cliente_inexistente(self, em) -> None:  # noqa: ANN001
        with pytest.raises(ErroDeDominio) as erro:
            em(date(2026, 9, 1)).listar_na_data(uuid.uuid4(), date(2026, 9, 1))
        assert erro.value.codigo is CodigoErro.NAO_ENCONTRADO
