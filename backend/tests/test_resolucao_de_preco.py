"""Testes da resolução de preço vigente (tarefa 17).

Esta é a regra mais consequente do produto: dela sai o valor que será congelado no
lançamento e cobrado do cliente. Um erro aqui produz fatura errada sem que nada
pareça quebrado.

Rodam SEM banco, contra repositórios em memória. A equivalência entre a consulta
SQL e a versão em memória é verificada pelos testes de API, que usam Postgres.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.erros import CodigoErro, ErroDeDominio
from app.services.servico_preco import ServicoPreco
from tests.repositorios_falsos import (
    RepositorioClienteFalso,
    RepositorioItemFalso,
    RepositorioPrecoFalso,
)


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
def servico(
    repositorio: RepositorioPrecoFalso,
    repositorio_cliente: RepositorioClienteFalso,
    repositorio_item: RepositorioItemFalso,
) -> ServicoPreco:
    return ServicoPreco(repositorio, repositorio_cliente, repositorio_item)


@pytest.fixture
def cliente_id(repositorio_cliente: RepositorioClienteFalso) -> uuid.UUID:
    return repositorio_cliente.semear("Hotel Aurora").id


@pytest.fixture
def lencol(repositorio_item: RepositorioItemFalso, cliente_id: uuid.UUID) -> uuid.UUID:
    return repositorio_item.semear(cliente_id, "Lençol").id


@pytest.fixture
def fronha(repositorio_item: RepositorioItemFalso, cliente_id: uuid.UUID) -> uuid.UUID:
    return repositorio_item.semear(cliente_id, "Fronha").id


class TestPropagacaoDaVigencia:
    """Req 4.4 — o preço vale do mês definido em diante, até que outro exista."""

    def test_vale_no_proprio_mes(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 6, 15))

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("4.50")
        assert vigente.vigencia_origem == date(2026, 6, 1)

    @pytest.mark.parametrize(
        "data_consulta",
        [date(2026, 7, 1), date(2026, 9, 15), date(2026, 12, 31), date(2027, 3, 10)],
    )
    def test_propaga_para_meses_seguintes(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        data_consulta: date,
    ) -> None:
        """Sem redigitação na virada do mês, inclusive atravessando o ano."""
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        vigente = servico.resolver_um(cliente_id, lencol, data_consulta)

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("4.50")
        assert vigente.vigencia_origem == date(2026, 6, 1)

    def test_mes_com_vigencia_propria_sobrepoe(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")
        repositorio.semear(cliente_id, lencol, date(2026, 10, 1), "4.80")

        setembro = servico.resolver_um(cliente_id, lencol, date(2026, 9, 30))
        outubro = servico.resolver_um(cliente_id, lencol, date(2026, 10, 1))

        assert setembro is not None and setembro.valor_unitario == Decimal("4.50")
        assert outubro is not None and outubro.valor_unitario == Decimal("4.80")

    def test_vence_o_mais_recente_entre_varios(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        for mes, valor in ((1, "3.00"), (4, "3.50"), (8, "4.00")):
            repositorio.semear(cliente_id, lencol, date(2026, mes, 1), valor)

        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 6, 10))

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("3.50")
        assert vigente.vigencia_origem == date(2026, 4, 1)

    def test_preco_futuro_nao_vale_antes_da_vigencia(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Preço programado para novembro não afeta setembro (Req 4.14)."""
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")
        repositorio.semear(cliente_id, lencol, date(2026, 11, 1), "5.20")

        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 9, 1))

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("4.50")


class TestFronteirasDoMes:
    """Qualquer dia do mês resolve o mesmo preço — a vigência é mensal."""

    @pytest.mark.parametrize("dia", [1, 2, 15, 28, 30])
    def test_todos_os_dias_do_mes_resolvem_igual(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        dia: int,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 9, 1), "4.75")

        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 9, dia))

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("4.75")

    def test_ultimo_dia_do_mes_nao_pega_o_mes_seguinte(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """A fronteira mais perigosa: 31/08 deve usar agosto, não setembro."""
        repositorio.semear(cliente_id, lencol, date(2026, 8, 1), "4.00")
        repositorio.semear(cliente_id, lencol, date(2026, 9, 1), "4.60")

        ultimo_de_agosto = servico.resolver_um(cliente_id, lencol, date(2026, 8, 31))
        primeiro_de_setembro = servico.resolver_um(cliente_id, lencol, date(2026, 9, 1))

        assert ultimo_de_agosto is not None
        assert ultimo_de_agosto.valor_unitario == Decimal("4.00")
        assert primeiro_de_setembro is not None
        assert primeiro_de_setembro.valor_unitario == Decimal("4.60")

    def test_virada_de_ano(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 12, 1), "5.00")
        repositorio.semear(cliente_id, lencol, date(2027, 1, 1), "5.50")

        dezembro = servico.resolver_um(cliente_id, lencol, date(2026, 12, 31))
        janeiro = servico.resolver_um(cliente_id, lencol, date(2027, 1, 1))

        assert dezembro is not None and dezembro.valor_unitario == Decimal("5.00")
        assert janeiro is not None and janeiro.valor_unitario == Decimal("5.50")


class TestLancamentoRetroativo:
    """Req 4.7 — resolve pela data do pedido, nunca pela data corrente."""

    def test_usa_o_preco_do_mes_do_pedido(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Pedido de agosto registrado em outubro recebe o preço de agosto."""
        repositorio.semear(cliente_id, lencol, date(2026, 8, 1), "4.00")
        repositorio.semear(cliente_id, lencol, date(2026, 10, 1), "4.80")

        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 8, 28))

        assert vigente is not None
        assert vigente.valor_unitario == Decimal("4.00")

    def test_sem_preco_anterior_ao_pedido(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Pedido de maio, primeiro preço em junho: não há valor aplicável."""
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        resolucao = servico.resolver(cliente_id, [lencol], date(2026, 5, 10))

        assert resolucao.vigentes == {}
        assert resolucao.sem_preco == (lencol,)
        assert resolucao.completa is False


class TestItemSemPreco:
    """Req 4.8 — ausência é reportada, nunca tratada como zero."""

    def test_item_sem_nenhum_preco(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        resolucao = servico.resolver(cliente_id, [lencol], date(2026, 9, 1))

        assert resolucao.sem_preco == (lencol,)
        assert lencol not in resolucao.vigentes

    def test_separa_resolvidos_de_faltantes(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        resolucao = servico.resolver(cliente_id, [lencol, fronha], date(2026, 9, 1))

        assert set(resolucao.vigentes) == {lencol}
        assert resolucao.sem_preco == (fronha,)

    def test_preserva_a_ordem_pedida_nos_faltantes(
        self,
        servico: ServicoPreco,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        """Ordem previsível torna a mensagem de erro estável."""
        resolucao = servico.resolver(cliente_id, [fronha, lencol], date(2026, 9, 1))

        assert resolucao.sem_preco == (fronha, lencol)

    def test_lista_vazia_de_itens(self, servico: ServicoPreco, cliente_id: uuid.UUID) -> None:
        resolucao = servico.resolver(cliente_id, [], date(2026, 9, 1))

        assert resolucao.vigentes == {}
        assert resolucao.sem_preco == ()
        assert resolucao.completa is True


class TestIsolamentoEntreClientes:
    def test_preco_de_um_cliente_nao_vale_para_outro(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")
        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        lencol_da_pousada = repositorio_item.semear(outro, "Lençol").id

        resolucao = servico.resolver(outro, [lencol_da_pousada], date(2026, 9, 1))

        assert resolucao.sem_preco == (lencol_da_pousada,)


class TestDefinicaoDePreco:
    def test_define_primeiro_preco(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        preco = servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal("4.50"))

        assert preco.valor_unitario == Decimal("4.50")
        assert preco.vigencia_mes == date(2026, 6, 1)

    def test_normaliza_a_vigencia_para_o_dia_primeiro(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Qualquer dia informado vira o dia 1 (o banco exige isso)."""
        preco = servico.definir(cliente_id, lencol, date(2026, 6, 23), Decimal("4.50"))

        assert preco.vigencia_mes == date(2026, 6, 1)

    def test_repetir_o_mesmo_mes_atualiza(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Req 4.2 — não cria duplicata."""
        servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal("4.50"))
        servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal("5.00"))

        assert len(repositorio.registros) == 1
        vigente = servico.resolver_um(cliente_id, lencol, date(2026, 6, 1))
        assert vigente is not None
        assert vigente.valor_unitario == Decimal("5.00")

    def test_normaliza_para_duas_casas(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        preco = servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal("4.5"))

        assert preco.valor_unitario == Decimal("4.50")

    @pytest.mark.parametrize("valor", ["0", "-1.00", "-0.01"])
    def test_recusa_valor_nao_positivo(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID, valor: str
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal(valor))

        assert excecao.value.codigo == CodigoErro.VALIDACAO
        assert excecao.value.detalhes["campos"] == ["valor_unitario"]

    @pytest.mark.parametrize("valor", ["4.555", "0.001", "1.2345"])
    def test_recusa_mais_de_duas_casas(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID, valor: str
    ) -> None:
        """Req 4.13 — sem fração de centavo."""
        with pytest.raises(ErroDeDominio) as excecao:
            servico.definir(cliente_id, lencol, date(2026, 6, 1), Decimal(valor))

        assert "duas casas" in excecao.value.mensagem

    def test_permite_corrigir_mes_passado(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Req 4.17 — correção de erro de digitação é permitida."""
        servico.definir(cliente_id, lencol, date(2026, 1, 1), Decimal("2.05"))

        corrigido = servico.definir(cliente_id, lencol, date(2026, 1, 1), Decimal("2.50"))

        assert corrigido.valor_unitario == Decimal("2.50")

    def test_recusa_item_de_outro_cliente(
        self,
        servico: ServicoPreco,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        item_do_outro = repositorio_item.semear(outro, "Toalha").id

        with pytest.raises(ErroDeDominio) as excecao:
            servico.definir(cliente_id, item_do_outro, date(2026, 6, 1), Decimal("4.50"))

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO

    def test_recusa_cliente_inexistente(self, servico: ServicoPreco, lencol: uuid.UUID) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.definir(uuid.uuid4(), lencol, date(2026, 6, 1), Decimal("4.50"))

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO


class TestVigenciaSugerida:
    """Decisão 18 — o padrão difere entre primeiro preço e alteração."""

    def test_primeiro_preco_sugere_mes_corrente(
        self, servico: ServicoPreco, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Senão o item recém-cadastrado não poderia ser lançado hoje."""
        sugestao = servico.vigencia_sugerida(cliente_id, lencol, date(2026, 9, 18))

        assert sugestao.vigencia_mes == date(2026, 9, 1)
        assert sugestao.e_primeiro_preco is True

    def test_alteracao_sugere_mes_seguinte(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Alteração no meio do mês só passa a valer no mês seguinte."""
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        sugestao = servico.vigencia_sugerida(cliente_id, lencol, date(2026, 9, 18))

        assert sugestao.vigencia_mes == date(2026, 10, 1)
        assert sugestao.e_primeiro_preco is False

    def test_alteracao_em_dezembro_sugere_janeiro_do_ano_seguinte(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        sugestao = servico.vigencia_sugerida(cliente_id, lencol, date(2026, 12, 20))

        assert sugestao.vigencia_mes == date(2027, 1, 1)

    def test_recusa_item_de_outro_cliente(
        self,
        servico: ServicoPreco,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        item_do_outro = repositorio_item.semear(outro, "Toalha").id

        with pytest.raises(ErroDeDominio) as excecao:
            servico.vigencia_sugerida(cliente_id, item_do_outro, date(2026, 9, 18))

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO


class TestListagemDoMes:
    def test_marca_itens_sem_preco(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        listagem = servico.listar_do_mes(cliente_id, date(2026, 9, 1))

        por_nome = {nome: vigente for _, nome, vigente in listagem}
        assert por_nome["Lençol"] is not None
        assert por_nome["Fronha"] is None

    def test_expoe_a_origem_da_vigencia(
        self,
        servico: ServicoPreco,
        repositorio: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Transparência: o operador vê que o preço de setembro veio de junho."""
        repositorio.semear(cliente_id, lencol, date(2026, 6, 1), "4.50")

        listagem = servico.listar_do_mes(cliente_id, date(2026, 9, 1))
        vigente = next(v for _, nome, v in listagem if nome == "Lençol")

        assert vigente is not None
        assert vigente.vigencia_origem == date(2026, 6, 1)
