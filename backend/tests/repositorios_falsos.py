"""Repositórios em memória que satisfazem os protocolos da camada de dados.

Permitem testar a regra de negócio **sem banco**: rápido, sem I/O, e falha por
defeito de regra em vez de por indisponibilidade de infraestrutura.

Funciona porque modelo declarativo do SQLAlchemy pode ser instanciado sem sessão.
O que o falso emula é apenas o contrato: busca por nome normalizado, presença de
histórico e atribuição de identificador na inserção.

Não substituem os testes contra Postgres: constraint, índice parcial e coluna
gerada só existem no banco real e têm suíte própria em ``test_constraints.py``.
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app.dominio import PrecoVigente
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.preco import Preco


def _normalizar(nome: str) -> str:
    """Espelha o que o índice único faz: lower(btrim(nome))."""
    return nome.strip().lower()


class RepositorioClienteFalso:
    """Emula ``RepositorioClienteProtocolo`` em memória."""

    def __init__(self) -> None:
        self.registros: dict[uuid.UUID, Cliente] = {}
        # ids marcados como tendo histórico de cobrança
        self.com_lancamentos: set[uuid.UUID] = set()
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(self, nome: str, *, ativo: bool = True, com_lancamento: bool = False) -> Cliente:
        cliente = Cliente(nome=nome, ativo=ativo)
        cliente.id = uuid.uuid4()
        self.registros[cliente.id] = cliente
        if com_lancamento:
            self.com_lancamentos.add(cliente.id)
        return cliente

    # --- contrato ---------------------------------------------------------

    def obter_por_id(self, cliente_id: uuid.UUID) -> Cliente | None:
        return self.registros.get(cliente_id)

    def listar(self, *, incluir_inativos: bool = False) -> list[Cliente]:
        clientes = [
            cliente for cliente in self.registros.values() if incluir_inativos or cliente.ativo
        ]
        return sorted(clientes, key=lambda cliente: cliente.nome.lower())

    def buscar_por_nome(self, nome: str) -> Cliente | None:
        alvo = _normalizar(nome)
        for cliente in self.registros.values():
            if _normalizar(cliente.nome) == alvo:
                return cliente
        return None

    def tem_lancamentos(self, cliente_id: uuid.UUID) -> bool:
        return cliente_id in self.com_lancamentos

    def inserir(self, nome: str) -> Cliente:
        cliente = Cliente(nome=nome, ativo=True)
        cliente.id = uuid.uuid4()
        self.registros[cliente.id] = cliente
        return cliente

    def excluir(self, cliente: Cliente) -> None:
        self.registros.pop(cliente.id, None)

    def sincronizar(self) -> None:
        self.sincronizacoes += 1


class RepositorioItemFalso:
    """Emula ``RepositorioItemProtocolo`` em memória."""

    def __init__(self) -> None:
        self.registros: dict[uuid.UUID, Item] = {}
        self.com_lancamentos: set[uuid.UUID] = set()
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        cliente_id: uuid.UUID,
        nome: str,
        *,
        ativo: bool = True,
        com_lancamento: bool = False,
    ) -> Item:
        item = Item(cliente_id=cliente_id, nome=nome, ativo=ativo)
        item.id = uuid.uuid4()
        self.registros[item.id] = item
        if com_lancamento:
            self.com_lancamentos.add(item.id)
        return item

    # --- contrato ---------------------------------------------------------

    def obter_por_id(self, item_id: uuid.UUID) -> Item | None:
        return self.registros.get(item_id)

    def listar_por_cliente(
        self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False
    ) -> list[Item]:
        itens = [
            item
            for item in self.registros.values()
            if item.cliente_id == cliente_id and (incluir_inativos or item.ativo)
        ]
        return sorted(itens, key=lambda item: item.nome.lower())

    def buscar_por_nome(self, cliente_id: uuid.UUID, nome: str) -> Item | None:
        alvo = _normalizar(nome)
        for item in self.registros.values():
            if item.cliente_id == cliente_id and _normalizar(item.nome) == alvo:
                return item
        return None

    def tem_lancamentos(self, item_id: uuid.UUID) -> bool:
        return item_id in self.com_lancamentos

    def inserir(self, cliente_id: uuid.UUID, nome: str) -> Item:
        item = Item(cliente_id=cliente_id, nome=nome, ativo=True)
        item.id = uuid.uuid4()
        self.registros[item.id] = item
        return item

    def excluir(self, item: Item) -> None:
        self.registros.pop(item.id, None)

    def sincronizar(self) -> None:
        self.sincronizacoes += 1


class RepositorioPrecoFalso:
    """Emula ``RepositorioPrecoProtocolo`` em memória.

    A resolução replica em Python o que o ``DISTINCT ON`` faz no banco: entre os
    preços com vigência até o mês de referência, vence o de vigência mais recente.

    Reimplementar a regra aqui é intencional. Se a consulta SQL e esta versão
    divergirem, os testes contra Postgres em ``test_constraints.py`` e os de API
    acusam — e a divergência aponta defeito em uma das duas.
    """

    def __init__(self) -> None:
        # (cliente_id, item_id, vigencia_mes) -> Preco
        self.registros: dict[tuple[uuid.UUID, uuid.UUID, date], Preco] = {}
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor: str,
    ) -> Preco:
        return self.inserir(cliente_id, item_id, vigencia_mes, Decimal(valor))

    # --- contrato ---------------------------------------------------------

    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        mes_referencia: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        if not item_ids:
            return {}

        procurados = set(item_ids)
        candidatos: dict[uuid.UUID, Preco] = {}

        for (cli, item, vigencia), preco in self.registros.items():
            if cli != cliente_id or item not in procurados or vigencia > mes_referencia:
                continue
            atual = candidatos.get(item)
            if atual is None or vigencia > atual.vigencia_mes:
                candidatos[item] = preco

        return {
            item_id: PrecoVigente(
                item_id=item_id,
                valor_unitario=preco.valor_unitario,
                vigencia_origem=preco.vigencia_mes,
            )
            for item_id, preco in candidatos.items()
        }

    def obter_do_mes(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, vigencia_mes: date
    ) -> Preco | None:
        return self.registros.get((cliente_id, item_id, vigencia_mes))

    def existe_algum(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        return any(cli == cliente_id and item == item_id for cli, item, _ in self.registros)

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor_unitario: Decimal,
    ) -> Preco:
        preco = Preco(
            cliente_id=cliente_id,
            item_id=item_id,
            vigencia_mes=vigencia_mes,
            valor_unitario=valor_unitario,
        )
        preco.id = uuid.uuid4()
        self.registros[(cliente_id, item_id, vigencia_mes)] = preco
        return preco

    def sincronizar(self) -> None:
        self.sincronizacoes += 1
