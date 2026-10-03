"""Schemas de entrada e saída de Item (v1.1: com preço)."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.dominio import PrecoVigente
from app.models.item import Item
from app.schemas.preco import PrecoAtual, ValorDePreco

NomeDeItem = Field(
    min_length=1,
    max_length=120,
    description="Nome do tipo de item. Único no catálogo do cliente, ignorando caixa.",
    examples=["Lençol"],
)


class ItemEntrada(BaseModel):
    """Corpo de renomeação."""

    nome: str = NomeDeItem


class ItemNovo(BaseModel):
    """Corpo de criação: nome e preço por peça, os dois obrigatórios (Req 3.1).

    O preço começa a valer hoje (decidido pela API) e, por ser o primeiro do
    item, vale também para pedidos de datas anteriores.
    """

    nome: str = NomeDeItem
    valor_unitario: ValorDePreco


class ItemResposta(BaseModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    nome: str
    ativo: bool
    preco_atual: PrecoAtual | None = Field(
        description="Preço que vale hoje. Nulo quando o item ainda não tem preço."
    )

    @classmethod
    def de(cls, item: Item, vigente: PrecoVigente | None, hoje: date) -> "ItemResposta":
        return cls(
            id=item.id,
            cliente_id=item.cliente_id,
            nome=item.nome,
            ativo=item.ativo,
            preco_atual=PrecoAtual.de(vigente, hoje),
        )
