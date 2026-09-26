"""Modelo de Preço — valor unitário de um item para um cliente, com vigência mensal."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditoriaMixin, Base, IdentificadorMixin

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.item import Item


class Preco(IdentificadorMixin, AuditoriaMixin, Base):
    """Preço de um item para um cliente, vigente a partir de um mês.

    Vigência se propaga: o preço vale do mês registrado em diante, até que um
    novo preço seja definido (Req 4.4). Por isso ``vigencia_mes`` é uma data
    (sempre dia 1) e não um par ano/mês — a resolução do preço vigente vira uma
    comparação simples que usa índice diretamente.
    """

    __tablename__ = "precos"

    cliente_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    # primeiro dia do mês de início de vigência
    vigencia_mes: Mapped[date] = mapped_column(Date, nullable=False)

    # duas casas decimais exatas: sem fração de centavo (Req 4.12)
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="precos")
    item: Mapped["Item"] = relationship(back_populates="precos")

    __table_args__ = (
        # FK composta: o item precisa pertencer ao cliente do preço.
        # Impede no banco que um preço aponte para item de outro cliente.
        ForeignKeyConstraint(
            ["item_id", "cliente_id"],
            ["itens.id", "itens.cliente_id"],
            name="fk_precos_item_do_cliente",
            ondelete="CASCADE",
        ),
        CheckConstraint("valor_unitario > 0", name="valor_positivo"),
        # vigência é sempre o primeiro dia do mês (Req 4.1)
        CheckConstraint("extract(day from vigencia_mes) = 1", name="vigencia_primeiro_dia"),
        # um preço por (cliente, item, mês) — Req 4.2 trata repetição como atualização
        UniqueConstraint(
            "cliente_id", "item_id", "vigencia_mes", name="uq_precos_cliente_item_mes"
        ),
        # serve à resolução do preço vigente: filtra por cliente+item e pega o
        # maior vigencia_mes <= mês de referência
        Index(
            "ix_precos_resolucao",
            "cliente_id",
            "item_id",
            mapped_column("vigencia_mes").desc(),
        ),
    )

    def __repr__(self) -> str:
        return f"<Preco {self.valor_unitario} desde {self.vigencia_mes}>"
