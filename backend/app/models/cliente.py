"""Modelo de Cliente — empresa atendida pela Lavandix."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditoriaMixin, Base, IdentificadorMixin

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.lancamento import Lancamento
    from app.models.preco import Preco


class Cliente(IdentificadorMixin, AuditoriaMixin, Base):
    """Empresa atendida.

    Cada cliente tem catálogo de itens e tabela de preços próprios: não existe
    catálogo nem preço global (Req 2.6).
    """

    __tablename__ = "clientes"

    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    itens: Mapped[list["Item"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
    )
    precos: Mapped[list["Preco"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
    )
    # sem cascade: lançamento é histórico de cobrança e bloqueia a exclusão
    # do cliente (Req 2.11), reforçado por ON DELETE RESTRICT na FK
    lancamentos: Mapped[list["Lancamento"]] = relationship(back_populates="cliente")

    __table_args__ = (
        CheckConstraint("btrim(nome) <> ''", name="nome_nao_vazio"),
        # habilita a FK composta de precos (garante item pertencente ao cliente)
        UniqueConstraint("id", name="uq_clientes_id"),
        # Nome único ignorando caixa e espaços nas pontas (Req 2.5).
        # Índice sobre expressão: "Hotel Aurora" e " hotel aurora " colidem.
        Index("ix_clientes_nome_unico", text("lower(btrim(nome))"), unique=True),
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.nome!r} ativo={self.ativo}>"
