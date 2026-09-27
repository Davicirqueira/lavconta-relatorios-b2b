"""Schemas de entrada e saída de Item."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ItemEntrada(BaseModel):
    """Corpo de criação e de renomeação."""

    nome: str = Field(
        min_length=1,
        max_length=120,
        description="Nome do tipo de item. Único no catálogo do cliente, ignorando caixa.",
        examples=["Lençol"],
    )


class ItemResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    nome: str
    ativo: bool
