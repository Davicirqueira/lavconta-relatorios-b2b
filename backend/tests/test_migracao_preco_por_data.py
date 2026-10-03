"""Migração v1.1 (fase 1): dados existentes passam para a regra nova sem perda.

Roda num banco **descartável** (``lavconta_migracao_teste``) no mesmo servidor
local, para poder voltar à revisão da v1, gravar dados no formato antigo e só
então aplicar a migração — algo que o banco de teste compartilhado, já em
``head``, não permite (Req 2.1 a 2.4).
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from tests.conftest import RAIZ_BACKEND

REVISAO_V1 = "54016f7a3787"
REVISAO_V11 = "9c4e1a7b2d60"
NOME_BANCO = "lavconta_migracao_teste"


@pytest.fixture
def banco_descartavel(url_banco_teste: str) -> Iterator[tuple[Engine, Config]]:
    url = make_url(url_banco_teste)
    administrativo = create_engine(
        url.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    with administrativo.connect() as conexao:
        conexao.execute(text(f'drop database if exists "{NOME_BANCO}" with (force)'))
        conexao.execute(text(f'create database "{NOME_BANCO}"'))

    url_descartavel = url.set(database=NOME_BANCO).render_as_string(hide_password=False)
    configuracao = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    configuracao.set_main_option("sqlalchemy.url", url_descartavel)
    motor = create_engine(url_descartavel)
    try:
        yield motor, configuracao
    finally:
        motor.dispose()
        with administrativo.connect() as conexao:
            conexao.execute(text(f'drop database if exists "{NOME_BANCO}" with (force)'))
        administrativo.dispose()


def _semear_formato_v1(motor: Engine) -> None:
    """Dois itens, preços por mês e um pedido com valor congelado."""
    with motor.begin() as c:
        cliente = c.execute(
            text("insert into clientes (nome) values ('Hotel Aurora') returning id")
        ).scalar_one()
        lencol = c.execute(
            text("insert into itens (cliente_id, nome) values (:c, 'Lençol') returning id"),
            {"c": cliente},
        ).scalar_one()
        fronha = c.execute(
            text("insert into itens (cliente_id, nome) values (:c, 'Fronha') returning id"),
            {"c": cliente},
        ).scalar_one()
        for item, mes, valor in (
            (lencol, "2026-06-01", "4.50"),
            (lencol, "2026-09-01", "4.80"),
            (fronha, "2026-06-01", "3.50"),
        ):
            c.execute(
                text(
                    "insert into precos (cliente_id, item_id, vigencia_mes, valor_unitario)"
                    " values (:c, :i, :m, :v)"
                ),
                {"c": cliente, "i": item, "m": mes, "v": valor},
            )
        pedido = c.execute(
            text(
                "insert into lancamentos (cliente_id, data) values (:c, '2026-08-20') returning id"
            ),
            {"c": cliente},
        ).scalar_one()
        c.execute(
            text(
                "insert into lancamento_linhas"
                " (lancamento_id, item_id, quantidade, valor_unitario_congelado)"
                " values (:p, :i, 40, 4.50)"
            ),
            {"p": pedido, "i": lencol},
        )


def _retrato(motor: Engine) -> dict:
    with motor.connect() as c:
        precos = c.execute(
            text("select item_id, valor_unitario from precos order by item_id, valor_unitario")
        ).all()
        linhas = c.execute(
            text("select quantidade, valor_unitario_congelado, total from lancamento_linhas")
        ).all()
    return {"precos": precos, "linhas": linhas}


def test_upgrade_preserva_precos_e_pedidos(banco_descartavel) -> None:  # noqa: ANN001
    motor, configuracao = banco_descartavel
    command.upgrade(configuracao, REVISAO_V1)
    _semear_formato_v1(motor)
    antes = _retrato(motor)

    command.upgrade(configuracao, REVISAO_V11)

    assert _retrato(motor) == antes
    with motor.connect() as c:
        divergentes = c.execute(
            text("select count(*) from precos where vigencia_inicio is distinct from vigencia_mes")
        ).scalar_one()
    assert divergentes == 0


def test_downgrade_volta_ao_formato_v1_enquanto_nao_ha_dois_precos_no_mes(
    banco_descartavel,  # noqa: ANN001
) -> None:
    motor, configuracao = banco_descartavel
    command.upgrade(configuracao, REVISAO_V1)
    _semear_formato_v1(motor)
    antes = _retrato(motor)
    command.upgrade(configuracao, REVISAO_V11)

    command.downgrade(configuracao, REVISAO_V1)

    assert _retrato(motor) == antes


def test_downgrade_recusa_quando_ha_dois_precos_no_mesmo_mes(
    banco_descartavel,  # noqa: ANN001
) -> None:
    motor, configuracao = banco_descartavel
    command.upgrade(configuracao, REVISAO_V1)
    _semear_formato_v1(motor)
    command.upgrade(configuracao, REVISAO_V11)
    with motor.begin() as c:
        # uso da regra nova: segundo preço do Lençol em setembro, no dia 15
        c.execute(
            text(
                "insert into precos (cliente_id, item_id, vigencia_inicio, valor_unitario)"
                " select cliente_id, item_id, date '2026-09-15', 5.00 from precos"
                " where vigencia_inicio = date '2026-09-01'"
            )
        )

    with pytest.raises(RuntimeError, match="Downgrade recusado"):
        command.downgrade(configuracao, REVISAO_V1)

    with motor.connect() as c:
        versao = c.execute(text("select version_num from alembic_version")).scalar_one()
    assert versao == REVISAO_V11
