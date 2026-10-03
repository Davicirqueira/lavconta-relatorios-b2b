"""Modelo de Preço — valor por peça de um item para um cliente, válido a partir de um dia."""

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
    from app.models.item import Item


class Preco(IdentificadorMixin, AuditoriaMixin, Base):
    """Preço de um item para um cliente, válido a partir de ``vigencia_inicio``.

    O preço vale do dia de início em diante, até a próxima alteração
    (``business-rules.md``, seção Preços). A resolução para um pedido escolhe o
    preço com maior início menor ou igual à data do pedido; se não houver, o
    primeiro preço do item (que vale também para datas anteriores).

    TRANSIÇÃO (v1.1, migração 9c4e1a7b2d60)
        ``vigencia_mes`` é a coluna da v1 (sempre dia 1). Ficou opcional e não é
        mais gravada; sai na fase 2 da migração, junto com o CHECK de dia 1 e o
        índice ``ix_precos_resolucao``. Até lá o modelo a declara para continuar
        idêntico ao banco.
    """

    __tablename__ = "precos"

    cliente_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    # dia a partir do qual o preço vale (definido pelo sistema: hoje em São Paulo)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)

    # v1, em desuso: removida na fase 2
    vigencia_mes: Mapped[date | None] = mapped_column(Date, nullable=True)

    # duas casas decimais exatas: sem fração de centavo
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Apenas a relação com Item: ela tem chave estrangeira declarada (a composta).
    # Ver a nota em models/cliente.py sobre a ausência de Cliente.precos.
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
        # v1, em desuso: removido na fase 2 (NULL passa no CHECK)
        CheckConstraint("extract(day from vigencia_mes) = 1", name="vigencia_primeiro_dia"),
        # um preço por (cliente, item, dia): duas alterações no mesmo dia viram uma
        UniqueConstraint(
            "cliente_id", "item_id", "vigencia_inicio", name="uq_precos_cliente_item_inicio"
        ),
        # resolução por data: maior vigencia_inicio <= data do pedido
        Index(
            "ix_precos_resolucao_inicio",
            "cliente_id",
            "item_id",
            mapped_column("vigencia_inicio").desc(),
        ),
        # v1, em desuso: removido na fase 2
        Index(
            "ix_precos_resolucao",
            "cliente_id",
            "item_id",
            mapped_column("vigencia_mes").desc(),
        ),
    )

    def __repr__(self) -> str:
        return f"<Preco {self.valor_unitario} desde {self.vigencia_inicio}>"
