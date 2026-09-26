"""Modelo de Item — tipo de peça do catálogo, pertencente a um cliente."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditoriaMixin, Base, IdentificadorMixin

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.lancamento import LancamentoLinha
    from app.models.preco import Preco


class Item(IdentificadorMixin, AuditoriaMixin, Base):
    """Tipo de peça (lençol, fronha, toalha...) do catálogo de um cliente.

    Item não é excluído quando já tem histórico: nesse caso só pode ser
    inativado (Req 3.11 e 3.12). Inativo sai da seleção de novos lançamentos
    sem afetar relatórios passados (Req 3.13).
    """

    __tablename__ = "itens"

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    cliente: Mapped["Cliente"] = relationship(back_populates="itens")
    precos: Mapped[list["Preco"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )
    # sem cascade: linha de lançamento é histórico e bloqueia a exclusão do item
    linhas: Mapped[list["LancamentoLinha"]] = relationship(back_populates="item")

    __table_args__ = (
        CheckConstraint("btrim(nome) <> ''", name="nome_nao_vazio"),
        # permite a FK composta em precos: garante no banco que o preço aponte
        # para um item do MESMO cliente (engineering.md §2)
        UniqueConstraint("id", "cliente_id", name="uq_itens_id_cliente"),
        # nome único por cliente, ignorando caixa e espaços nas pontas (Req 3.2)
        Index(
            "ix_itens_nome_unico_por_cliente",
            "cliente_id",
            text("lower(btrim(nome))"),
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Item {self.nome!r} ativo={self.ativo}>"
