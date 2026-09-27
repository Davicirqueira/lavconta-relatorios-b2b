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

from app.models.cliente import Cliente
from app.models.item import Item


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
