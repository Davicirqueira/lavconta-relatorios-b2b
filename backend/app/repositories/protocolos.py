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
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.dominio import LinhaDeFechamento, LinhaDoResumoGeral, PrecoVigente
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.preco import Preco


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


class RepositorioPrecoProtocolo(Protocol):
    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        data: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        """Preço vigente de cada item na data (regra em ``preco_repo``).

        Item ausente no retorno não tem nenhum preço.
        """
        ...

    def obter_vigente(self, cliente_id: uuid.UUID, item_id: uuid.UUID, data: date) -> Preco | None:
        """O registro que a resolução escolheria para a data."""
        ...

    def obter_no_dia(self, cliente_id: uuid.UUID, item_id: uuid.UUID, dia: date) -> Preco | None:
        """Preço com início exatamente naquele dia."""
        ...

    def inicios(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> list[date]:
        """Datas de início de todos os preços do item, em ordem crescente."""
        ...

    def contar_pedidos_afetados(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        desde: date | None,
        ate_exclusivo: date | None,
        valor_diferente_de: Decimal,
    ) -> int:
        """Pedidos gravados no intervalo com o item a valor diferente do informado."""
        ...

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_inicio: date,
        valor_unitario: Decimal,
    ) -> Preco: ...

    def sincronizar(self) -> None: ...


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


class RepositorioFechamentoProtocolo(Protocol):
    """Recorte do repositório de lançamento usado pelo relatório.

    Protocolo estreito de propósito: o serviço de relatório só lê, e declarar
    apenas a consulta de que depende deixa explícito que ele não escreve nada.

    Também é o que permite testar a agregação — colunas presentes, mapa de
    quantidades, coincidência entre ``totais`` e ``resumo`` — sem Postgres. Essa
    parte é aritmética em Python, não recurso de banco; o SQL real tem cobertura
    própria nos testes de API.
    """

    def buscar_linhas_do_periodo(
        self, cliente_id: uuid.UUID, inicio: date, fim: date
    ) -> list[LinhaDeFechamento]:
        """Linhas de lançamento do cliente no período, ordenadas por data."""
        ...

    def buscar_resumo_geral(self, inicio: date, fim: date) -> list[LinhaDoResumoGeral]:
        """Todos os clientes do período, somados por (cliente, item, valor congelado)."""
        ...
