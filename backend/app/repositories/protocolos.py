"""Contratos da camada de repositório.

POR QUE PROTOCOLO
    Os serviços declaram dependência sobre estes protocolos, não sobre as
    implementações concretas. Duas consequências práticas:

    1. A regra de negócio fica testável sem banco — um repositório falso em
       memória satisfaz o contrato.
    2. O contrato fica explícito e verificável por tipo, em vez de implícito no
       acoplamento.

ESCOPO HONESTO DESTA CAMADA
    Os repositórios devolvem **entidades do domínio** (que por conveniência são
    os próprios modelos ORM), e os serviços alteram atributos dessas entidades.
    Não há tradução para estruturas separadas.

    Isso é deliberado: um mapeamento adicional dobraria o código sem ganho nesta
    escala. O que a camada entrega de fato é concentração das consultas e
    possibilidade de testar a regra sem I/O — não independência total do ORM.
    Modelo declarativo pode ser instanciado em memória, sem sessão, o que basta
    para o repositório falso funcionar.
"""

import uuid
from typing import Protocol

from app.models.cliente import Cliente
from app.models.item import Item


class RepositorioClienteProtocolo(Protocol):
    def obter_por_id(self, cliente_id: uuid.UUID) -> Cliente | None: ...

    def listar(self, *, incluir_inativos: bool = False) -> list[Cliente]: ...

    def buscar_por_nome(self, nome: str) -> Cliente | None:
        """Busca ignorando caixa e espaços nas pontas (espelha o índice único)."""
        ...

    def tem_lancamentos(self, cliente_id: uuid.UUID) -> bool: ...

    def inserir(self, nome: str) -> Cliente: ...

    def excluir(self, cliente: Cliente) -> None: ...

    def sincronizar(self) -> None:
        """Aplica alterações pendentes, disparando as constraints do banco."""
        ...


class RepositorioItemProtocolo(Protocol):
    def obter_por_id(self, item_id: uuid.UUID) -> Item | None: ...

    def listar_por_cliente(
        self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False
    ) -> list[Item]: ...

    def buscar_por_nome(self, cliente_id: uuid.UUID, nome: str) -> Item | None:
        """Busca no catálogo do cliente; a unicidade é POR CLIENTE."""
        ...

    def tem_lancamentos(self, item_id: uuid.UUID) -> bool: ...

    def inserir(self, cliente_id: uuid.UUID, nome: str) -> Item: ...

    def excluir(self, item: Item) -> None: ...

    def sincronizar(self) -> None: ...
