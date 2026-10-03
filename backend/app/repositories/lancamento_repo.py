"""Acesso a dados de Lançamento e suas linhas."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.dominio import LinhaDeFechamento, LinhaDoResumoGeral
from app.models.cliente import Cliente
from app.models.item import Item
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

    def buscar_linhas_do_periodo(
        self, cliente_id: uuid.UUID, inicio: date, fim: date
    ) -> list[LinhaDeFechamento]:
        """Todas as linhas de lançamento do período, em **uma** consulta (Req 7.6).

        Achatada em (lançamento, item) porque é o formato do ``join``; o serviço
        agrupa por lançamento. Uma consulta só evita o N+1 que apareceria ao
        buscar as linhas lançamento por lançamento.

        ``inner join`` com as linhas: lançamento sem nenhuma linha não apareceria.
        Não existe esse caso — criar e editar exigem ao menos uma linha — e, se
        existisse, uma linha de fechamento com total zero seria ruído.

        A ordenação por data atende o Req 7.9. A ordenação secundária por nome de
        item existe só para tornar o resultado determinístico; a ordem das colunas
        é decidida no serviço, sem depender da collation do banco.

        Volume máximo: 31 lançamentos por mês por cliente (um por dia). Sem
        paginação — a simplicidade aqui é escolha informada.
        """
        consulta = (
            select(
                Lancamento.id.label("lancamento_id"),
                Lancamento.data,
                Lancamento.comanda,
                LancamentoLinha.item_id,
                Item.nome.label("item_nome"),
                LancamentoLinha.quantidade,
                LancamentoLinha.valor_unitario_congelado,
                LancamentoLinha.total,
            )
            .join(LancamentoLinha, LancamentoLinha.lancamento_id == Lancamento.id)
            .join(Item, Item.id == LancamentoLinha.item_id)
            .where(
                Lancamento.cliente_id == cliente_id,
                Lancamento.data >= inicio,
                Lancamento.data <= fim,
            )
            .order_by(Lancamento.data, Item.nome)
        )

        return [
            LinhaDeFechamento(
                lancamento_id=registro.lancamento_id,
                data=registro.data,
                comanda=registro.comanda,
                item_id=registro.item_id,
                item_nome=registro.item_nome,
                quantidade=registro.quantidade,
                valor_unitario_congelado=registro.valor_unitario_congelado,
                total=registro.total,
            )
            for registro in self._sessao.execute(consulta)
        ]

    def buscar_resumo_geral(self, inicio: date, fim: date) -> list[LinhaDoResumoGeral]:
        """Todos os clientes do período, somados por (cliente, item, valor) — v1.1, Req 5.

        **Uma** consulta agrupada, qualquer que seja o número de clientes (Req 5.9).

        - ``inner join`` com lançamentos: cliente sem pedido no período não aparece;
          cliente inativo com pedido aparece (o filtro é só de data, Req 5.5).
        - Agrupar também pelo valor congelado faz o mesmo item, a dois valores no
          período, sair em duas linhas (Req 5.4). Nada é recalculado: ``sum(total)``
          soma a coluna gerada do banco.
        - A ordem final (nomes sem acento) é decidida no serviço, como no
          relatório por cliente.
        """
        consulta = (
            select(
                Cliente.id.label("cliente_id"),
                Cliente.nome.label("cliente_nome"),
                Item.id.label("item_id"),
                Item.nome.label("item_nome"),
                LancamentoLinha.valor_unitario_congelado.label("valor_unitario"),
                func.sum(LancamentoLinha.quantidade).label("quantidade"),
                func.sum(LancamentoLinha.total).label("subtotal"),
            )
            .select_from(Lancamento)
            .join(LancamentoLinha, LancamentoLinha.lancamento_id == Lancamento.id)
            .join(Item, Item.id == LancamentoLinha.item_id)
            .join(Cliente, Cliente.id == Lancamento.cliente_id)
            .where(Lancamento.data >= inicio, Lancamento.data <= fim)
            .group_by(
                Cliente.id,
                Cliente.nome,
                Item.id,
                Item.nome,
                LancamentoLinha.valor_unitario_congelado,
            )
        )
        return [
            LinhaDoResumoGeral(
                cliente_id=registro.cliente_id,
                cliente_nome=registro.cliente_nome,
                item_id=registro.item_id,
                item_nome=registro.item_nome,
                valor_unitario=registro.valor_unitario,
                quantidade=int(registro.quantidade),
                subtotal=registro.subtotal,
            )
            for registro in self._sessao.execute(consulta)
        ]

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

    def recarregar_linhas(self, lancamento: Lancamento) -> None:
        """Recarrega a coleção de linhas do banco.

        Necessário depois de inserir ou remover linhas: a coleção já carregada na
        sessão não reflete escritas feitas fora dela, e o objeto devolvido viria
        com o conjunto obsoleto — linha adicionada não apareceria e linha removida
        continuaria visível.
        """
        self._sessao.refresh(lancamento, ["linhas"])

    def sincronizar(self) -> None:
        self._sessao.flush()
