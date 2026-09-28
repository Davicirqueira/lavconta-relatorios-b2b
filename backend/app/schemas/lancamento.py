"""Schemas de entrada e saída de Lançamento.

O CLIENTE NUNCA ENVIA VALOR
    A entrada tem apenas item e quantidade. O preço é resolvido e congelado pelo
    servidor — aceitar valor do navegador seria permitir que ele definisse quanto
    custa.

DINHEIRO COMO TEXTO
    Valores saem como string decimal, nunca como número. Número em JSON vira
    ``double`` no JavaScript, e ponto flutuante binário não representa todo
    decimal exatamente.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

DinheiroTexto = Annotated[Decimal, PlainSerializer(lambda valor: f"{valor:.2f}", return_type=str)]


class LinhaEntrada(BaseModel):
    """Uma linha do pedido, como o operador a informa."""

    item_id: uuid.UUID
    quantidade: int = Field(
        gt=0,
        description="Quantidade de peças. Inteiro positivo: peças são contáveis.",
        examples=[40],
    )


class LancamentoEntrada(BaseModel):
    """Corpo de criação e de edição de lançamento."""

    cliente_id: uuid.UUID
    data: date = Field(
        description=(
            "Data do pedido, no formato YYYY-MM-DD. Data de calendário, sem hora "
            "e sem fuso. Não pode ser futura."
        ),
        examples=["2026-09-01"],
    )
    comanda: str | None = Field(
        default=None,
        max_length=50,
        description=(
            "Número da comanda. Opcional. Quando preenchida, deve ser única para o "
            "cliente, ignorando maiúsculas e minúsculas."
        ),
        examples=["1201"],
    )
    linhas: list[LinhaEntrada] = Field(min_length=1, description="Ao menos um item com quantidade.")


class PreviaEntrada(BaseModel):
    """Corpo da prévia de totais.

    Sem comanda: ela não afeta valor. Sem exigência de data não futura: prévia
    trata de cálculo, e conflito é assunto do salvamento.
    """

    cliente_id: uuid.UUID
    data: date = Field(
        description="Data do pedido. Define o mês usado para resolver o preço.",
        examples=["2026-09-01"],
    )
    linhas: list[LinhaEntrada] = Field(min_length=1)


class LinhaResposta(BaseModel):
    """Uma linha gravada, com o valor congelado e o total."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    quantidade: int
    valor_unitario_congelado: DinheiroTexto = Field(
        description="Preço vigente no mês da data do lançamento, gravado na criação."
    )
    total: DinheiroTexto = Field(description="Valor congelado × quantidade.")


class LancamentoResposta(BaseModel):
    """Lançamento como a API o devolve, com totais calculados."""

    id: uuid.UUID
    cliente_id: uuid.UUID
    data: date
    comanda: str | None
    linhas: list[LinhaResposta]
    total_pecas: int
    total_valor: DinheiroTexto


class LancamentoResumo(BaseModel):
    """Lançamento na listagem, sem as linhas."""

    id: uuid.UUID
    cliente_id: uuid.UUID
    data: date
    comanda: str | None
    total_pecas: int
    total_valor: DinheiroTexto


class LinhaPrevia(BaseModel):
    """Uma linha calculada, sem persistência."""

    item_id: uuid.UUID
    quantidade: int
    valor_unitario: DinheiroTexto
    total: DinheiroTexto


class PreviaResposta(BaseModel):
    """Totais calculados sem gravar nada.

    ``itens_sem_preco`` vem como lista em vez de erro: a tela marca essas linhas
    enquanto o operador monta o pedido, e o salvamento é que recusa.
    """

    linhas: list[LinhaPrevia]
    total_pecas: int
    total_valor: DinheiroTexto
    itens_sem_preco: list[uuid.UUID]
