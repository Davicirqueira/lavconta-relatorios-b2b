"""Schemas de entrada e saída de Cliente.

Separados dos modelos ORM de propósito: o modelo de banco nunca é exposto na API
(engineering.md §1). Isso evita vazar campo interno por acidente e deixa o
contrato explícito.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ClienteEntrada(BaseModel):
    """Corpo de criação e de renomeação."""

    nome: str = Field(
        min_length=1,
        max_length=160,
        description="Nome da empresa atendida. Único, ignorando caixa e espaços nas pontas.",
        examples=["Hotel Aurora"],
    )


class ClienteResposta(BaseModel):
    """Cliente como a API o devolve."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    ativo: bool
