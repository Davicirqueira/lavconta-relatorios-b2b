"""v1.1 — preço por data (fase 1: expand).

O preço deixa de valer por mês e passa a valer **a partir de um dia**
(``business-rules.md``, seção Preços; requisitos v1.1, Req 1 e 2).

Esta revisão só ACRESCENTA a estrutura nova e afrouxa a antiga, sem apagar dado:

- ``vigencia_inicio`` (date, NOT NULL), preenchida com ``vigencia_mes``: cada
  preço existente passa a valer desde o dia 1 do mês em que valia (Req 2.1).
- ``uq_precos_cliente_item_inicio``: um preço por (cliente, item, dia). É o que
  garante no banco que duas alterações no mesmo dia viram uma só (Req 1.4).
- ``ix_precos_resolucao_inicio``: atende a resolução por data.
- Remove ``uq_precos_cliente_item_mes`` e torna ``vigencia_mes`` opcional: o
  código novo grava início no meio do mês e não preenche mais a coluna antiga.
  O CHECK de dia 1 continua (NULL passa no CHECK) e sai na fase 2.

Nenhuma linha de ``lancamento_linhas`` é tocada: valores congelados ficam
intactos (Req 2.3).

A fase 2 (revisão separada, depois do código novo estável em produção) remove
``vigencia_mes``, o CHECK de dia 1 e o índice antigo.

DOWNGRADE — LIMITAÇÃO
    Reconstrói ``vigencia_mes`` como o primeiro dia do mês de ``vigencia_inicio``
    e recria a unicidade por mês. Isso só é possível enquanto nenhum item tiver
    mais de um preço no mesmo mês. Depois que a regra nova for usada (ex.: preço
    mudado no dia 15 de um mês que já tinha preço), o downgrade é recusado com
    mensagem explicativa, e o caminho de volta é restaurar o backup (pg_dump)
    feito antes da migração (design v1.1, §2).

Revision ID: 9c4e1a7b2d60
Revises: 54016f7a3787
Create Date: 2026-10-02 12:00:00-03:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c4e1a7b2d60"
down_revision: str | None = "54016f7a3787"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. coluna nova, preenchida a partir da antiga, depois obrigatória
    op.add_column("precos", sa.Column("vigencia_inicio", sa.Date(), nullable=True))
    op.execute("UPDATE precos SET vigencia_inicio = vigencia_mes")
    op.alter_column("precos", "vigencia_inicio", nullable=False)

    # 2. unicidade e índice da regra nova
    op.create_unique_constraint(
        "uq_precos_cliente_item_inicio",
        "precos",
        ["cliente_id", "item_id", "vigencia_inicio"],
    )
    op.create_index(
        "ix_precos_resolucao_inicio",
        "precos",
        ["cliente_id", "item_id", sa.literal_column("vigencia_inicio DESC")],
        unique=False,
    )

    # 3. afrouxa a estrutura antiga (removida de vez na fase 2)
    op.drop_constraint("uq_precos_cliente_item_mes", "precos", type_="unique")
    op.alter_column("precos", "vigencia_mes", nullable=True)


def downgrade() -> None:
    conexao = op.get_bind()

    # Recusa explícita em vez de deixar a unicidade falhar com erro genérico.
    conflitos = conexao.execute(
        sa.text(
            """
            SELECT count(*) FROM (
                SELECT 1 FROM precos
                GROUP BY cliente_id, item_id, date_trunc('month', vigencia_inicio)
                HAVING count(*) > 1
            ) AS repetidos
            """
        )
    ).scalar_one()
    if conflitos:
        raise RuntimeError(
            f"Downgrade recusado: {conflitos} item(ns) têm mais de um preço no mesmo "
            "mês, o que a estrutura antiga não comporta. Restaure o backup (pg_dump) "
            "feito antes da migração."
        )

    op.execute(
        "UPDATE precos SET vigencia_mes = date_trunc('month', vigencia_inicio)::date "
        "WHERE vigencia_mes IS NULL OR vigencia_mes <> date_trunc('month', vigencia_inicio)::date"
    )
    op.alter_column("precos", "vigencia_mes", nullable=False)
    op.create_unique_constraint(
        "uq_precos_cliente_item_mes",
        "precos",
        ["cliente_id", "item_id", "vigencia_mes"],
    )

    op.drop_index("ix_precos_resolucao_inicio", table_name="precos")
    op.drop_constraint("uq_precos_cliente_item_inicio", "precos", type_="unique")
    op.drop_column("precos", "vigencia_inicio")
