"""Modelos de Lançamento e Linha de lançamento — o pedido diário de um cliente."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditoriaMixin, Base, IdentificadorMixin

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.item import Item


class Lancamento(IdentificadorMixin, AuditoriaMixin, Base):
    """Pedido diário de um cliente numa data.

    Identificador natural: (cliente, data). Cada empresa faz no máximo um pedido
    por dia, e o sistema impede o segundo (Req 5.2).

    A validação de data futura NÃO pode ser constraint: ``CHECK`` exige expressão
    imutável e "hoje" depende do fuso America/Sao_Paulo. Fica no service (Req 5.15).
    """

    __tablename__ = "lancamentos"

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        # RESTRICT: cliente com lançamento não pode ser excluído (Req 2.11)
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # data de calendário, sem hora e sem fuso (Req 11.1)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    # opcional; quando preenchida, única por cliente (Req 5.5 e 5.9)
    comanda: Mapped[str | None] = mapped_column(String(50), nullable=True)

    cliente: Mapped["Cliente"] = relationship(back_populates="lancamentos")
    linhas: Mapped[list["LancamentoLinha"]] = relationship(
        back_populates="lancamento",
        cascade="all, delete-orphan",
        order_by="LancamentoLinha.criado_em",
    )

    __table_args__ = (
        # unicidade forte (cliente, data) — Req 5.2 e 5.3
        UniqueConstraint("cliente_id", "data", name="uq_lancamentos_cliente_data"),
        # comanda só com espaços é tratada como nula, nunca texto vazio (Req 5.8)
        CheckConstraint(
            "comanda is null or btrim(comanda) <> ''",
            name="comanda_nao_vazia",
        ),
        # Unicidade PARCIAL e insensível a caixa (Req 5.9 e 5.10):
        # ignora lançamentos sem comanda; 'a100' e 'A100' colidem.
        Index(
            "ix_lancamentos_comanda_unica_por_cliente",
            "cliente_id",
            text("lower(btrim(comanda))"),
            unique=True,
            postgresql_where=text("comanda is not null"),
        ),
        # serve à busca por período do relatório
        Index("ix_lancamentos_cliente_periodo", "cliente_id", "data"),
    )

    def __repr__(self) -> str:
        return f"<Lancamento cliente={self.cliente_id} data={self.data}>"


class LancamentoLinha(IdentificadorMixin, Base):
    """Item + quantidade + valor unitário congelado.

    O ``valor_unitario_congelado`` é copiado do preço vigente no momento da
    criação e nunca recalculado (Req 6.1 a 6.3). É o que mantém relatórios
    passados estáveis.

    O ``total`` é coluna gerada pelo banco: torna impossível gravar um total que
    divirja de congelado × quantidade.
    """

    __tablename__ = "lancamento_linhas"

    lancamento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lancamentos.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        # RESTRICT: item com histórico não pode ser excluído (Req 3.12)
        ForeignKey("itens.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # peças são contáveis: inteiro positivo (Req 5.11)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_unitario_congelado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # numeric(10,2) × integer é exato: não há arredondamento nesta cadeia
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        Computed("valor_unitario_congelado * quantidade", persisted=True),
        nullable=False,
    )

    # instante real de criação da linha (timestamptz), usado para ordenação
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    lancamento: Mapped["Lancamento"] = relationship(back_populates="linhas")
    item: Mapped["Item"] = relationship(back_populates="linhas")

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint("valor_unitario_congelado > 0", name="valor_positivo"),
        # mesmo item não repete no mesmo lançamento (Req 5.12)
        UniqueConstraint("lancamento_id", "item_id", name="uq_linhas_lancamento_item"),
        Index("ix_linhas_por_lancamento", "lancamento_id"),
    )

    def __repr__(self) -> str:
        return f"<LancamentoLinha item={self.item_id} qtd={self.quantidade}>"
