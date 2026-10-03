"""Catálogo com preço: item e preço tratados juntos (v1.1, Req 3).

Orquestração fina sobre ``ServicoItem`` e ``ServicoPreco``. Cada um mantém sua
responsabilidade única — o item não conhece preço, o preço não conhece nome de
item —; este serviço só junta os dois onde a tela precisa deles juntos.

ATOMICIDADE (Req 3.3)
    O valor é validado **antes** de criar o item, então a falha prevista (valor
    inválido) nunca deixa item sem preço. Uma falha inesperada depois da inserção
    do item desfaz tudo pela transação da requisição (``core/banco.obter_sessao``:
    rollback em exceção).
"""

import uuid
from decimal import Decimal

from app.dominio import PrecoVigente
from app.models.item import Item
from app.services.servico_item import ServicoItem
from app.services.servico_preco import ServicoPreco


class ServicoCatalogo:
    def __init__(self, servico_item: ServicoItem, servico_preco: ServicoPreco) -> None:
        self._itens = servico_item
        self._precos = servico_preco

    def listar(
        self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False
    ) -> list[tuple[Item, PrecoVigente | None]]:
        """Itens do cliente com o preço que vale hoje (``None`` = sem preço)."""
        return self._precos.listar_na_data(
            cliente_id, self._precos.hoje(), incluir_inativos=incluir_inativos
        )

    def obter(self, item_id: uuid.UUID) -> tuple[Item, PrecoVigente | None]:
        item = self._itens.obter(item_id)
        return item, self._precos.preco_atual(item.id)

    def criar_item_com_preco(
        self, cliente_id: uuid.UUID, nome: str, valor_unitario: Decimal
    ) -> tuple[Item, PrecoVigente | None]:
        """Cria o item já com o primeiro preço (início hoje, vale também para trás)."""
        self._precos.validar_valor(valor_unitario)
        item = self._itens.criar(cliente_id, nome)
        self._precos.mudar_a_partir_de_hoje(item.id, valor_unitario)
        return item, self._precos.preco_atual(item.id)

    def com_preco(self, item: Item) -> tuple[Item, PrecoVigente | None]:
        """Acrescenta o preço atual a um item já obtido (respostas de escrita)."""
        return item, self._precos.preco_atual(item.id)
