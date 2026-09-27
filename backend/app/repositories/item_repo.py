"""Acesso a dados de Item (catálogo por cliente)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.lancamento import LancamentoLinha


class RepositorioItem:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # --- leitura ----------------------------------------------------------

    def obter_por_id(self, item_id: uuid.UUID) -> Item | None:
        return self._sessao.get(Item, item_id)

    def listar_por_cliente(
        self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False
    ) -> list[Item]:
        """Itens de um cliente, em ordem alfabética (Req 3.4)."""
        consulta = select(Item).where(Item.cliente_id == cliente_id)
        if not incluir_inativos:
            consulta = consulta.where(Item.ativo.is_(True))
        consulta = consulta.order_by(func.lower(Item.nome))
        return list(self._sessao.scalars(consulta))

    def buscar_por_nome(self, cliente_id: uuid.UUID, nome: str) -> Item | None:
        """Busca no catálogo do cliente, ignorando caixa e espaços nas pontas.

        A unicidade é POR CLIENTE: "Lençol" pode existir em dois clientes
        diferentes (Req 3.2).
        """
        consulta = select(Item).where(
            Item.cliente_id == cliente_id,
            func.lower(func.btrim(Item.nome)) == nome.strip().lower(),
        )
        return self._sessao.scalars(consulta).first()

    def tem_lancamentos(self, item_id: uuid.UUID) -> bool:
        """Se o item já foi usado em alguma linha de lançamento (Req 3.12)."""
        consulta = select(LancamentoLinha.id).where(LancamentoLinha.item_id == item_id).limit(1)
        return self._sessao.scalars(consulta).first() is not None

    # --- escrita ----------------------------------------------------------

    def inserir(self, cliente_id: uuid.UUID, nome: str) -> Item:
        item = Item(cliente_id=cliente_id, nome=nome)
        self._sessao.add(item)
        self._sessao.flush()
        return item

    def excluir(self, item: Item) -> None:
        self._sessao.delete(item)
        self._sessao.flush()

    def sincronizar(self) -> None:
        self._sessao.flush()
