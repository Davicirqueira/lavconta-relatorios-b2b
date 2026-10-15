from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import uuid

@dataclass(frozen=True, slots=True)
class LinhaDeDemandaDiaria:
    data: date
    quantidades: dict[uuid.UUID, int]
    total_pecas: int
    total_valor: Decimal