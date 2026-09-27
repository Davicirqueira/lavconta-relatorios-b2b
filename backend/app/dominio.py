"""Objetos de valor do domínio.

Estruturas simples, sem ORM e sem I/O, trocadas entre repositório e serviço
quando uma entidade não é a resposta certa. Ficam separadas dos modelos porque
não representam linha de tabela, e separadas dos schemas porque não são contrato
de API.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PrecoVigente:
    """Preço aplicável a um item num mês de referência.

    ``vigencia_origem`` é o mês em que esse preço foi **definido**, que pode ser
    anterior ao mês consultado — a vigência se propaga até que um novo preço
    exista (Req 4.4).

    Expor a origem dá transparência à regra: o operador vê que o preço de
    setembro veio de junho, em vez de precisar deduzir.
    """

    item_id: uuid.UUID
    valor_unitario: Decimal
    vigencia_origem: date


@dataclass(frozen=True, slots=True)
class SugestaoDeVigencia:
    """Mês a propor na interface ao definir preço, e por quê.

    ``e_primeiro_preco`` vem da consulta ao repositório, não de comparar o mês
    sugerido com o corrente. Derivar por comparação funcionaria hoje e quebraria
    em silêncio se a regra de sugestão mudasse.
    """

    vigencia_mes: date
    e_primeiro_preco: bool


@dataclass(frozen=True, slots=True)
class ResolucaoDePrecos:
    """Resultado de resolver preços para um conjunto de itens.

    Separa explicitamente o que foi resolvido do que **não tem preço**. Quem
    consome decide o que fazer com a ausência: o lançamento recusa (Req 5.14), a
    prévia de totais apenas informa.
    """

    vigentes: dict[uuid.UUID, PrecoVigente]
    sem_preco: tuple[uuid.UUID, ...]

    @property
    def completa(self) -> bool:
        return not self.sem_preco
