"""Acesso a dados de Lançamento e suas linhas."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.lancamento import Lancamento, LancamentoLinha


class RepositorioLancamento:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # --- leitura ----------------------------------------------------------

    def obter_por_id(self, lancamento_id: uuid.UUID) -> Lancamento | None:
        """Carrega o lançamento já com as linhas, evitando consulta extra."""
        consulta = (
            select(Lancamento)
            .where(Lancamento.id == lancamento_id)
            .options(selectinload(Lancamento.linhas))
        )
        return self._sessao.scalars(consulta).first()

    def buscar_por_cliente_e_data(self, cliente_id: uuid.UUID, data: date) -> Lancamento | None:
        """Identificador natural do lançamento (Req 5.2)."""
        consulta = select(Lancamento).where(
            Lancamento.cliente_id == cliente_id, Lancamento.data == data
        )
        return self._sessao.scalars(consulta).first()

    def buscar_por_comanda(self, cliente_id: uuid.UUID, comanda: str) -> Lancamento | None:
        """Busca ignorando caixa e espaços, espelhando o índice único parcial."""
        consulta = select(Lancamento).where(
            Lancamento.cliente_id == cliente_id,
            func.lower(func.btrim(Lancamento.comanda)) == comanda.strip().lower(),
        )
        return self._sessao.scalars(consulta).first()

    def listar_por_periodo(
        self, cliente_id: uuid.UUID, inicio: date, fim: date
    ) -> list[Lancamento]:
        """Lançamentos do cliente no período, em ordem de data (Req 7.9)."""
        consulta = (
            select(Lancamento)
            .where(
                Lancamento.cliente_id == cliente_id,
                Lancamento.data >= inicio,
                Lancamento.data <= fim,
            )
            .options(selectinload(Lancamento.linhas))
            .order_by(Lancamento.data)
        )
        return list(self._sessao.scalars(consulta))

    # --- escrita ----------------------------------------------------------

    def inserir(self, cliente_id: uuid.UUID, data: date, comanda: str | None) -> Lancamento:
        lancamento = Lancamento(cliente_id=cliente_id, data=data, comanda=comanda)
        self._sessao.add(lancamento)
        self._sessao.flush()
        return lancamento

    def inserir_linha(
        self,
        lancamento_id: uuid.UUID,
        item_id: uuid.UUID,
        quantidade: int,
        valor_unitario_congelado: Decimal,
    ) -> LancamentoLinha:
        linha = LancamentoLinha(
            lancamento_id=lancamento_id,
            item_id=item_id,
            quantidade=quantidade,
            valor_unitario_congelado=valor_unitario_congelado,
        )
        self._sessao.add(linha)
        self._sessao.flush()
        return linha

    def excluir_linha(self, linha: LancamentoLinha) -> None:
        self._sessao.delete(linha)
        self._sessao.flush()

    def excluir(self, lancamento: Lancamento) -> None:
        """Remove o lançamento; as linhas vão em cascata (Req 5.23)."""
        self._sessao.delete(lancamento)
        self._sessao.flush()

    def sincronizar(self) -> None:
        self._sessao.flush()
