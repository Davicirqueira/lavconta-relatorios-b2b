"""Schema inicial do Lavconta.

Cria as cinco tabelas do domínio e as constraints que reforçam as regras
críticas no nível do banco:

- ``uq_lancamentos_cliente_data``: no máximo um lançamento por cliente por data
  (Req 5.2 e 5.3).
- ``ix_lancamentos_comanda_unica_por_cliente``: índice único PARCIAL sobre
  ``lower(btrim(comanda))`` com ``WHERE comanda is not null`` — comanda única por
  cliente, ignorando nulos e insensível a caixa (Req 5.9 e 5.10).
- ``fk_precos_item_do_cliente``: FK composta garantindo que um preço aponte para
  item do mesmo cliente (engineering.md §2).
- ``ck_precos_vigencia_primeiro_dia``: vigência sempre no dia 1 (Req 4.1).
- ``total`` como coluna gerada: impossível divergir de congelado × quantidade
  (Req 6.4).
- ``ON DELETE RESTRICT`` em cliente e item de lançamento: registro com histórico
  não pode ser excluído (Req 2.11 e 3.12).

Dinheiro em ``NUMERIC`` e data de negócio em ``DATE`` (sem fuso), conforme
Requisitos 4.11 e 11.1.

Revision ID: 54016f7a3787
Revises:
Create Date: 2026-09-25 21:11:01.109922-03:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "54016f7a3787"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(nome) <> ''", name=op.f("ck_clientes_nome_nao_vazio")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clientes")),
        sa.UniqueConstraint("id", name="uq_clientes_id"),
    )
    op.create_index(
        "ix_clientes_nome_unico", "clientes", [sa.literal_column("lower(btrim(nome))")], unique=True
    )
    op.create_table(
        "itens",
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(nome) <> ''", name=op.f("ck_itens_nome_nao_vazio")),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["clientes.id"], name=op.f("fk_itens_cliente_id"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_itens")),
        sa.UniqueConstraint("id", "cliente_id", name="uq_itens_id_cliente"),
    )
    op.create_index(
        "ix_itens_nome_unico_por_cliente",
        "itens",
        ["cliente_id", sa.literal_column("lower(btrim(nome))")],
        unique=True,
    )
    op.create_table(
        "lancamentos",
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("comanda", sa.String(length=50), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "comanda is null or btrim(comanda) <> ''", name=op.f("ck_lancamentos_comanda_nao_vazia")
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
            name=op.f("fk_lancamentos_cliente_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lancamentos")),
        sa.UniqueConstraint("cliente_id", "data", name="uq_lancamentos_cliente_data"),
    )
    op.create_index(
        "ix_lancamentos_cliente_periodo", "lancamentos", ["cliente_id", "data"], unique=False
    )
    op.create_index(
        "ix_lancamentos_comanda_unica_por_cliente",
        "lancamentos",
        ["cliente_id", sa.literal_column("lower(btrim(comanda))")],
        unique=True,
        postgresql_where=sa.text("comanda is not null"),
    )
    op.create_table(
        "lancamento_linhas",
        sa.Column("lancamento_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_unitario_congelado", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "total",
            sa.Numeric(precision=12, scale=2),
            sa.Computed("valor_unitario_congelado * quantidade", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_lancamento_linhas_quantidade_positiva")),
        sa.CheckConstraint(
            "valor_unitario_congelado > 0", name=op.f("ck_lancamento_linhas_valor_positivo")
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["itens.id"],
            name=op.f("fk_lancamento_linhas_item_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lancamento_id"],
            ["lancamentos.id"],
            name=op.f("fk_lancamento_linhas_lancamento_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lancamento_linhas")),
        sa.UniqueConstraint("lancamento_id", "item_id", name="uq_linhas_lancamento_item"),
    )
    op.create_index(
        "ix_linhas_por_lancamento", "lancamento_linhas", ["lancamento_id"], unique=False
    )
    op.create_table(
        "precos",
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("vigencia_mes", sa.Date(), nullable=False),
        sa.Column("valor_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "extract(day from vigencia_mes) = 1", name=op.f("ck_precos_vigencia_primeiro_dia")
        ),
        sa.CheckConstraint("valor_unitario > 0", name=op.f("ck_precos_valor_positivo")),
        sa.ForeignKeyConstraint(
            ["item_id", "cliente_id"],
            ["itens.id", "itens.cliente_id"],
            name="fk_precos_item_do_cliente",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_precos")),
        sa.UniqueConstraint(
            "cliente_id", "item_id", "vigencia_mes", name="uq_precos_cliente_item_mes"
        ),
    )
    op.create_index(
        "ix_precos_resolucao",
        "precos",
        ["cliente_id", "item_id", sa.literal_column("vigencia_mes DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Remove tudo o que o upgrade criou, na ordem inversa das dependências."""
    op.drop_index("ix_precos_resolucao", table_name="precos")
    op.drop_table("precos")
    op.drop_index("ix_linhas_por_lancamento", table_name="lancamento_linhas")
    op.drop_table("lancamento_linhas")
    op.drop_index(
        "ix_lancamentos_comanda_unica_por_cliente",
        table_name="lancamentos",
        postgresql_where=sa.text("comanda is not null"),
    )
    op.drop_index("ix_lancamentos_cliente_periodo", table_name="lancamentos")
    op.drop_table("lancamentos")
    op.drop_index("ix_itens_nome_unico_por_cliente", table_name="itens")
    op.drop_table("itens")
    op.drop_index("ix_clientes_nome_unico", table_name="clientes")
    op.drop_table("clientes")
