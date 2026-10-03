"""Schemas de entrada e saída de Preço (v1.1).

DINHEIRO COMO TEXTO NA SAÍDA
    Valor monetário serializa como string decimal (``"4.50"``), não como número.
    Motivo concreto: número em JSON vira ``double`` no JavaScript, e ponto
    flutuante binário não representa todo decimal exatamente. Trafegando texto, o
    frontend formata sem nunca converter para número.

SEM DATA NA ENTRADA
    A alteração de preço não tem campo de data: o início é sempre hoje, decidido
    pela API (Req 1.2). ``extra="forbid"`` recusa explicitamente um corpo que
    tente informar data, em vez de ignorá-la em silêncio.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.dominio import ModoDeAlteracao, PrecoVigente

# Dinheiro na saída: sempre duas casas, como texto.
DinheiroTexto = Annotated[Decimal, PlainSerializer(lambda valor: f"{valor:.2f}", return_type=str)]

ValorDePreco = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Preço por peça, com no máximo duas casas decimais.",
        examples=["4.50"],
    ),
]


class AlteracaoDePreco(BaseModel):
    """Corpo para mudar ou corrigir o preço de um item."""

    model_config = ConfigDict(extra="forbid")

    valor_unitario: ValorDePreco
    modo: ModoDeAlteracao = Field(
        default=ModoDeAlteracao.A_PARTIR_DE_HOJE,
        description=(
            "`a_partir_de_hoje`: o novo preço vale para pedidos de hoje em diante. "
            "`corrigir_atual`: troca o valor do preço atual desde o dia em que foi "
            "definido (erro de digitação). Pedidos já registrados não mudam em "
            "nenhum dos dois."
        ),
    )


class PrecoAtual(BaseModel):
    """Preço que vale hoje para um item."""

    valor_unitario: DinheiroTexto
    desde: date = Field(description="Dia em que este preço começou a valer.")
    e_hoje: bool = Field(
        description="Verdadeiro quando o preço começou hoje: mudar e corrigir têm o mesmo efeito."
    )

    @classmethod
    def de(cls, vigente: PrecoVigente | None, hoje: date) -> "PrecoAtual | None":
        if vigente is None:
            return None
        return cls(
            valor_unitario=vigente.valor_unitario,
            desde=vigente.desde,
            e_hoje=vigente.desde == hoje,
        )


class ImpactoDaAlteracao(BaseModel):
    """Aviso antes de confirmar uma alteração (Req 1.6 e 1.13)."""

    pedidos_com_valor_anterior: int = Field(
        description="Pedidos já registrados que continuam com o valor anterior."
    )


class ItemComPreco(BaseModel):
    """Um item do catálogo e o preço que vale na data consultada."""

    item_id: uuid.UUID
    nome: str
    valor_unitario: DinheiroTexto | None = Field(
        description="Preço por peça na data. Nulo quando o item ainda não tem preço."
    )
    desde: date | None = Field(description="Dia em que o preço aplicado começou a valer.")
    sem_preco: bool = Field(description="Item sem nenhum preço. Impede salvar o pedido.")


class PrecosNaData(BaseModel):
    """Preços dos itens de um cliente numa data (usado pelo formulário de pedido)."""

    data: date
    itens: list[ItemComPreco]
