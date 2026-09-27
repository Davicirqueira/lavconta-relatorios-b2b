"""Schemas de entrada e saída de Preço.

DINHEIRO COMO TEXTO NA SAÍDA
    Valor monetário serializa como string decimal (``"4.50"``), não como número.
    Motivo concreto: número em JSON vira ``double`` no JavaScript, e ponto
    flutuante binário não representa todo decimal exatamente. Trafegando texto, o
    frontend formata sem nunca converter para número.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.core.datas import mes_como_texto, texto_para_mes

# Dinheiro na saída: sempre duas casas, como texto.
DinheiroTexto = Annotated[Decimal, PlainSerializer(lambda valor: f"{valor:.2f}", return_type=str)]

# Mês na saída: "YYYY-MM".
MesTexto = Annotated[date, PlainSerializer(mes_como_texto, return_type=str)]


class PrecoEntrada(BaseModel):
    """Corpo para definir ou atualizar o preço de um item.

    Repetir a mesma combinação (item, mês) é atualização, não duplicata.
    """

    item_id: uuid.UUID
    vigencia_mes: str = Field(
        description="Mês de início da vigência, no formato YYYY-MM.",
        examples=["2026-10"],
    )
    valor_unitario: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Preço por peça, com no máximo duas casas decimais.",
        examples=["4.50"],
    )

    @field_validator("vigencia_mes")
    @classmethod
    def _validar_formato_do_mes(cls, valor: str) -> str:
        # converte para validar; o serviço faz a conversão definitiva
        texto_para_mes(valor)
        return valor

    @property
    def mes(self) -> date:
        return texto_para_mes(self.vigencia_mes)


class ItemComPreco(BaseModel):
    """Um item do catálogo e seu preço vigente no mês consultado."""

    model_config = ConfigDict(from_attributes=True)

    item_id: uuid.UUID
    nome: str
    valor_unitario: DinheiroTexto | None = Field(
        description="Preço vigente no mês. Nulo quando não há preço definido."
    )
    vigencia_origem: MesTexto | None = Field(
        description=(
            "Mês em que este preço foi definido. Pode ser anterior ao consultado, "
            "porque a vigência se propaga até que um novo preço exista."
        )
    )
    sem_preco: bool = Field(
        description="Verdadeiro quando não há preço definido até o mês consultado. "
        "Item sem preço bloqueia lançamento."
    )


class PrecosDoMes(BaseModel):
    """Tabela de preços de um cliente para um mês."""

    mes: MesTexto
    itens: list[ItemComPreco]


class PrecoResposta(BaseModel):
    """Preço como a API o devolve após definir ou atualizar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_id: uuid.UUID
    item_id: uuid.UUID
    vigencia_mes: MesTexto
    valor_unitario: DinheiroTexto


class VigenciaSugerida(BaseModel):
    """Mês que a interface deve propor ao definir preço.

    Primeiro preço de um item: mês corrente, para que ele possa ser lançado hoje.
    Alteração de preço existente: mês seguinte, porque alteração no meio do mês só
    passa a valer no mês seguinte.
    """

    vigencia_mes: MesTexto
    e_primeiro_preco: bool
