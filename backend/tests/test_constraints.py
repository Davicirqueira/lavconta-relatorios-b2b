"""Testes das constraints de banco (tarefa 9).

Verificam COMPORTAMENTO, não texto de DDL: cada teste tenta violar uma regra e
exige que o banco recuse. Comparar definição de índice por string é frágil — o
Postgres normaliza expressões (``lower(btrim((comanda)::text))``) e a asserção
quebra por formatação, não por defeito real.

Exigem Postgres real: índice único parcial, índice sobre expressão e coluna
gerada não existem em SQLite.
"""

from decimal import Decimal

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError, IntegrityError

from tests.conftest import criar_cliente, criar_item, criar_lancamento


def executar(conexao: Connection, sql: str, **parametros: object) -> None:
    """Executa em SAVEPOINT, para que a falha esperada não aborte a transação."""
    ponto = conexao.begin_nested()
    try:
        conexao.execute(text(sql), parametros)
        ponto.commit()
    except Exception:
        ponto.rollback()
        raise


class TestClienteNomeUnico:
    """Req 2.5 — nome único ignorando caixa e espaços nas pontas."""

    def test_recusa_nome_com_caixa_diferente(self, conexao: Connection) -> None:
        criar_cliente(conexao, "Hotel Aurora")

        with pytest.raises(IntegrityError):
            executar(conexao, "insert into clientes (nome) values ('hotel aurora')")

    def test_recusa_nome_com_espacos_nas_pontas(self, conexao: Connection) -> None:
        criar_cliente(conexao, "Hotel Aurora")

        with pytest.raises(IntegrityError):
            executar(conexao, "insert into clientes (nome) values ('  Hotel Aurora  ')")

    def test_recusa_nome_vazio(self, conexao: Connection) -> None:
        with pytest.raises(IntegrityError):
            executar(conexao, "insert into clientes (nome) values ('   ')")

    def test_aceita_nomes_diferentes(self, conexao: Connection) -> None:
        criar_cliente(conexao, "Hotel Aurora")
        criar_cliente(conexao, "Restaurante Bom Prato")

        total = conexao.execute(text("select count(*) from clientes")).scalar_one()
        assert total == 2


class TestItemNomeUnicoPorCliente:
    """Req 3.2 — nome único por cliente, não globalmente."""

    def test_recusa_item_repetido_no_mesmo_cliente(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_item(conexao, cliente, "Lençol")

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into itens (cliente_id, nome) values (:c, 'lençol')",
                c=cliente,
            )

    def test_aceita_mesmo_item_em_clientes_diferentes(self, conexao: Connection) -> None:
        hotel = criar_cliente(conexao, "Hotel Aurora")
        pousada = criar_cliente(conexao, "Pousada Vista Verde")

        criar_item(conexao, hotel, "Lençol")
        criar_item(conexao, pousada, "Lençol")

        total = conexao.execute(text("select count(*) from itens")).scalar_one()
        assert total == 2


class TestPrecoPorData:
    """v1.1 — um preço por (cliente, item, dia), valor positivo, item do próprio cliente."""

    INSERT = (
        "insert into precos (cliente_id, item_id, vigencia_inicio, valor_unitario)"
        " values (:c, :i, :inicio, :valor)"
    )

    def test_aceita_inicio_no_meio_do_mes(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")

        executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-06-15", valor=4.50)

        total = conexao.execute(text("select count(*) from precos")).scalar_one()
        assert total == 1

    def test_aceita_dois_precos_no_mesmo_mes_em_dias_diferentes(self, conexao: Connection) -> None:
        """A regra antiga (um por mês) não existe mais no banco."""
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")

        executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-09-01", valor=4.50)
        executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-09-15", valor=4.80)

        total = conexao.execute(text("select count(*) from precos")).scalar_one()
        assert total == 2

    def test_recusa_dois_precos_no_mesmo_dia(self, conexao: Connection) -> None:
        """uq_precos_cliente_item_inicio: duas alterações no mesmo dia viram uma."""
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")
        executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-09-15", valor=4.50)

        with pytest.raises(IntegrityError) as erro:
            executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-09-15", valor=5.00)
        assert "uq_precos_cliente_item_inicio" in str(erro.value)

    def test_exige_data_de_inicio(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")

        with pytest.raises(IntegrityError):
            executar(conexao, self.INSERT, c=cliente, i=item, inicio=None, valor=4.50)

    @pytest.mark.parametrize("valor", [Decimal("0"), Decimal("-1.00")])
    def test_recusa_valor_nao_positivo(self, conexao: Connection, valor: Decimal) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")

        with pytest.raises(IntegrityError):
            executar(conexao, self.INSERT, c=cliente, i=item, inicio="2026-06-01", valor=valor)

    def test_recusa_preco_com_item_de_outro_cliente(self, conexao: Connection) -> None:
        """A FK composta impede misturar catálogo entre clientes."""
        hotel = criar_cliente(conexao, "Hotel Aurora")
        pousada = criar_cliente(conexao, "Pousada Vista Verde")
        item_da_pousada = criar_item(conexao, pousada, "Toalha")

        with pytest.raises(IntegrityError):
            executar(
                conexao, self.INSERT, c=hotel, i=item_da_pousada, inicio="2026-06-01", valor=4.50
            )


class TestLancamentoUnicoPorClienteData:
    """Req 5.2 e 5.3 — no máximo um lançamento por cliente por data."""

    def test_recusa_segundo_lancamento_do_mesmo_cliente_na_mesma_data(
        self, conexao: Connection
    ) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_lancamento(conexao, cliente, "2026-09-01")

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamentos (cliente_id, data) values (:c, '2026-09-01')",
                c=cliente,
            )

    def test_aceita_clientes_diferentes_na_mesma_data(self, conexao: Connection) -> None:
        hotel = criar_cliente(conexao, "Hotel Aurora")
        pousada = criar_cliente(conexao, "Pousada Vista Verde")

        criar_lancamento(conexao, hotel, "2026-09-01")
        criar_lancamento(conexao, pousada, "2026-09-01")

        total = conexao.execute(text("select count(*) from lancamentos")).scalar_one()
        assert total == 2

    def test_aceita_mesmo_cliente_em_datas_diferentes(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")

        criar_lancamento(conexao, cliente, "2026-09-01")
        criar_lancamento(conexao, cliente, "2026-09-02")

        total = conexao.execute(text("select count(*) from lancamentos")).scalar_one()
        assert total == 2


class TestComandaUnicaPorCliente:
    """Req 5.9 e 5.10 — única por cliente, insensível a caixa, ignorando nulos."""

    def test_recusa_comanda_repetida_no_mesmo_cliente(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_lancamento(conexao, cliente, "2026-09-01", "1201")

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamentos (cliente_id, data, comanda)"
                " values (:c, '2026-09-02', '1201')",
                c=cliente,
            )

    def test_aceita_mesma_comanda_em_clientes_diferentes(self, conexao: Connection) -> None:
        hotel = criar_cliente(conexao, "Hotel Aurora")
        pousada = criar_cliente(conexao, "Pousada Vista Verde")

        criar_lancamento(conexao, hotel, "2026-09-01", "1201")
        criar_lancamento(conexao, pousada, "2026-09-01", "1201")

        total = conexao.execute(text("select count(*) from lancamentos")).scalar_one()
        assert total == 2

    @pytest.mark.parametrize(
        ("gravada", "tentada"),
        [("A100", "a100"), ("a100", "A100"), ("Abc-1", "ABC-1")],
    )
    def test_recusa_comanda_que_difere_apenas_na_caixa(
        self, conexao: Connection, gravada: str, tentada: str
    ) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_lancamento(conexao, cliente, "2026-09-01", gravada)

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamentos (cliente_id, data, comanda)"
                " values (:c, '2026-09-02', :comanda)",
                c=cliente,
                comanda=tentada,
            )

    def test_recusa_comanda_apenas_com_espacos(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamentos (cliente_id, data, comanda)"
                " values (:c, '2026-09-01', '   ')",
                c=cliente,
            )

    def test_aceita_varios_lancamentos_sem_comanda(self, conexao: Connection) -> None:
        """O índice é PARCIAL: nulos não colidem entre si."""
        cliente = criar_cliente(conexao, "Hotel Aurora")

        criar_lancamento(conexao, cliente, "2026-09-01")
        criar_lancamento(conexao, cliente, "2026-09-02")
        criar_lancamento(conexao, cliente, "2026-09-03")

        sem_comanda = conexao.execute(
            text("select count(*) from lancamentos where comanda is null")
        ).scalar_one()
        assert sem_comanda == 3


class TestLinhaDeLancamento:
    """Req 5.11, 5.12 e 6.4 — quantidade, item único e total gerado."""

    def _linha(self, conexao: Connection) -> tuple[str, str]:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")
        lancamento = criar_lancamento(conexao, cliente, "2026-09-01", "1201")
        return lancamento, item

    def test_total_e_calculado_pelo_banco(self, conexao: Connection) -> None:
        lancamento, item = self._linha(conexao)

        total = conexao.execute(
            text(
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
                " values (:l, :i, 40, 4.50) returning total"
            ),
            {"l": lancamento, "i": item},
        ).scalar_one()

        # 4,50 x 40 = 180,00 exato: preço com 2 casas x inteiro não gera dízima
        assert str(total) == "180.00"

    def test_total_nao_pode_ser_gravado_manualmente(self, conexao: Connection) -> None:
        """Coluna gerada: não existe caminho para um total divergente."""
        lancamento, item = self._linha(conexao)

        with pytest.raises(DatabaseError):
            executar(
                conexao,
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado, total)"
                " values (:l, :i, 40, 4.50, 999.99)",
                l=lancamento,
                i=item,
            )

    def test_recusa_item_repetido_no_lancamento(self, conexao: Connection) -> None:
        lancamento, item = self._linha(conexao)
        executar(
            conexao,
            "insert into lancamento_linhas"
            " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
            " values (:l, :i, 40, 4.50)",
            l=lancamento,
            i=item,
        )

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
                " values (:l, :i, 10, 4.50)",
                l=lancamento,
                i=item,
            )

    @pytest.mark.parametrize("quantidade", [0, -5])
    def test_recusa_quantidade_nao_positiva(self, conexao: Connection, quantidade: int) -> None:
        lancamento, item = self._linha(conexao)

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
                " values (:l, :i, :qtd, 4.50)",
                l=lancamento,
                i=item,
                qtd=quantidade,
            )

    def test_recusa_valor_congelado_nao_positivo(self, conexao: Connection) -> None:
        lancamento, item = self._linha(conexao)

        with pytest.raises(IntegrityError):
            executar(
                conexao,
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
                " values (:l, :i, 10, 0)",
                l=lancamento,
                i=item,
            )


class TestProtecaoDoHistorico:
    """Req 2.11 e 3.12 — ON DELETE RESTRICT em registro com histórico."""

    def test_recusa_excluir_cliente_com_lancamento(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_lancamento(conexao, cliente, "2026-09-01")

        with pytest.raises(IntegrityError):
            executar(conexao, "delete from clientes where id = :c", c=cliente)

    def test_recusa_excluir_item_usado_em_lancamento(self, conexao: Connection) -> None:
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")
        lancamento = criar_lancamento(conexao, cliente, "2026-09-01")
        executar(
            conexao,
            "insert into lancamento_linhas"
            " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
            " values (:l, :i, 40, 4.50)",
            l=lancamento,
            i=item,
        )

        with pytest.raises(IntegrityError):
            executar(conexao, "delete from itens where id = :i", i=item)

    def test_permite_excluir_cliente_sem_lancamento(self, conexao: Connection) -> None:
        """Sem histórico, a exclusão é permitida e leva o catálogo (Req 2.10)."""
        cliente = criar_cliente(conexao, "Hotel Aurora")
        criar_item(conexao, cliente, "Lençol")

        executar(conexao, "delete from clientes where id = :c", c=cliente)

        assert conexao.execute(text("select count(*) from clientes")).scalar_one() == 0
        assert conexao.execute(text("select count(*) from itens")).scalar_one() == 0

    def test_excluir_lancamento_remove_as_linhas(self, conexao: Connection) -> None:
        """CASCADE nas linhas: excluir o lançamento leva suas linhas (Req 5.23)."""
        cliente = criar_cliente(conexao, "Hotel Aurora")
        item = criar_item(conexao, cliente, "Lençol")
        lancamento = criar_lancamento(conexao, cliente, "2026-09-01")
        executar(
            conexao,
            "insert into lancamento_linhas"
            " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
            " values (:l, :i, 40, 4.50)",
            l=lancamento,
            i=item,
        )

        executar(conexao, "delete from lancamentos where id = :l", l=lancamento)

        assert conexao.execute(text("select count(*) from lancamento_linhas")).scalar_one() == 0


class TestIsolamentoEntreTestes:
    """A fixture reverte a transação: nada vaza de um teste para o outro."""

    def test_grava_dados(self, conexao: Connection) -> None:
        criar_cliente(conexao, "Cliente Temporario")
        assert conexao.execute(text("select count(*) from clientes")).scalar_one() == 1

    def test_banco_esta_limpo_no_teste_seguinte(self, conexao: Connection) -> None:
        assert conexao.execute(text("select count(*) from clientes")).scalar_one() == 0
