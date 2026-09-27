"""Testes do congelamento de valor e do cálculo (tarefa 26, parte 1).

Esta é a verificação mais consequente do sistema. O congelamento é o que torna a
cobrança defensável: o relatório que o cliente recebeu não pode mudar depois.

Rodam sem banco. As constraints de unicidade têm verificação própria contra
Postgres em ``test_constraints.py``.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.datas import hoje_sp
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

# data passada e estável, para não depender do dia em que o teste roda
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


@pytest.fixture
def sem_preco(repositorio_item: RepositorioItemFalso, cliente_id: uuid.UUID) -> uuid.UUID:
    """Item cadastrado no catálogo, mas sem preço definido."""
    return repositorio_item.semear(cliente_id, "Roupão").id


class TestCongelamentoNaCriacao:
    """Req 6.1 — o valor vigente é gravado na linha no momento da criação."""

    def test_grava_o_preco_vigente_do_mes_da_data(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)], "1201")

        linhas = repositorio.linhas[lancamento.id]
        assert len(linhas) == 1
        assert linhas[0].valor_unitario_congelado == Decimal("4.50")

    def test_alterar_o_preco_depois_nao_muda_o_lancamento(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Req 6.2 — o teste central do produto.

        Um relatório já enviado ao cliente não pode exibir outro total depois.
        """
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])
        total_original = repositorio.linhas[lancamento.id][0].total

        # preço sobe depois, com vigência retroativa ao próprio mês do pedido
        repositorio_preco.semear(cliente_id, lencol, MES_DO_PEDIDO, "9.99")

        linha = repositorio.linhas[lancamento.id][0]
        assert linha.valor_unitario_congelado == Decimal("4.50")
        assert linha.total == total_original == Decimal("180.00")

    def test_usa_o_preco_propagado_de_mes_anterior(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Preço definido em junho, pedido em setembro."""
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert repositorio.linhas[lancamento.id][0].valor_unitario_congelado == Decimal("4.50")

    def test_lancamento_retroativo_usa_o_mes_do_pedido(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        """Req 4.7 — resolve pela data do pedido, não pela data corrente."""
        # preço mudou em setembro; o pedido é de agosto
        repositorio_preco.semear(cliente_id, lencol, date(2026, 9, 1), "4.80")

        lancamento = servico.criar(cliente_id, date(2026, 8, 28), [LinhaSolicitada(lencol, 10)])

        assert repositorio.linhas[lancamento.id][0].valor_unitario_congelado == Decimal("4.50")


class TestCalculoDeTotais:
    """Req 6.4 a 6.6 — total da linha, total de peças e total em R$."""

    def test_total_da_linha_e_valor_vezes_quantidade(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 40)])

        assert repositorio.linhas[lancamento.id][0].total == Decimal("180.00")

    def test_totais_de_multiplas_linhas(
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

        linhas = repositorio.linhas[lancamento.id]
        # 40 × 4,50 = 180,00 ; 30 × 3,50 = 105,00
        assert sum(linha.quantidade for linha in linhas) == 70
        assert sum((linha.total for linha in linhas), Decimal("0")) == Decimal("285.00")

    def test_calculo_nao_produz_arredondamento(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Preço com duas casas × inteiro é exato: sem dízima em ponto algum.

        Verificamos o expoente do Decimal, não só o valor: um resultado com mais
        de duas casas indicaria que a cadeia deixou de ser exata.
        """
        calculo = servico._resolver_e_calcular(  # noqa: SLF001
            cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 7)]
        )

        total = calculo.linhas[0].total
        assert total == Decimal("31.50")
        assert total.as_tuple().exponent >= -2

    @pytest.mark.parametrize(
        ("quantidade", "esperado"),
        [(1, "4.50"), (3, "13.50"), (7, "31.50"), (100, "450.00"), (999, "4495.50")],
    )
    def test_exatidao_em_varias_quantidades(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        quantidade: int,
        esperado: str,
    ) -> None:
        calculo = servico._resolver_e_calcular(  # noqa: SLF001
            cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, quantidade)]
        )

        assert calculo.linhas[0].total == Decimal(esperado)

    def test_totais_do_calculo_batem_com_as_linhas(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        fronha: uuid.UUID,
    ) -> None:
        """Os totais agregados não podem divergir da soma das linhas."""
        calculo = servico._resolver_e_calcular(  # noqa: SLF001
            cliente_id,
            DATA_PEDIDO,
            [LinhaSolicitada(lencol, 12), LinhaSolicitada(fronha, 8)],
        )

        assert calculo.total_pecas == sum(linha.quantidade for linha in calculo.linhas)
        assert calculo.total_valor == sum(
            (linha.total for linha in calculo.linhas), Decimal("0.00")
        )


class TestItemSemPreco:
    """Req 5.14 — recusa nomeando os itens, sem valor zero implícito."""

    def test_recusa_o_lancamento(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        sem_preco: uuid.UUID,
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(
                cliente_id,
                DATA_PEDIDO,
                [LinhaSolicitada(lencol, 10), LinhaSolicitada(sem_preco, 5)],
            )

        assert excecao.value.codigo == CodigoErro.ITENS_SEM_PRECO

    def test_mensagem_nomeia_o_item_e_o_mes(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        sem_preco: uuid.UUID,
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(sem_preco, 5)])

        assert "Roupão" in excecao.value.mensagem
        assert "setembro/2026" in excecao.value.mensagem
        assert excecao.value.detalhes["itens"] == ["Roupão"]

    def test_nada_e_gravado(
        self,
        servico: ServicoLancamento,
        repositorio: RepositorioLancamentoFalso,
        cliente_id: uuid.UUID,
        sem_preco: uuid.UUID,
    ) -> None:
        with pytest.raises(ErroDeDominio):
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(sem_preco, 5)])

        assert repositorio.registros == {}

    def test_preco_existe_mas_e_posterior_ao_pedido(
        self,
        servico: ServicoLancamento,
        repositorio_preco: RepositorioPrecoFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Preço só a partir de outubro; pedido de setembro fica sem valor."""
        item = repositorio_item.semear(cliente_id, "Tapete")
        repositorio_preco.semear(cliente_id, item.id, date(2026, 10, 1), "8.00")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(item.id, 2)])

        assert excecao.value.codigo == CodigoErro.ITENS_SEM_PRECO


class TestValidacoesDeEntrada:
    def test_recusa_data_futura(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Req 5.15 — o serviço é registrado depois de ocorrer."""
        amanha = hoje_sp() + timedelta(days=1)

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, amanha, [LinhaSolicitada(lencol, 10)])

        assert excecao.value.codigo == CodigoErro.DATA_FUTURA

    def test_aceita_hoje(
        self,
        servico: ServicoLancamento,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        hoje = hoje_sp()
        repositorio_preco.semear(cliente_id, lencol, hoje.replace(day=1), "4.50")

        lancamento = servico.criar(cliente_id, hoje, [LinhaSolicitada(lencol, 10)])

        assert lancamento.data == hoje

    def test_recusa_lancamento_sem_linhas(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [])

        assert excecao.value.codigo == CodigoErro.VALIDACAO

    @pytest.mark.parametrize("quantidade", [0, -1, -50])
    def test_recusa_quantidade_nao_positiva(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        quantidade: int,
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, quantidade)])

        assert excecao.value.codigo == CodigoErro.VALIDACAO

    def test_recusa_item_repetido(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(
                cliente_id,
                DATA_PEDIDO,
                [LinhaSolicitada(lencol, 10), LinhaSolicitada(lencol, 5)],
            )

        assert excecao.value.codigo == CodigoErro.ITEM_DUPLICADO_NO_LANCAMENTO
        assert "Lençol" in excecao.value.mensagem

    def test_recusa_item_de_outro_cliente(
        self,
        servico: ServicoLancamento,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        item_do_outro = repositorio_item.semear(outro, "Toalha").id

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(item_do_outro, 5)])

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO

    def test_recusa_cliente_inexistente(
        self, servico: ServicoLancamento, lencol: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(uuid.uuid4(), DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert excecao.value.codigo == CodigoErro.NAO_ENCONTRADO


class TestComanda:
    def test_aceita_lancamento_sem_comanda(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        assert lancamento.comanda is None

    def test_remove_espacos_nas_pontas(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        lancamento = servico.criar(
            cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)], "  1201  "
        )

        assert lancamento.comanda == "1201"

    @pytest.mark.parametrize("entrada", ["", "   ", "\t"])
    def test_comanda_em_branco_vira_nula(
        self,
        servico: ServicoLancamento,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
        entrada: str,
    ) -> None:
        """Texto vazio colidiria com outro texto vazio no índice único."""
        lancamento = servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)], entrada)

        assert lancamento.comanda is None

    def test_recusa_comanda_repetida_no_mesmo_cliente(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)], "1201")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, date(2026, 9, 11), [LinhaSolicitada(lencol, 5)], "1201")

        assert excecao.value.codigo == CodigoErro.COMANDA_DUPLICADA

    def test_recusa_comanda_que_difere_apenas_na_caixa(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)], "A100")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, date(2026, 9, 11), [LinhaSolicitada(lencol, 5)], "a100")

        assert excecao.value.codigo == CodigoErro.COMANDA_DUPLICADA

    def test_permite_varios_lancamentos_sem_comanda(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])
        segundo = servico.criar(cliente_id, date(2026, 9, 11), [LinhaSolicitada(lencol, 5)])

        assert segundo.comanda is None


class TestUnicidadeClienteData:
    def test_recusa_segundo_lancamento_na_mesma_data(
        self, servico: ServicoLancamento, cliente_id: uuid.UUID, lencol: uuid.UUID
    ) -> None:
        """Req 5.2 — cada empresa faz um pedido por dia."""
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 5)])

        assert excecao.value.codigo == CodigoErro.LANCAMENTO_DUPLICADO
        assert "10/09/2026" in excecao.value.mensagem

    def test_aceita_clientes_diferentes_na_mesma_data(
        self,
        servico: ServicoLancamento,
        repositorio_cliente: RepositorioClienteFalso,
        repositorio_item: RepositorioItemFalso,
        repositorio_preco: RepositorioPrecoFalso,
        cliente_id: uuid.UUID,
        lencol: uuid.UUID,
    ) -> None:
        servico.criar(cliente_id, DATA_PEDIDO, [LinhaSolicitada(lencol, 10)])

        outro = repositorio_cliente.semear("Pousada Vista Verde").id
        item = repositorio_item.semear(outro, "Toalha")
        repositorio_preco.semear(outro, item.id, date(2026, 6, 1), "6.00")

        lancamento = servico.criar(outro, DATA_PEDIDO, [LinhaSolicitada(item.id, 3)])

        assert lancamento.data == DATA_PEDIDO
