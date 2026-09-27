"""Testes de edição, exclusão e prévia de lançamento (tarefas 23 a 25 e 26).

O teste mais importante deste arquivo é
``test_previa_e_salvamento_produzem_os_mesmos_totais``: ele impede que a prévia e
o valor efetivamente cobrado divirjam. Se alguém duplicar a lógica de cálculo, ele
quebra.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.erros import CodigoErro, ErroDeDominio
from app.dominio import LinhaSolicitada
from app.services.servico_lancamento import ServicoLancamento
from app.services.servico_preco import ServicoPreco
from tests.repositorios_falsos import (
    RepositorioClienteFalso,
    RepositorioItemFalso,
    RepositorioLancamentoFalso,
    RepositorioPrecoFalso,
)

DATA_PEDIDO = date(2026, 9, 10)
MES_DO_PEDIDO = date(2026, 9, 1)


@pytest.fixture
def repositorio_cliente() -> RepositorioClienteFalso:
    return RepositorioClienteFalso()


@pytest.fixture
def repositorio_item() -> RepositorioItemFalso:
    return RepositorioItemFalso()


@pytest.fixture
def repositorio_preco() -> RepositorioPrecoFalso:
    return RepositorioPrecoFalso()


@pytest.fixture
def repositorio() -> RepositorioLancamentoFalso:
    return RepositorioLancamentoFalso()


@pytest.fixture
def servico(
    repositorio: RepositorioLancamentoFalso,
    repositorio_cliente: RepositorioClienteFalso,
    repositorio_item: RepositorioItemFalso,
    repositorio_preco: RepositorioPrecoFalso,
) -> ServicoLancamento:
    servico_preco = ServicoPreco(repositorio_preco, repositorio_cliente, repositorio_item)
    return ServicoLancamento(repositorio, repositorio_cliente, repositorio_item, servico_preco)


@pytest.fixture
def cliente_id(repositorio_cliente: RepositorioClienteFalso) -> uuid.UUID:
    return repositorio_cliente.semear("Hotel Aurora").id


@pytest.fixture
def lencol(
    repositorio_item: RepositorioItemFalso,
    repositorio_preco: RepositorioPrecoFalso,
    cliente_id: uuid.UUID,
) -> uuid.UUID:
    item = repositorio_item.semear(cliente_id, "Lençol")
    repositorio_preco.semear(cliente_id, item.id, date(2026, 6, 1), "4.50")
    return item.id


@pytest.fixture
def fronha(
    repositorio_item: RepositorioItemFalso,
    repositorio_preco: RepositorioPrecoFalso,
    cliente_id: uuid.UUID,
) -> uuid.UUID:
    item = repositorio_item.semear(cliente_id, "Fronha")
    repositorio_preco.semear(cliente_id, item.id, date(2026, 6, 1), "3.50")
    return item.id


def linhas_de(repositorio: RepositorioLancamentoFalso, lancamento_id: uuid.UUID) -> dict:
    return {linha.item_id: linha for linha in repositorio.linhas[lancamento_id]}


class TestEdicaoPreservaCongelamento:
    """Req 5.18 e 6.3 — a edição corrige o registro, não renegocia o preço."""

    def test_alterar_quantidade_mantem_o_valor_congelado(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        # preço sobe, com vigência no próprio mês do pedido
        repositorio_preco.semear(cliente_id, lencol, MES_DO_PEDIDO, "9.99")

        servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 50)])

        linha = linhas_de(repositorio, lancamento.id)[lencol]
        assert linha.valor_unitario_congelado == Decimal("4.50")
        assert linha.quantidade == 50

    def test_recalcula_apenas_o_total_pela_nova_quantidade(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        linha = linhas_de(repositorio, lancamento.id)[lencol]
        assert linha.total == Decimal("45.00")

    def test_linha_nova_usa_o_mes_da_data_do_lancamento(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        repositorio_preco: RepositorioPrecoFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Req 5.19 — o detalhe mais fácil de errar.

        Pedido de agosto editado depois: a linha nova recebe preço de agosto, não
        do mês em que a edição acontece.
        """
        data_agosto = date(2026, 8, 28)
        toalha = repositorio_item.semear(cliente_id, "Toalha")
        repositorio_preco.semear(cliente_id, toalha.id, date(2026, 8, 1), "6.00")
        # preço da toalha muda em setembro e outubro
        repositorio_preco.semear(cliente_id, toalha.id, date(2026, 9, 1), "7.00")
        repositorio_preco.semear(cliente_id, toalha.id, date(2026, 10, 1), "8.00")

        lancamento = servico.criar(cliente_id, data_agosto, [LinhaSolicitada(lencol, 10)])
        servico.editar(
            lancamento.id,
            data_agosto,
            [LinhaSolicitada(lencol, 10), LinhaSolicitada(toalha.id, 5)],
        )

        linha_nova = linhas_de(repositorio, lancamento.id)[toalha.id]
        assert linha_nova.valor_unitario_congelado == Decimal("6.00")

    def test_remove_linha(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(
            cliente_id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 40), LinhaSolicitada(fronha, 30)],
        )

        servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        linhas = linhas_de(repositorio, lancamento.id)
        assert set(linhas) == {lencol}

    def test_mantem_congelado_ao_adicionar_e_remover_na_mesma_edicao(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])
        repositorio_preco.semear(cliente_id, lencol, MES_DO_PEDIDO, "9.99")

        servico.editar(
            lancamento.id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 40), LinhaSolicitada(fronha, 20)],
        )

        linhas = linhas_de(repositorio, lancamento.id)
        assert linhas[lencol].valor_unitario_congelado == Decimal("4.50")
        assert linhas[fronha].valor_unitario_congelado == Decimal("3.50")

    def test_edicao_sem_alterar_nada_e_idempotente(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")

        servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")

        linhas = linhas_de(repositorio, lancamento.id)
        assert len(linhas) == 1
        assert linhas[lencol].valor_unitario_congelado == Decimal("4.50")
        assert linhas[lencol].quantidade == 40


class TestEdicaoRevalidaUnicidade:
    """Req 5.20 — alterar data ou cliente exige revalidar."""

    def test_permite_salvar_sem_alterar_a_data(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Não pode acusar conflito com o próprio registro."""
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        editado = servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 41)])

        assert editado.data == DATA_PEDIDO

    def test_recusa_mover_para_data_ja_ocupada(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        primeiro = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])
        servico.criar(cliente_id, date(2026, 9, 11), [LinhaSolicitada(lencol, 10)])

        with pytest.raises(ErroDeDominio) as excecao:
            servico.editar(primeiro.id, date(2026, 9, 11), [LinhaSolicitada(lencol, 40)])

        assert excecao.value.codigo == CodigoErro.LANCAMENTO_DUPLICADO

    def test_permite_mover_para_data_livre(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        editado = servico.editar(lancamento.id, date(2026, 9, 12), [LinhaSolicitada(lencol, 40)])

        assert editado.data == date(2026, 9, 12)

    def test_permite_manter_a_propria_comanda(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")

        editado = servico.editar(lancamento.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")

        assert editado.comanda == "1201"

    def test_recusa_comanda_de_outro_lancamento(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        primeiro = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")
        servico.criar(cliente_id, date(2026, 9, 11), [LinhaSolicitada(lencol, 10)], "1202")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.editar(primeiro.id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1202")

        assert excecao.value.codigo == CodigoErro.COMANDA_DUPLICADA

    def test_recusa_data_futura_na_edicao(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        from datetime import timedelta

        from app.core.datas import hoje_sp

        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        with pytest.raises(ErroDeDominio) as excecao:
            servico.editar(
                lancamento.id, hoje_sp() + timedelta(days=1), [LinhaSolicitada(lencol, 40)]
            )

        assert excecao.value.codigo == CodigoErro.DATA_FUTURA

    def test_404_para_lancamento_inexistente(
        self, servico: ServicoLancamento, lencol: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.editar(uuid.uuid4(), DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO


class TestExclusao:
    def test_exclui_o_lancamento(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        servico.excluir(lancamento.id)

        assert repositorio.registros == {}

    def test_exclui_as_linhas_em_cascata(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        """Req 5.23 — o registro deixa de compor relatórios do período."""
        lancamento = servico.criar(
            cliente_id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 40), LinhaSolicitada(fronha, 30)],
        )

        servico.excluir(lancamento.id)

        assert repositorio.linhas.get(lancamento.id) is None

    def test_libera_a_data_para_novo_lancamento(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])
        servico.excluir(lancamento.id)

        novo = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert novo.data == DATA_PEDIDO

    def test_404_para_lancamento_inexistente(self, servico: ServicoLancamento) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.excluir(uuid.uuid4())

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO


class TestPrevia:
    def test_calcula_totais_sem_persistir(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        calculo = servico.calcular_previa(
            cliente_id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 40), LinhaSolicitada(fronha, 30)],
        )

        assert calculo.total_pecas == 70
        assert calculo.total_valor == Decimal("285.00")
        assert repositorio.registros == {}

    def test_previa_e_salvamento_produzem_os_mesmos_totais(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        """O teste que impede prévia e cobrança de divergirem.

        Se alguém duplicar a lógica de cálculo, este teste quebra.
        """
        solicitadas = [LinhaSolicitada(lencol, 37), LinhaSolicitada(fronha, 23)]

        previa = servico.calcular_previa(cliente_id, DATA_PEDIDO, solicitadas)
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, solicitadas)

        linhas = repositorio.linhas[lancamento.id]
        assert sum(linha.quantidade for linha in linhas) == previa.total_pecas
        assert sum((linha.total for linha in linhas), Decimal("0.00")) == previa.total_valor

        # e linha por linha, não só no agregado
        por_item = {linha.item_id: linha for linha in linhas}
        for calculada in previa.linhas:
            gravada = por_item[calculada.item_id]
            assert gravada.valor_unitario_congelado == calculada.valor_unitario
            assert gravada.total == calculada.total

    def test_nao_falha_por_item_sem_preco(
        self,
        servico: ServicoLancamento,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Erro no meio da digitação seria hostil; a tela avisa em linha."""
        roupao = repositorio_item.semear(cliente_id, "Roupão").id

        calculo = servico.calcular_previa(
            cliente_id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 40), LinhaSolicitada(roupao, 5)],
        )

        assert calculo.itens_sem_preco == (roupao,)
        assert calculo.completo is False
        # o total considera apenas o item com preço
        assert calculo.total_valor == Decimal("180.00")
        assert calculo.total_pecas == 40

    def test_salvar_a_mesma_entrada_e_recusado(
        self,
        servico: ServicoLancamento,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """A prévia tolera; o salvamento recusa. As duas coisas ao mesmo tempo."""
        roupao = repositorio_item.semear(cliente_id, "Roupão").id
        solicitadas = [LinhaSolicitada(lencol, 40), LinhaSolicitada(roupao, 5)]

        previa = servico.calcular_previa(cliente_id, DATA_PEDIDO, solicitadas)
        assert previa.itens_sem_preco == (roupao,)

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, solicitadas)

        assert excecao.value.codigo == CodigoErro.ITENS_SEM_PRECO

    def test_nao_valida_unicidade_de_data(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Prévia trata de valor; conflito é assunto do salvamento."""
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        calculo = servico.calcular_previa(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert calculo.total_valor == Decimal("45.00")

    def test_nao_valida_data_futura(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        from datetime import timedelta

        from app.core.datas import hoje_sp

        amanha = hoje_sp() + timedelta(days=1)

        calculo = servico.calcular_previa(cliente_id, amanha, [LinhaSolicitada(lencol, 2)])

        assert calculo.total_pecas == 2

    def test_recusa_item_de_outro_cliente(
        self,
        servico: ServicoLancamento,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Validação que a prévia mantém: item precisa ser do cliente."""
        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        item_do_outro = repositorio_item.semear(outro, "Toalha").id

        with pytest.raises(ErroDeDominio) as excecao:
            servico.calcular_previa(cliente_id, DATA_PEDIDO, [LinhaSolicitada(item_do_outro, 5)])

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO

    def test_recusa_item_repetido(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.calcular_previa(
                cliente_id,
                DATA_PEDIDO,
                [LinhaSolicitada(lencol, 10), LinhaSolicitada(lencol, 5)],
            )

        assert excecao.value.codigo == CodigoErro.ITEM_DUPLICADO_NO_LANCAMENTO
